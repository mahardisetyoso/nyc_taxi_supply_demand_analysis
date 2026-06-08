# Decisions Log

All technical and strategic decisions that have been made and are **NOT to be reopened**.
Before adding scope, switching tools, or revisiting any decision — read this file first.

---

## DECISIONS — PROBLEM & SCOPE

### D-001 | Problem Statement Selection
**Date:** 2026-05-31 (Day 0)
**Decision:** Supply-Demand Gap Analysis as project headline, not Schema & Query Optimization.
**Rationale:** Schema optimization is a method, not a problem statement. No hiring manager wants to read a portfolio about "optimized tables." Supply-demand analysis has dollar value, spatial visualization potential, and direct operational relevance.
**Implication:** Schema & Query Optimization remains as engineering content angle, not project headline.

### D-002 | Problem Statement Framework
**Date:** 2026-05-31 (Day 0)
**Decision:** "NYC Taxi Supply-Demand Gap Analysis: Identifying Underserved Zones and Lost Revenue Windows Using Spatial Aggregation and H3 Indexing"
**Business Questions:**
1. Which H3 zones are consistently high-demand but low-supply during peak hours?
2. What is the estimated revenue loss from supply-demand gaps?
3. Are there predictable temporal patterns (hour/day) in these gaps?
**Rationale:** Three concrete questions answerable without ML, directly ops-relevant, with quantifiable revenue impact.

### D-003 | Data Scope
**Date:** 2026-05-31 (Day 0)
**Original Decision:** Yellow Taxi only, January–June 2023. Fixed. Not to be expanded.
**Original Rationale:** 6 months sufficient for seasonal patterns. Not too large for pipeline performance (~18-20M rows).

**⚠️ AMENDED — D-003a | Scope Expansion to Full Year**
**Date:** 2026-06-02 (Day 2)
**Revised Decision:** 2023 January–December (12 months).
**Rationale:** Business Question #3 (temporal patterns) requires annual seasonality detection — winter dropoff, summer surge, holiday spikes. H1 only cannot show full cycle.
**Trade-off accepted:** 2x storage + 2x Spark processing cost (~$3-5 incremental, negligible against free trial credit).
**Lock:** Full year 2023. No expansion to multi-year.

### D-004 | Predictive Element — Evaluate Later
**Date:** 2026-06-01 (Day 1)
**Decision:** Consider simple time series forecast (BigQuery ML ARIMA_PLUS) for business question #3. Evaluate in Week 5, not now.
**Rationale:** Shifts framing from descriptive (2018-era) to predictive (2026-relevant). Must not add scope prematurely.
**Status:** PENDING — revisit in Week 5.

---

## DECISIONS — DATA SOURCE

### D-005 | TLC Data via CloudFront, Not Socrata API
**Date:** 2026-06-01 (Day 1)
**Decision:** Direct Parquet download from TLC CloudFront URLs.
**URL Pattern:** `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-{01-12}.parquet`
**Rationale:** Full dataset (not sampled), PySpark-native format, predictable URL pattern for Kestra orchestration. Socrata API = sampled data + rate limits.
**Lock:** No switching to Socrata.

### D-006 | Additional Data Sources
**Date:** 2026-05-31 (Day 0)
**Decision:** 4 data sources total:
1. NYC TLC Yellow Taxi Parquet (CloudFront) — trip events
2. OSM Street Data (Geofabrik PBF) — road network context
3. H3 Grid Table (generated via Python h3-py) — spatial aggregation unit
4. NYC Taxi Zone boundaries (official GeoParquet) — zone reference
**Rejected:** NYC Census/PLUTO as demand proxy — insufficient value for added complexity.

---

## DECISIONS — ARCHITECTURE & STACK

### D-007 | Spatial Aggregation Unit — H3 Resolution 8
**Date:** 2026-05-31 (Day 0)
**Decision:** H3 resolution 8 (~460m hexagon) as primary analysis unit.
**Rationale:** Balance between granularity and query performance. Res 7 too coarse (~1.2km), res 9 too granular (~175m) for supply-demand analysis.
**Lock:** Fixed. No switching to S2, Geohash, or different resolution.

### D-008 | H3 Over S2 or Geohash
**Date:** 2026-06-01 (Day 1)
**Decision:** H3 hexagonal indexing, not Google S2 cells or Geohash.
**Rationale:** H3 has uniform adjacency (6 neighbors vs variable in S2 quads), more natural for supply-demand spatial analysis as distance to all neighbors is equal. H3 is the de facto standard post-2024 — native support in BigQuery, Snowflake, Databricks.
**Interview note:** If asked "why not S2?" — reference Gojek ATLAS (2018) used S2 when H3 wasn't mature yet. H3 is the 2026 choice.

### D-009 | Dual Database Strategy
**Date:** 2026-05-31 (Day 0)
**Decision:** BigQuery for analytical workload + Supabase/PostGIS for spatial queries.
**Rationale:** PostGIS is the primary gap in Pano AI JD. Supabase = cloud-native PostgreSQL + PostGIS extension, already familiar from previous portfolio. Not redundant architecture — each serves a distinct role.
**Technical justification:** "BigQuery is optimal for large-scale analytics; PostGIS/Supabase for spatial operations requiring native geometry functions (ST_Within, ST_Distance, buffer analysis)."

### D-010 | Full Stack Definition
**Date:** 2026-05-31 (Day 0)
**Decision:** Kestra → GCS → Dataproc/PySpark → BigQuery → dbt → Streamlit + Supabase/PostGIS
**Rationale:** Every tool has specific justification. Nothing added to "look impressive."
**Lock:** No additional tools without explicit decision entry here.

### D-011 | Terraform as IaC
**Date:** 2026-06-01 (Day 1)
**Decision:** Terraform for all GCP resource provisioning.
**Rationale:** Industry standard, reproducible, version controlled. Separation of config (variables.tf) from resources (main.tf).

---

## DECISIONS — GCP INFRASTRUCTURE

### D-012 | Separate GCP Project
**Date:** 2026-06-01 (Day 1)
**Decision:** New project `hardy-geo-portofolio`, fully isolated from bootcamp course.
**Rationale:** Complete isolation — billing, credentials, resources do not mix. Portfolio must stand alone.

### D-013 | Region Selection
**Date:** 2026-05-31 (Day 0)
**Decision:** asia-southeast1 (Singapore).
**Rationale:** Low latency from Jakarta. Consistent across all resources (GCS, BigQuery, Dataproc).

### D-014 | GCS Bucket Configuration
**Date:** 2026-06-01 (Day 1)
**Decision:** Bucket name `hardy-geo-de-267342`, STANDARD storage class, 90-day lifecycle delete rule.
**Rationale:** Globally unique name. 90 days sufficient for full development cycle.

### D-015 | BigQuery Dataset Separation
**Date:** 2026-06-01 (Day 1)
**Decision:** Two datasets — `geoops_raw` (raw ingested data) and `geoops_dbt_dev` (dbt transformed models).
**Rationale:** Separation of concerns. Raw and transformed data must not coexist in same dataset.

### D-016 | Service Account Roles
**Date:** 2026-06-01 (Day 1)
**Decision:** Service account `terraform-runner` with roles: Storage Admin, BigQuery Admin, Dataproc Administrator.
**Rationale:** Minimum roles required for Terraform provisioning + future Dataproc cluster creation.

---

## DECISIONS — DOCKER & KESTRA

### D-017 | Kestra Lean Setup
**Date:** 2026-06-01 (Day 1)
**Decision:** Docker Compose with only 2 services — kestra + kestra_postgres. No pgdatabase, no pgAdmin.
**Rationale:** Portfolio pipeline does not need local Postgres. Data flows directly to GCS → BigQuery.

### D-018 | GCP Credentials via .env File
**Date:** 2026-06-01 (Day 1)
**Decision:** Base64-encoded JSON key stored in `.env` file, auto-read by Docker Compose.
**Rationale:** Simpler than KV store approach. `.env` is gitignored. No manual export needed per session.

---

## DECISIONS — INGESTION ARCHITECTURE

### D-019 | Three Separate Kestra Flows
**Date:** 2026-06-01 (Day 1)
**Decision:** 3 independent flows, not 1 monolith:
- Flow 1: TLC Parquet → GCS (no Python, Kestra native HTTP + GCS tasks)
- Flow 2: OSM PBF → Python processing (osmium/GeoPandas) → GCS
- Flow 3: H3 grid generation (Python h3-py) → GCS
**Rationale:** Independent execution — if one fails, others continue. Easier to debug, test, and maintain individually.

### D-020 | Flow Execution Priority
**Date:** 2026-06-01 (Day 1)
**Decision:** Build order: Flow 1 first (TLC), then Flow 3 (H3), then Flow 2 (OSM).
**Rationale:** Flow 1 is simplest and immediately produces queryable data. Quick win for momentum. OSM processing is most complex — save for last.

---

## DECISIONS — SPARK PERFORMANCE

### D-021 | Pre-Planned Spark Performance Mitigations
**Date:** 2026-06-01 (Day 1)
**Decision:** Four mitigations decided before writing any Spark code:
1. **Broadcast join** for zone tables (~300 rows) — eliminates shuffle entirely
2. **Salting** for skewed H3 keys (Manhattan hotkey problem)
3. **AQE enabled** (`spark.sql.adaptive.enabled = true`) — auto-rebalance partitions
4. **Coalesce before write** — target file size 128MB-1GB, prevent small files problem
**Rationale:** 10 Spark problems identified upfront: data skew, small files, cartesian product, Python UDF slowness, shuffle spill, repartition overuse, missing predicate pushdown, driver OOM, straggler tasks, inefficient window functions. Mitigations must be architectural decisions, not afterthoughts.
**Content angle:** Each problem = 1 LinkedIn post with real NYC taxi examples.

---

## DECISIONS — CONTENT & POSITIONING

### D-022 | Content Platform Sequencing
**Date:** 2026-05-31 (Day 0)
**Decision:** LinkedIn only until portfolio complete → Medium from Week 3 → Instagram from Week 6 → Substack Week 7-8.
**Rationale:** Publishing on 4 platforms from day one is self-sabotage. A good portfolio generates good content, not the other way around.

### D-023 | Target Audience
**Date:** 2026-05-31 (Day 0)
**Decision:** Primary audience: Geospatial Data Engineering hiring managers and talent acquisition.
**Rationale:** Lead with one audience for 90-day focus. Audience dilution (recruiters + engineers + general users) reduces impact.

### D-024 | Schema Optimization as Content, Not Headline
**Date:** 2026-05-31 (Day 0)
**Decision:** Schema & Query Optimization enters as content angle (LinkedIn/Medium posts), not as portfolio headline.
**Rationale:** Demonstrates engineering depth without altering problem statement. Potential for 2-3 posts on "Why I designed my schema this way."

### D-025 | Modern Framing vs 2018 Approaches
**Date:** 2026-06-01 (Day 1)
**Decision:** Explicitly position project as "2026 approach" — H3 (not S2), dbt (not custom aggregation), BigQuery (not custom time series DB), Terraform (not custom IaC), Kestra (not custom orchestration).
**Rationale:** Gojek ATLAS (2018) had to custom-build because managed tools weren't mature. In 2026, the value is in selecting the right tools and connecting them end-to-end, not reinventing infrastructure.
**Interview framing:** "I can deliver equivalent analytical value using open-source managed stack, demonstrating I know how to choose the right tools — not just build everything from scratch."

---

## DECISIONS — ANTI-PATTERNS (DO NOT DO)

### D-026 | Scope Creep Prevention Protocol
**Date:** 2026-05-31 (Day 0)
**Decision:** Every temptation to add data sources, switch tools, or expand scope must be logged here with reasoning for rejection.
**Rationale:** Parallel polish is an identified behavioral pattern. Single-focus commitment is the counter-strategy.

---

## AMENDMENT LOG

| Date | Decision | Change | Justification |
|---|---|---|---|
| 2026-06-02 | D-003 → D-003a | Scope expanded from Jan-Jun to Jan-Dec 2023 | Q3 temporal patterns require annual seasonality detection |

---

## 2026-06-02 — Flow 1 Design Decisions

 GCS path layout | Hive-partitioned: `raw/tlc_yellow/year=YYYY/month=MM/` | Enables Spark partition prune + BQ external table auto-detect. Industrial pattern. |
| Scope expansion | 2023 Jan-Dec (12 bulan), from initial 6 bulan | Q3 (temporal patterns) requires annual seasonality detection. Trade-off: 2x cost (~$3-5 incremental, negligible vs free credit). |
| Execution pattern | Single-month YAML + disabled schedule trigger + Kestra Backfill UI | Demonstrates production pattern (scheduled + backfillable) without committing to live cron. |
| Raw landing validation | Inline size check only (< 10MB = fail) | Pragmatic for Flow 1 raw. Deep validation (schema, row count) defer ke transform layer di dbt. |
| Idempotency | Overwrite GCS objects on re-run. Source data immutable (TLC CloudFront). | Versioning GCS filename tidak reach dbt reproducibility (chain break at GCS→BQ). Reproducibility delivered via PySpark-injected metadata columns (`_ingested_at`, `_source_file`) di BQ raw table — implemented di Spark Flow nanti. |
| Kestra namespace | `geoops.portfolio.raw` | Hierarchy scales to `transform` + `serve` layers. |

## DECISIONS — FLOW 3 PREP (TAXI ZONES + H3 GRID)

### D-006a | AMENDMENT — Remove H3 Grid from Data Sources List
**Date:** 2026-06-04 (Day 3 prep)
**Original D-006:** 4 data sources — TLC Parquet, OSM, H3 Grid, NYC Taxi Zones.
**Amended:** 3 data sources — TLC Parquet, OSM, NYC Taxi Zones.
**Rationale:** H3 Grid removed from "data sources" — it is a derived dataset computed from Taxi Zones (see D-027), not an ingested source. Categorizing computed data as data source conflated raw vs derived layers.

### D-027 | NYC Taxi Zones as Single Spatial Reference Source [MERGED]
**Date:** 2026-06-04 (Day 3 prep)
**Decision:** NYC Taxi Zones GeoJSON serves dual purpose as the single spatial reference source.
**Dual purpose:**
  1. **Spatial reference / lookup** — PULocationID and DOLocationID in TLC trips ↔ zone name + borough
  2. **H3 polyfill source** — union 263 zone polygons → polyfill at res 8 → ~12K H3 cells

**Rationale for merge (vs initially planned separate boroughs source):**
  - Single source-of-truth for NYC spatial geometry
  - Consistent coverage — H3 grid covers exactly the same area as analytical zone lookup
  - No mismatch risk between "where can H3 cells exist" and "where can trips be assigned"
  - Native join with TLC trip data via `locationid` (matches PULocationID/DOLocationID)

**Source:** NYC OpenData — "NYC Taxi Zones" dataset (ID: `8meu-9t5y`)
**Verified URL (2026-06-04):**

**URL** https://data.cityofnewyork.us/api/geospatial/8meu-9t5y?method=export&format=GeoJSON

**API pattern:** Socrata geospatial export — returns full dataset in single response, no pagination required.
**Verified payload structure:** `FeatureCollection` with 263 features, properties = `{shape_area, locationid, shape_leng, zone, borough}`, geometry = `MultiPolygon`.

**Trade-off accepted:**
  - 263 polygon union polyfill (~10s) vs 5 boroughs union polyfill (~1s)
  - One-time cost during H3 grid generation, negligible for portfolio scope
  - Production scale would pre-compute dissolved geometry if rebuild becomes frequent

**Storage outputs (Flow 3, Day 3 build):**
  - `gs://hardy-geo-de-267342/raw/reference/nyc_taxi_zones.geojson` (~1-2 MB)
  - `gs://hardy-geo-de-267342/raw/h3_grid/h3_res8_nyc.parquet` (~80 KB, ~1,070 rows, centroid containment mode)

**Granularity confirmed via Jupyter prototype (2026-06-04):** 1,070 H3 cells cover NYC ~784 km² (math: 1070 × 0.737 km²/cell = 789 km², matching expected). Initial estimate of ~12K cells was incorrect — caught during pre-production validation.

**Lock:** No fallback to separate boroughs source. Taxi zones = single spatial reference for entire project.

### D-028 | H3 Library Version & Output Schema
**Date:** 2026-06-04 (Day 3 prep)
**Decision:** H3 v4 Python library (`h3-py` ≥ 4.0).
**Output Parquet schema for `h3_res8_nyc.parquet`:**

| Column | Type | Description |
|---|---|---|
| `h3_index` | STRING | H3 cell ID at resolution 8 |
| `h3_centroid_lat` | FLOAT64 | Centroid latitude |
| `h3_centroid_lng` | FLOAT64 | Centroid longitude |
| `h3_resolution` | INT64 | Fixed at 8 |
| `h3_parent_res7` | STRING | Parent H3 cell at res 7 (enables hierarchical aggregation later) |

**Rationale:**
  - H3 v4 = 2026 current standard. v3 deprecated. API change: `polyfill()` → `polygon_to_cells()` (or `geo_to_cells()`).
  - Pre-compute centroids and parent in grid generation (one-time cost) avoids Spark recompute on every analytical query.
  - Snappy compression — Spark default, good speed/size trade-off.

### D-030 | Flow 3 Renaming Post-Merge

**Date:** 2026-06-04 (Day 3 prep)
**Original filename:** `flow_03_h3_grid_generate.yaml`
**Renamed to:** `flow_03_taxi_zones_and_h3_grid.yaml`
**Rationale:** Flow 3 now produces 2 outputs (taxi zones reference GeoJSON + H3 grid Parquet) as a consequence of D-027 merge. Original name only reflected H3 output, misleading on full responsibility.
**Updates required:** File naming section in DECISIONS.md to be updated.

### D-031 | PostGIS Depth Deferred to Week 5-6 (Option 3)
**Date:** 2026-06-05 (Day 4)
**Decision:** Flow 2 ingest OSM streets ke GCS GeoParquet (pyosmium/GeoPandas),
TIDAK direct-to-PostGIS. PostGIS depth dipindah ke Week 5-6 sebagai serving-layer work:
  - osm2pgsql replay dari GCS GeoParquet → Supabase PostGIS
  - Advanced spatial queries: ST_DWithin H3 cells ke nearest road,
    street density per H3, spatial join streets × taxi zones
  - pgvector OPTIONAL (D-PENDING-1): embedding street/neighborhood descriptors,
    evaluate hanya jika Week 5 on-schedule
**Rationale:** Preserve D-010 lake architecture (GCS → Spark → BQ → dbt → serve).
  osm2pgsql output target = PostGIS table, tidak fit raw-zone GCS landing.
  PostGIS gap closure tetap tercapai via serving layer, tanpa decision-retract D-010
  dan tanpa scope explosion di Day 4. Opsi 2 (osm2pgsql di Flow 2) ditolak:
  break lake pattern + 12-15jam scope + Supabase 500MB limit risk.
**Supersedes:** D-019 amendment "osm2pgsql" (reverted to pyosmium primary)

### D-032 | OSM Source: NY State Extract, Not US Northeast
**Date:** 2026-06-05 (Day 4)
**Decision:** Geofabrik New York state extract (465 MB) sebagai sumber OSM Flow 2,
bukan US Northeast bundle (1.6 GB).
URL: https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf
**Rationale:** Northeast = NY + Boston + Pennsylvania, 3.5x lebih besar untuk data
yang ~90% di luar scope. NY state sudah mencakup NYC, crop ke 5 borough via bbox.
Bandwidth + memory + waktu proses turun signifikan. URL + size verified 2026-06-05.

### D-033 | Flow 2 Filter: Drivable Highway Classes Only
**Date:** 2026-06-05 (Day 4)
**Decision:** Include hanya: motorway, trunk, primary, secondary, tertiary +
semua _link variants, residential, unclassified, living_street.
Exclude: footway, cycleway, path, pedestrian, steps, bridleway, track, service.
**Rationale:** Taxi supply-demand = drivable network only. Footpath/cycleway
meng-inflate street density per H3 di zona yang taxi tidak operate. Filter ini
maps ke OSM functional road hierarchy = ekuivalen road-class logic GRAB routing.
`service` (driveway, parking_aisle, alley) di-exclude sebagai noise.

### D-034 | Flow 2 Spatial Clip: bbox v1, Polygon Refinement Deferred
**Date:** 2026-06-05 (Day 4)
**Decision:** Clip NY → NYC pakai bbox (-74.26, 40.49, -73.70, 40.92) di Flow 2 v1.
Polygon clip presisi pakai nyc_taxi_zones.geojson = future refinement, bukan blocker.
**Rationale:** bbox rectangular include sedikit edge NJ + water, tapi harmless untuk
road data (tidak ada drivable way di air). Polygon clip lebih presisi tapi tambah
GCS dependency di task — defer sampai terbukti perlu, hindari over-engineering v1.

### D-035 | Flow 2 OOM Incident — Architectural Lesson + Fix
**Date:** 2026-06-05 (Day 4)
**Incident:** Flow 2 v1 (single Python task, 465 MB PBF + locations=True)
triggered OOM mid-execution. Kestra JVM killed as collateral damage.
Root cause: total Codespaces memory = OS (~1GB) + Kestra JVM (~800MB)
+ postgres (~200MB) + Python Docker task node cache (~3GB) = exceeds 8GB.
**Key observation:** GCS write completed BEFORE Kestra crashed. Execution
marked RUNNING (inconsistent state) but data landed correctly.
**Why safe:** GCS object writes are atomic — file either exists complete
or not at all, no partial write possible. Idempotent design (overwrite)
made re-run safe regardless.
**Fix (v2):** osmium-tool pre-crop to NYC bbox in beforeCommands, BEFORE
Python task runs. NY state PBF (465 MB) → NYC PBF (~30-50 MB) via C++
CLI. Python task memory: 3 GB → ~300 MB. No OOM.
**Lesson:** Jupyter is NOT a reliable memory canary for Kestra Docker
tasks. Jupyter runs in host process memory; Kestra adds JVM + postgres
overhead before task container even starts.
**Validated output:** 8,739,248 bytes, EPSG:4326, ~72K drivable segments.

### D-036 | Kestra Deployment: Dev vs Production Pattern
**Date:** 2026-06-05 (Day 4)
**Current (portfolio):** Kestra + postgres + task containers co-located
di Codespaces Docker Compose. Acceptable untuk development.
**Production pattern:** Orchestrator resource-isolated dari task execution.
Achieved dua cara:
  1. Separate VM untuk orchestrator vs task workers (enterprise)
  2. Task execution di-offload ke managed service (lo sudah implement
     ini untuk Week 3: Kestra → Dataproc job submission. Spark cluster
     berjalan terpisah di GCP, Kestra JVM tetap ringan.)
**Why Flow 2 hit OOM:** Exception — heavy Python task jalan lokal
(bukan managed service), co-located dengan Kestra. Fixed via osmium
pre-crop (D-035). Future heavy local tasks: evaluate Cloud Run atau
Dataproc custom container sebelum commit ke Python Script task.

### D-038 | Dataproc Cluster Configuration v1
**Date:** 2026-06-05 (Day 4, post-ingestion phase)
**Decision:** Standard Spark cluster (non-HA, non-autoscaling) untuk Week 3 H3 enrichment.

**Sizing:**
- Master: 1 × n2-standard-2 (2 vCPU, 8 GB RAM)
- Workers: 2 × n2-standard-2 (minimum Dataproc requirement)
- Boot disk: 100 GB pd-standard per node
- Estimated cost: ~$0.25/hour saat running

**Software:**
- Image: 2.2-debian12 (Spark 3.5, stable)
- Optional component: JUPYTER (interactive debugging via Component Gateway)
- Spark properties: AQE enabled (mitigasi data skew Manhattan H3 cells)

**Cost protection:**
- `idle_delete_ttl = 1800s` — cluster auto-destroy setelah 30 menit idle.
  Mitigates "lupa shutdown" risk → max wasted billing = ~$0.12 per insiden.

**Excluded from v1 (deferred decisions):**
- Preemptible workers (D-PENDING-2): defer sampai job berjalan stable.
  Adding eviction handling sebelum job logic validated = premature optimization.
- Apache Sedona init action: defer. Sedona via `--packages` per job submission
  cukup untuk Flow 4. Init action = berlaku saat Week 5-6 perlu advanced spatial.
- Autoscaling policy: defer sampai workload behavior dipahami.

**Rationale:** Portfolio scale doesn't justify HA master atau large worker pool.
2-worker config cukup untuk 40M rows TLC + H3 enrichment via Sedona-less h3-py UDF.
Component Gateway enables Spark UI debugging dari browser — penting untuk
demonstrate troubleshooting di interview narrative ("I caught skewed partition
via Spark UI lineage view").

### D-039 | Raster Component DROPPED from NYC Taxi Project
**Date:** 2026-06-05 (Day 4)
**Decision:** Tidak ada raster/elevation component di NYC Taxi
Supply-Demand portfolio. Project tetap 100% vector-based
(H3 cells + OSM streets + Taxi zones polygon).

**Reasoning:**
- Original justification (close Pano AI JD raster gap) sudah collapse —
  Pano AI posting confirmed UNAVAILABLE June 2026.
- Tidak ada analytical use case untuk raster di NYC flat geography
  (elevation 0-50m, no meaningful topographic variation).
- Force-fit raster tanpa use case = "checkbox feature," low portfolio signal,
  high effort-to-value ratio.

**Pivot positioning:** Portfolio positioning sebagai vector-DE specialist
untuk class of geospatial roles (Mapbox, Esri, Carto, Foursquare, Overture,
Uber/DoorDash geo teams, geospatial startups). 

**Parked sebagai future portfolio project (BUKAN current scope):**
Indonesia dynamic pricing portfolio. Identified industry problem:
Grab/Gojek flat pricing tidak account untuk topography di highland routes
(Puncak, Lembang, Dieng, Bromo, Toba access). Solution sketch: elevation
per H3/geohash sebagai dynamic price multiplier.
Re-evaluate post Week 8 NYC project completion.

**Reference bookmarks (untuk future Indonesia project, BUKAN current):**
- orofarne/scenic-routing-mcp — Valhalla scenic routing pattern
- USGS 3DEP / NASA SRTM — DEM data sources
- Apache Sedona raster module — Spark geospatial raster processing

Filter criteria:
- pickup_datetime IS NOT NULL AND dropoff_datetime IS NOT NULL
- dropoff_datetime > pickup_datetime
- DATEDIFF(dropoff, pickup) <= 180 menit
- PULocationID/DOLocationID IS NOT NULL AND NOT IN (264, 265)
- passenger_count BETWEEN 1 AND 8
- trip_distance BETWEEN 0.1 AND 100
- fare_amount BETWEEN 2.50 AND 500
- total_amount BETWEEN 2.50 AND 500

## 2026-06-02 pipepline naming

kestra/flows/
├── flow_01_tlc_parquet_to_gcs.yaml          ← raw layer (done Day 2)
├── flow_02_osm_pbf_to_gcs.yaml              ← raw layer (TBD)
├── flow_03_taxi_zones_and_h3_grid.yaml      ← raw + derived (Day 3)
└── flow_04_spark_h3_enrichment.yaml         ← transform layer (later)