# Architecture

How data moves from the TLC CloudFront endpoint to the public dashboard, which component owns each step, and where it lives in this repo.

For *why* each choice was made, see [`DECISIONS.md`](DECISIONS.md) (referenced as `D-xxx` below). For cold-start / reactivation steps, see `REACTIVATE.md` (local only).

---

## 1. System Overview

```mermaid
flowchart LR
    subgraph SRC[External sources]
        TLC[TLC CloudFront<br/>Yellow Taxi Parquet 2023]
        OSM[Geofabrik<br/>NY State OSM .pbf]
        NYC[NYC Open Data<br/>Taxi Zones GeoJSON]
    end

    subgraph ORCH[Kestra · Docker Compose · local]
        F1[flow_01<br/>tlc_parquet_to_gcs]
        F2[flow_02<br/>osm_streets_to_gcs]
        F3[flow_03<br/>taxi_zones_and_h3_grid]
        F4[flow_04<br/>spark_h3_enrichment]
    end

    subgraph GCP[GCP · asia-southeast1 · Terraform]
        GCS[(GCS bucket<br/>hardy-geo-de-267342)]
        DP[Ephemeral Dataproc<br/>PySpark flow4_h3_enrichment]
        BQR[(BigQuery<br/>geoops_raw)]
        BQD[(BigQuery<br/>geoops_dbt_dev)]
    end

    DBT[dbt<br/>staging → intermediate → marts]

    subgraph SB[Supabase · PostGIS]
        RL[(revenue_loss_by_zone)]
        OS[(osm_streets)]
    end

    ST[Streamlit Cloud<br/>public dashboard]
    GHA[GitHub Actions<br/>keepalive cron]

    TLC --> F1 --> GCS
    OSM --> F2 --> GCS
    NYC --> F3 --> GCS
    GCS --> DP --> BQR
    F4 -- create · submit · delete --> DP
    BQR --> DBT --> BQD
    BQD -. manual export .-> RL
    GCS -. osm_road_density.py .-> OS
    OS -- ST_Intersects --> RL
    RL --> ST
    GHA -- every 3 days --> SB
```

Solid arrows are automated or scripted steps. Dotted arrows are steps run by hand (see [§6 Known gaps](#6-known-gaps)).

---

## 2. Layers

| # | Layer | Tool | Runs where | Repo path | Decisions |
|---|---|---|---|---|---|
| 1 | Infrastructure | Terraform (GCS remote state) | Local CLI → GCP | `infrastructure/terraform/` | D-011 – D-016, D-060 |
| 2 | Ingestion / orchestration | Kestra | Docker Compose (local) | `kestra/flows/`, `docker-compose.yaml` | D-017, D-019, D-032 – D-036, D-059 |
| 3 | Processing | PySpark | Ephemeral Dataproc (created by flow_04) | `spark/flow4_h3_enrichment.py` | D-040 – D-046, D-059 |
| 4 | Warehouse transform | dbt-bigquery | Local CLI (ADC oauth) | `dbt/nyc_taxi_supply_demand/` | D-055 |
| 5 | Spatial serving DB | Supabase PostGIS 3.3 | Supabase cloud | `scripts/osm_road_density.py` | D-009, D-031, D-057 |
| 6 | Presentation | Streamlit + pydeck | Streamlit Community Cloud | `streamlit/app.py` | — |
| 7 | Ops | GitHub Actions | GitHub-hosted runner | `.github/workflows/`, `scripts/supabase_keepalive.py` | D-058 |

---

## 3. Data Flow, Step by Step

### 3.1 Ingestion → GCS raw zone (Kestra)

| Flow | Source | Lands at |
|---|---|---|
| `flow_01_tlc_parquet_to_gcs` | `d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-MM.parquet` | `gs://hardy-geo-de-267342/raw/tlc_yellow/year=2023/month=MM/` |
| `flow_02_osm_streets_to_gcs` | Geofabrik NY State extract, filtered to drivable highway classes (D-033), bbox-clipped (D-034) | GeoParquet in `raw/` |
| `flow_03_taxi_zones_and_h3_grid` | NYC Open Data taxi zones | `raw/reference/nyc_taxi_zones.geojson`, `raw/h3_grid/h3_res8_nyc.parquet` |

Plus one reference artifact (D-044): `raw/reference/location_h3_lookup.csv` — 260 rows, `LocationID → h3_res8`. It is precomputed because Dataproc nodes have no internet access for `pip install`. flow_04 rebuilds it from the committed dbt seed on every run (D-059).

Only `raw/tlc_yellow/` expires after 90 days (D-060). Re-running flow_04 after that needs a flow_01 backfill.

### 3.2 Processing (PySpark on Dataproc, orchestrated by flow_04)

`kestra/flows/flow_04_spark_h3_enrichment.yaml` runs: preflight (12 TLC months in GCS?) → stage lookup → create cluster → submit job → verify row count → **delete cluster in `finally`**. The Spark script and lookup are fetched from GitHub at the `git_ref` input.

`spark/flow4_h3_enrichment.py`:

1. Reads each month separately and casts to a common schema, then `unionByName` — January 2023 uses a different schema from Feb–Dec (D-045, D-045a).
2. Filters invalid trips (D-040): 38.3M → 34.96M rows.
3. Joins the LocationID → H3 lookup for pickup and dropoff (D-041).
4. Writes `geoops_raw.yellow_trips_h3_enriched` via the built-in BigQuery connector (D-046) — partitioned by `DAY(tpep_pickup_datetime)`, clustered by `h3_pickup_res8, h3_dropoff_res8`.

The cluster exists only for the length of a run (~$0.20/hr). Terraform does not manage it (D-059).

### 3.3 Warehouse transform (dbt → `geoops_dbt_dev`)

```
source: geoops_raw.yellow_trips_h3_enriched
  └─ stg_yellow_trips                         (view)
       ├─ int_demand_by_h3_hour               (table)  pickups  = demand
       └─ int_supply_by_h3_hour               (table)  dropoffs = supply
            └─ int_supply_demand_gap          (table)
                 ├─ mart_temporal_patterns    (table)  hour × day-of-week
                 └─ mart_gap_zones            (table)  zone-level rates (D-055)
                      └─ mart_gap_zones_named (table)  + seed location_h3_zone_lookup
                           └─ mart_revenue_loss (table)
```

Guardrail tests (`tests/`, `_marts.yaml`): `unmet_demand_rate ∈ [0,1]`, `supply_demand_ratio ≥ 0`, `zone_status ∈ {UNDERSUPPLIED, BALANCED, OVERSUPPLIED}`. Rates are computed as a ratio of totals, never an average of ratios (D-055).

### 3.4 Spatial layer (Supabase PostGIS)

| Table | Rows | Origin |
|---|---|---|
| `revenue_loss_by_zone` | 185 | Export of `mart_revenue_loss` + H3 cell geometry |
| `osm_streets` | 72,005 | Loaded from GCS by `scripts/osm_road_density.py`, GIST index on `geom` |

`osm_road_density.py` adds `road_segment_count` to `revenue_loss_by_zone` via `ST_Intersects` (D-057). Without the GIST index this step takes 10+ minutes instead of ~90s.

### 3.5 Presentation (Streamlit)

`streamlit/app.py` reads Supabase directly with psycopg2 (`SUPABASE_DB_URL`), cached for 5 minutes (`@st.cache_data(ttl=300)`):

- `load_zones()` — zone metrics + `ST_AsGeoJSON(geom)` for the H3 hexagon map.
- `load_transit()` — `ST_Distance` from each zone to 5 transit hubs (Penn Station, Grand Central, Port Authority, Union Square, JFK AirTrain).

Live at <https://nyctaxisupplydemandanalysis.streamlit.app>.

---

## 4. Operations

### 4.1 Supabase keepalive (D-058)

Supabase free tier pauses after ~7 days idle, which would break the public dashboard.

```
GitHub Actions cron "17 3 */3 * *"
  → python scripts/supabase_keepalive.py
      → SELECT count(*) FROM revenue_loss_by_zone   (expect 185)
      → SELECT count(*) FROM osm_streets            (expect 72,005)
  → gh api PUT .../workflows/supabase-keepalive.yml/enable
```

- Connect failure → non-zero exit → red run in the Actions tab.
- Row-count mismatch → warning only (the ping still counts as activity).
- The final step re-enables the workflow so GitHub's 60-day inactivity rule does not silently stop the schedule.
- Run manually: Actions → *Supabase keepalive* → *Run workflow*, or locally `python scripts/supabase_keepalive.py`.

### 4.2 Cost control

| Resource | Billing | Policy |
|---|---|---|
| Dataproc `geoops-spark` | Per hour while it exists | Created and deleted by flow_04; `--max-idle=30m` backup |
| BigQuery | Storage + on-demand query | Partition + cluster on the enriched table |
| GCS | Storage | `raw/tlc_yellow/` expires after 90 days; Terraform state bucket versioned |
| Supabase | Free tier (500 MB, 2 active projects per owner) | Keepalive; both active slots in use (this project + portfolio website DB) |
| Streamlit Cloud, GitHub Actions | Free | — |

---

## 5. Secrets & Configuration

| Secret | Used by | Stored in |
|---|---|---|
| `SUPABASE_DB_URL` (session pooler, IPv4) | Streamlit app, scripts, keepalive | `.env` (local), Streamlit Cloud secrets, GitHub Actions secret |
| GCP credentials | dbt, gcloud | Application Default Credentials (`gcloud auth application-default login`) |
| Terraform auth | Terraform | ADC by default; optional `credentials` var → SA key path |

All are gitignored (`.env`, `*.json`, `*secret*`, `*creds*`, `terraform.tfvars`). When rotating the Supabase password, update **all three** locations of `SUPABASE_DB_URL` — missing Streamlit Cloud breaks the public dashboard.

---

## 6. Known Gaps

Stated up front rather than left for a reviewer to find:

1. **Orchestration stops after Spark.** flow_01–04 cover ingestion and enrichment. `dbt build`, the BigQuery → Supabase export, and `osm_road_density.py` are run by hand.
2. **The BigQuery → Supabase export is not scripted in this repo.** `revenue_loss_by_zone` was loaded manually.
3. **flow_04 has not run end-to-end yet.** GCS raw expired (D-060). The first run needs a 12-month flow_01 backfill.
4. **CI covers only the keepalive.** No automated `dbt build` or lint on push.
