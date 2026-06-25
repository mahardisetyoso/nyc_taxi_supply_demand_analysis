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
**Rationale:** Business Question #3 (temporal patterns) requires annual seasonality detection — winter dropoff, summer surge, holiday spikes. H1 only cannot show the full cycle.
**Trade-off accepted:** 2x storage + 2x Spark processing cost (~$3-5 incremental, negligible against free trial credit).
**Lock:** Full year 2023. No expansion to multi-year.

### D-004 | Predictive Element — Evaluate Later
**Date:** 2026-06-01 (Day 1)
**Decision:** Consider a simple time series forecast (BigQuery ML ARIMA_PLUS) for business question #3. Evaluate in Week 5, not now.
**Rationale:** Shifts framing from descriptive (2018-era) to predictive (2026-relevant). Must not add scope prematurely.
**Status:** PENDING — revisit in Week 5.

---

## DECISIONS — DATA SOURCE

### D-005 | TLC Data via CloudFront, Not Socrata API
**Date:** 2026-06-01 (Day 1)
**Decision:** Direct Parquet download from TLC CloudFront URLs.
**URL Pattern:** `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-{01-12}.parquet`
**Rationale:** Full dataset (not sampled), PySpark-native format, predictable URL pattern for Kestra orchestration. Socrata API = sampled data + rate limits.
**Lock:** No switching to Socrata for trip records.
**Attribution note:** Trip records are sourced from TLC CloudFront. NYC Open Data (Socrata) is used **only** for the taxi-zone geometry (see D-027) — it must not be credited as the source of the trip records.

### D-006 | Additional Data Sources
**Date:** 2026-05-31 (Day 0)
**Decision:** 4 data sources total:
1. NYC TLC Yellow Taxi Parquet (CloudFront) — trip events
2. OSM Street Data (Geofabrik PBF) — road network context
3. H3 Grid Table (generated via Python h3-py) — spatial aggregation unit
4. NYC Taxi Zone boundaries (official GeoParquet) — zone reference
**Rejected:** NYC Census/PLUTO as a demand proxy — insufficient value for the added complexity.

---

## DECISIONS — ARCHITECTURE & STACK

### D-007 | Spatial Aggregation Unit — H3 Resolution 8
**Date:** 2026-05-31 (Day 0)
**Decision:** H3 resolution 8 (~460m hexagon) as the primary analysis unit.
**Rationale:** Balance between granularity and query performance. Res 7 too coarse (~1.2km), res 9 too granular (~175m) for supply-demand analysis.
**Lock:** Fixed. No switching to S2, Geohash, or a different resolution.

### D-008 | H3 Over S2 or Geohash
**Date:** 2026-06-01 (Day 1)
**Decision:** H3 hexagonal indexing, not Google S2 cells or Geohash.
**Rationale:** H3 has uniform adjacency (6 neighbors vs variable in S2 quads), more natural for supply-demand spatial analysis because the distance to all neighbors is equal. H3 is the de facto standard post-2024 — native support in BigQuery, Snowflake, Databricks.
**Interview note:** If asked "why not S2?" — reference that Gojek ATLAS (2018) used S2 when H3 wasn't mature yet. H3 is the 2026 choice.

### D-009 | Dual Database Strategy
**Date:** 2026-05-31 (Day 0)
**Decision:** BigQuery for the analytical workload + Supabase/PostGIS for spatial queries.
**Rationale:** PostGIS is the primary skill gap being closed. Supabase = cloud-native PostgreSQL + PostGIS extension, already familiar from a previous portfolio. Not redundant architecture — each serves a distinct role.
**Technical justification:** "BigQuery is optimal for large-scale analytics; PostGIS/Supabase for spatial operations requiring native geometry functions (ST_Within, ST_Distance, buffer analysis)."

### D-010 | Full Stack Definition
**Date:** 2026-05-31 (Day 0)
**Decision:** Kestra → GCS → Dataproc/PySpark → BigQuery → dbt → Streamlit + Supabase/PostGIS
**Rationale:** Every tool has a specific justification. Nothing added to "look impressive."
**Lock:** No additional tools without an explicit decision entry here.

### D-011 | Terraform as IaC
**Date:** 2026-06-01 (Day 1)
**Decision:** Terraform for all GCP resource provisioning.
**Rationale:** Industry standard, reproducible, version controlled. Separation of config (variables.tf) from resources (main.tf).

---

## DECISIONS — GCP INFRASTRUCTURE

### D-012 | Separate GCP Project
**Date:** 2026-06-01 (Day 1)
**Decision:** New project `hardy-geo-portofolio`, fully isolated from the bootcamp course.
**Rationale:** Complete isolation — billing, credentials, and resources do not mix. The portfolio must stand alone.

### D-013 | Region Selection
**Date:** 2026-05-31 (Day 0)
**Decision:** asia-southeast1 (Singapore).
**Rationale:** Low latency from Jakarta. Consistent across all resources (GCS, BigQuery, Dataproc).

### D-014 | GCS Bucket Configuration
**Date:** 2026-06-01 (Day 1)
**Decision:** Bucket name `hardy-geo-de-267342`, STANDARD storage class, 90-day lifecycle delete rule.
**Rationale:** Globally unique name. 90 days is sufficient for the full development cycle.

### D-015 | BigQuery Dataset Separation
**Date:** 2026-06-01 (Day 1)
**Decision:** Two datasets — `geoops_raw` (raw ingested data) and `geoops_dbt_dev` (dbt-transformed models).
**Rationale:** Separation of concerns. Raw and transformed data must not coexist in the same dataset.

### D-016 | Service Account Roles
**Date:** 2026-06-01 (Day 1)
**Decision:** Service account `terraform-runner` with roles: Storage Admin, BigQuery Admin, Dataproc Administrator.
**Rationale:** Minimum roles required for Terraform provisioning + future Dataproc cluster creation.

---

## DECISIONS — DOCKER & KESTRA

### D-017 | Kestra Lean Setup
**Date:** 2026-06-01 (Day 1)
**Decision:** Docker Compose with only 2 services — kestra + kestra_postgres. No pgdatabase, no pgAdmin.
**Rationale:** The portfolio pipeline does not need a local Postgres. Data flows directly to GCS → BigQuery.

### D-018 | GCP Credentials via .env File
**Date:** 2026-06-01 (Day 1)
**Decision:** Base64-encoded JSON key stored in a `.env` file, auto-read by Docker Compose.
**Rationale:** Simpler than the KV-store approach. `.env` is gitignored. No manual export needed per session.

---

## DECISIONS — INGESTION ARCHITECTURE

### D-019 | Three Separate Kestra Flows
**Date:** 2026-06-01 (Day 1)
**Decision:** 3 independent flows, not 1 monolith:
- Flow 1: TLC Parquet → GCS (no Python, Kestra-native HTTP + GCS tasks)
- Flow 2: OSM PBF → Python processing (osmium/GeoPandas) → GCS
- Flow 3: H3 grid generation (Python h3-py) → GCS
**Rationale:** Independent execution — if one fails, the others continue. Easier to debug, test, and maintain individually.

### D-020 | Flow Execution Priority
**Date:** 2026-06-01 (Day 1)
**Decision:** Build order: Flow 1 first (TLC), then Flow 3 (H3), then Flow 2 (OSM).
**Rationale:** Flow 1 is simplest and immediately produces queryable data — a quick win for momentum. OSM processing is the most complex, so it is saved for last.

---

## DECISIONS — SPARK PERFORMANCE

### D-021 | Pre-Planned Spark Performance Mitigations
**Date:** 2026-06-01 (Day 1)
**Decision:** Four mitigations decided before writing any Spark code:
1. **Broadcast join** for zone tables (~300 rows) — eliminates shuffle entirely
2. **Salting** for skewed H3 keys (Manhattan hotkey problem)
3. **AQE enabled** (`spark.sql.adaptive.enabled = true`) — auto-rebalance partitions
4. **Coalesce before write** — target file size 128MB-1GB, prevents the small-files problem
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
**Rationale:** Lead with one audience for the 90-day focus. Audience dilution (recruiters + engineers + general users) reduces impact.

### D-024 | Schema Optimization as Content, Not Headline
**Date:** 2026-05-31 (Day 0)
**Decision:** Schema & Query Optimization enters as a content angle (LinkedIn/Medium posts), not as the portfolio headline.
**Rationale:** Demonstrates engineering depth without altering the problem statement. Potential for 2-3 posts on "Why I designed my schema this way."

### D-025 | Modern Framing vs 2018 Approaches
**Date:** 2026-06-01 (Day 1)
**Decision:** Explicitly position the project as a "2026 approach" — H3 (not S2), dbt (not custom aggregation), BigQuery (not a custom time series DB), Terraform (not custom IaC), Kestra (not custom orchestration).
**Rationale:** Gojek ATLAS (2018) had to custom-build because managed tools weren't mature. In 2026, the value is in selecting the right tools and connecting them end-to-end, not reinventing infrastructure.
**Interview framing:** "I can deliver equivalent analytical value using an open-source managed stack, demonstrating that I know how to choose the right tools — not just build everything from scratch."

---

## DECISIONS — ANTI-PATTERNS (DO NOT DO)

### D-026 | Scope Creep Prevention Protocol
**Date:** 2026-05-31 (Day 0)
**Decision:** Every temptation to add data sources, switch tools, or expand scope must be logged here with the reasoning for its rejection.
**Rationale:** Parallel polish is an identified behavioral pattern. Single-focus commitment is the counter-strategy.

---

## AMENDMENT LOG

| Date | Decision | Change | Justification |
|---|---|---|---|
| 2026-06-02 | D-003 → D-003a | Scope expanded from Jan-Jun to Jan-Dec 2023 | Q3 temporal patterns require annual seasonality detection |

---

## 2026-06-02 — Flow 1 Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| GCS path layout | Hive-partitioned: `raw/tlc_yellow/year=YYYY/month=MM/` | Enables Spark partition pruning + BQ external-table auto-detect. Industry pattern. |
| Scope expansion | 2023 Jan–Dec (12 months), from the initial 6 months | Q3 (temporal patterns) requires annual seasonality detection. Trade-off: 2x cost (~$3-5 incremental, negligible vs free credit). |
| Execution pattern | Single-month YAML + disabled schedule trigger + Kestra Backfill UI | Demonstrates a production pattern (scheduled + backfillable) without committing to a live cron. |
| Raw landing validation | Inline size check only (< 10MB = fail) | Pragmatic for the Flow 1 raw layer. Deep validation (schema, row count) is deferred to the transform layer in dbt. |
| Idempotency | Overwrite GCS objects on re-run. Source data is immutable (TLC CloudFront). | Versioning the GCS filename does not reach dbt reproducibility (the chain breaks at GCS→BQ). Reproducibility is instead delivered via PySpark-injected metadata columns (`_ingested_at`, `_source_file`) in the BQ raw table — implemented later in the Spark flow. |
| Kestra namespace | `geoops.portfolio.raw` | Hierarchy scales to `transform` + `serve` layers. |

---

## DECISIONS — FLOW 3 PREP (TAXI ZONES + H3 GRID)

### D-006a | AMENDMENT — Remove H3 Grid from Data Sources List
**Date:** 2026-06-04 (Day 3 prep)
**Original D-006:** 4 data sources — TLC Parquet, OSM, H3 Grid, NYC Taxi Zones.
**Amended:** 3 data sources — TLC Parquet, OSM, NYC Taxi Zones.
**Rationale:** H3 Grid is removed from "data sources" — it is a derived dataset computed from Taxi Zones (see D-027), not an ingested source. Categorizing computed data as a data source conflated the raw and derived layers.

### D-027 | NYC Taxi Zones as Single Spatial Reference Source [MERGED]
**Date:** 2026-06-04 (Day 3 prep)
**Decision:** The NYC Taxi Zones GeoJSON serves a dual purpose as the single spatial reference source.
**Dual purpose:**
  1. **Spatial reference / lookup** — PULocationID and DOLocationID in TLC trips ↔ zone name + borough
  2. **H3 polyfill source** — union 263 zone polygons → polyfill at res 8 → ~12K H3 cells (later corrected to ~1,070; see granularity note below)

**Rationale for the merge (vs the initially planned separate boroughs source):**
  - Single source-of-truth for NYC spatial geometry
  - Consistent coverage — the H3 grid covers exactly the same area as the analytical zone lookup
  - No mismatch risk between "where can H3 cells exist" and "where can trips be assigned"
  - Native join with TLC trip data via `locationid` (matches PULocationID/DOLocationID)

**Source:** NYC Open Data — "NYC Taxi Zones" dataset (ID: `8meu-9t5y`)
**Verified URL (2026-06-04):** `https://data.cityofnewyork.us/api/geospatial/8meu-9t5y?method=export&format=GeoJSON`

**API pattern:** Socrata geospatial export — returns the full dataset in a single response, no pagination required.
**Verified payload structure:** `FeatureCollection` with 263 features; properties = `{shape_area, locationid, shape_leng, zone, borough}`; geometry = `MultiPolygon`.

**Trade-off accepted:**
  - 263-polygon union polyfill (~10s) vs 5-borough union polyfill (~1s)
  - A one-time cost during H3 grid generation, negligible for portfolio scope
  - At production scale, dissolved geometry would be pre-computed if rebuilds become frequent

**Storage outputs (Flow 3, Day 3 build):**
  - `gs://hardy-geo-de-267342/raw/reference/nyc_taxi_zones.geojson` (~1-2 MB)
  - `gs://hardy-geo-de-267342/raw/h3_grid/h3_res8_nyc.parquet` (~80 KB, ~1,070 rows, centroid-containment mode)

**Granularity confirmed via Jupyter prototype (2026-06-04):** 1,070 H3 cells cover NYC's ~784 km² (math: 1070 × 0.737 km²/cell = 789 km², matching expectation). The initial estimate of ~12K cells was incorrect — caught during pre-production validation.

**Lock:** No fallback to a separate boroughs source. Taxi zones = the single spatial reference for the entire project.

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
  - H3 v4 = the 2026 current standard. v3 is deprecated. API change: `polyfill()` → `polygon_to_cells()` (or `geo_to_cells()`).
  - Pre-computing centroids and parent in grid generation (a one-time cost) avoids Spark recompute on every analytical query.
  - Snappy compression — Spark default, a good speed/size trade-off.

### D-030 | Flow 3 Renaming Post-Merge
**Date:** 2026-06-04 (Day 3 prep)
**Original filename:** `flow_03_h3_grid_generate.yaml`
**Renamed to:** `flow_03_taxi_zones_and_h3_grid.yaml`
**Rationale:** Flow 3 now produces 2 outputs (taxi-zones reference GeoJSON + H3 grid Parquet) as a consequence of the D-027 merge. The original name only reflected the H3 output, which was misleading about its full responsibility.
**Updates required:** The file-naming section in DECISIONS.md is to be updated.

### D-031 | PostGIS Depth Deferred to Week 5-6 (Option 3)
**Date:** 2026-06-05 (Day 4)
**Decision:** Flow 2 ingests OSM streets to GCS GeoParquet (pyosmium/GeoPandas), **not** direct-to-PostGIS. PostGIS depth is moved to Week 5-6 as serving-layer work:
  - osm2pgsql replay from GCS GeoParquet → Supabase PostGIS
  - Advanced spatial queries: ST_DWithin from H3 cells to nearest road, street density per H3, spatial join of streets × taxi zones
  - pgvector OPTIONAL (D-PENDING-1): embedding street/neighborhood descriptors — evaluate only if Week 5 is on schedule
**Rationale:** Preserve the D-010 lake architecture (GCS → Spark → BQ → dbt → serve). The osm2pgsql output target is a PostGIS table, which does not fit the raw-zone GCS landing. The PostGIS gap is still closed via the serving layer, without retracting D-010 and without scope explosion on Day 4. Option 2 (osm2pgsql in Flow 2) was rejected: it breaks the lake pattern, adds 12-15h of scope, and risks the Supabase 500MB limit.
**Supersedes:** the D-019 amendment "osm2pgsql" (reverted to pyosmium as primary).

### D-032 | OSM Source: NY State Extract, Not US Northeast
**Date:** 2026-06-05 (Day 4)
**Decision:** Use the Geofabrik New York state extract (465 MB) as the OSM source for Flow 2, not the US Northeast bundle (1.6 GB).
**URL:** `https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf`
**Rationale:** Northeast = NY + Boston + Pennsylvania, 3.5x larger for data that is ~90% out of scope. NY state already covers NYC; crop to the 5 boroughs via bbox. Bandwidth, memory, and processing time all drop significantly. URL + size verified 2026-06-05.

### D-033 | Flow 2 Filter: Drivable Highway Classes Only
**Date:** 2026-06-05 (Day 4)
**Decision:** Include only: motorway, trunk, primary, secondary, tertiary + all `_link` variants, residential, unclassified, living_street. Exclude: footway, cycleway, path, pedestrian, steps, bridleway, track, service.
**Rationale:** Taxi supply-demand = the drivable network only. Footpaths/cycleways inflate street density per H3 in zones where taxis don't operate. This filter maps to the OSM functional road hierarchy — equivalent to GRAB's road-class routing logic. `service` (driveways, parking aisles, alleys) is excluded as noise.

### D-034 | Flow 2 Spatial Clip: bbox v1, Polygon Refinement Deferred
**Date:** 2026-06-05 (Day 4)
**Decision:** Clip NY → NYC using a bbox (-74.26, 40.49, -73.70, 40.92) in Flow 2 v1. Precise polygon clipping using `nyc_taxi_zones.geojson` is a future refinement, not a blocker.
**Rationale:** The rectangular bbox includes a little edge of NJ + water, but that is harmless for road data (there are no drivable ways on water). Polygon clipping is more precise but adds a GCS dependency to the task — defer until proven necessary, to avoid over-engineering v1.

### D-035 | Flow 2 OOM Incident — Architectural Lesson + Fix
**Date:** 2026-06-05 (Day 4)
**Incident:** Flow 2 v1 (a single Python task, 465 MB PBF + `locations=True`) triggered an OOM mid-execution. The Kestra JVM was killed as collateral damage. Root cause: total Codespaces memory = OS (~1GB) + Kestra JVM (~800MB) + postgres (~200MB) + Python Docker task node cache (~3GB) = exceeds 8GB.
**Key observation:** The GCS write completed BEFORE Kestra crashed. The execution was marked RUNNING (an inconsistent state) but the data landed correctly.
**Why it was safe:** GCS object writes are atomic — a file either exists complete or not at all; no partial write is possible. The idempotent design (overwrite) made the re-run safe regardless.
**Fix (v2):** osmium-tool pre-crop to the NYC bbox in `beforeCommands`, BEFORE the Python task runs. NY state PBF (465 MB) → NYC PBF (~30-50 MB) via the C++ CLI. Python task memory: 3 GB → ~300 MB. No OOM.
**Lesson:** Jupyter is NOT a reliable memory canary for Kestra Docker tasks. Jupyter runs in host-process memory; Kestra adds JVM + postgres overhead before the task container even starts.
**Validated output:** 8,739,248 bytes, EPSG:4326, ~72K drivable segments.

### D-036 | Kestra Deployment: Dev vs Production Pattern
**Date:** 2026-06-05 (Day 4)
**Current (portfolio):** Kestra + postgres + task containers co-located in Codespaces Docker Compose. Acceptable for development.
**Production pattern:** The orchestrator is resource-isolated from task execution. Achieved two ways:
  1. Separate VMs for the orchestrator vs task workers (enterprise)
  2. Task execution offloaded to a managed service (already implemented for Week 3: Kestra → Dataproc job submission. The Spark cluster runs separately on GCP, so the Kestra JVM stays light.)
**Why Flow 2 hit OOM:** An exception — a heavy Python task ran locally (not on a managed service), co-located with Kestra. Fixed via the osmium pre-crop (D-035). For future heavy local tasks: evaluate Cloud Run or a Dataproc custom container before committing to a Python Script task.

### D-038 | Dataproc Cluster Configuration v1
**Date:** 2026-06-05 (Day 4, post-ingestion phase)
**Decision:** A standard Spark cluster (non-HA, non-autoscaling) for the Week 3 H3 enrichment.

**Sizing:**
- Master: 1 × n2-standard-2 (2 vCPU, 8 GB RAM)
- Workers: 2 × n2-standard-2 (minimum Dataproc requirement)
- Boot disk: 100 GB pd-standard per node
- Estimated cost: ~$0.25/hour while running

**Software:**
- Image: 2.2-debian12 (Spark 3.5, stable)
- Optional component: JUPYTER (interactive debugging via Component Gateway)
- Spark properties: AQE enabled (mitigates data skew on Manhattan H3 cells)

**Cost protection:**
- `idle_delete_ttl = 1800s` — cluster auto-destroys after 30 minutes idle. Mitigates the "forgot to shut down" risk → max wasted billing = ~$0.12 per incident.

**Excluded from v1 (deferred decisions):**
- Preemptible workers (D-PENDING-2): defer until the job runs stably. Adding eviction handling before the job logic is validated = premature optimization.
- Apache Sedona init action: defer. Sedona via `--packages` per job submission is sufficient for Flow 4. An init action applies when Week 5-6 needs advanced spatial work.
- Autoscaling policy: defer until the workload behavior is understood.

**Rationale:** Portfolio scale doesn't justify an HA master or a large worker pool. The 2-worker config is sufficient for 40M rows of TLC + H3 enrichment via a Sedona-less h3-py UDF. Component Gateway enables Spark UI debugging from the browser — important for demonstrating troubleshooting in the interview narrative ("I caught a skewed partition via the Spark UI lineage view").

### D-039 | Raster Component DROPPED from NYC Taxi Project
**Date:** 2026-06-05 (Day 4)
**Decision:** No raster/elevation component in the NYC Taxi Supply-Demand portfolio. The project stays 100% vector-based (H3 cells + OSM streets + taxi-zone polygons).

**Reasoning:**
- The original justification (closing the Pano AI JD raster gap) has collapsed — the Pano AI posting was confirmed UNAVAILABLE as of June 2026.
- There is no analytical use case for raster in NYC's flat geography (elevation 0-50m, no meaningful topographic variation).
- Force-fitting raster without a use case = a "checkbox feature": low portfolio signal, high effort-to-value ratio.

**Pivot positioning:** Position the portfolio as a vector-DE specialist for a class of geospatial roles (Mapbox, Esri, Carto, Foursquare, Overture, Uber/DoorDash geo teams, geospatial startups).

**Parked as a future portfolio project (NOT current scope):** an Indonesia dynamic-pricing portfolio. Identified industry problem: Grab/Gojek flat pricing does not account for topography on highland routes (Puncak, Lembang, Dieng, Bromo, Toba access). Solution sketch: elevation per H3/geohash as a dynamic price multiplier. Re-evaluate after the Week 8 NYC project completion.

**Reference bookmarks (for the future Indonesia project, NOT current):**
- orofarne/scenic-routing-mcp — Valhalla scenic-routing pattern
- USGS 3DEP / NASA SRTM — DEM data sources
- Apache Sedona raster module — Spark geospatial raster processing

### D-040 | Trip Filtering Strategy
**Date:** 2026-06-09 (Day 6 prep)
**Resolution:** Standard Clean (Option B)
**Criteria:**
- `pickup_datetime` & `dropoff_datetime` NOT NULL
- `dropoff_datetime` > `pickup_datetime`
- Trip duration ≤ 180 minutes (10,800 seconds)
- `PULocationID` & `DOLocationID` NOT NULL, NOT IN (264, 265)
- `passenger_count` BETWEEN 1 AND 8 [dtype: double — cast first]
- `trip_distance` BETWEEN 0.1 AND 100
- `fare_amount` BETWEEN 2.50 AND 500
- `total_amount` BETWEEN 2.50 AND 500

### D-041 | H3 Indexing Approach
**Date:** 2026-06-09 (Day 6 prep)
**Resolution:** Broadcast join via a lookup table
- Library: h3-py (consistent with Flow 3)
- Data confirmed: NO coordinates — `PULocationID` & `DOLocationID` are integer zone IDs, not lat/lng
- Approach: pre-build a LocationID → h3_cell lookup from `nyc_taxi_zones.geojson` + `h3_res8_nyc.parquet`, then broadcast-join to the trip data
- Apply to: `PULocationID` → `h3_pickup_res8`; `DOLocationID` → `h3_dropoff_res8`
- Sedona: Rejected (overkill, wrong bottleneck)

**D-041 ADDENDUM (from the prototype):**
- LocationID 56, 103 are duplicated in the GeoJSON → fix: `drop_duplicates(keep="first")`
- LocationID 57, 105 are absent from the GeoJSON → 36 rows dropped (0.001%)
- Aggregation: group by pickup/dropoff H3 independently, not nested

### D-042 | Aggregation Granularity
**Date:** 2026-06-09 (Day 6 prep)
**Resolution:** hour_of_day × day_of_week (168 buckets)
- Columns: `h3_cell | day_of_week (0–6) | hour_of_day (0–23)`
- Rationale: an ops-relevant weekly pattern, not a daily average that isn't actionable

### D-043 | Output Schema (BigQuery)
**Date:** 2026-06-09 (Day 6 prep)
**Resolution:** Row-level enriched
- Table: `geoops_raw.yellow_trips_h3_enriched`
- Type: 1 row = 1 trip (not pre-aggregated)
- New columns: `h3_pickup_res8`, `h3_dropoff_res8`, `day_of_week`, `hour_of_day`
- Partition: `DATE(tpep_pickup_datetime)`
- Clustering: `h3_pickup_res8`, `h3_dropoff_res8`
- Aggregation logic: delegated to dbt (Week 4)

---

# Day 6 Decisions — Flow 4 Production Implementation

## D-044 | Pre-computed H3 Lookup (Cluster Dependency Strategy)
**Date:** 2026-06-09
**Status:** LOCKED
**Context:** Dataproc cluster VMs have no external IP (org policy). `pip install` via an initialization action fails with `[Errno 101] Network is unreachable` on all 3 nodes (master + 2 workers). The libraries h3, geopandas, gcsfs are only needed on the driver to build the 260-row lookup table.

**Decision:** Pre-compute the LocationID → H3 lookup as a CSV in Codespaces (where geopandas/h3 are available), upload it to GCS, and have PySpark read the plain CSV. Zero external dependencies on the cluster.

**Artifact:** `gs://hardy-geo-de-267342/raw/reference/location_h3_lookup.csv`
- 260 rows (263 zones − 3 duplicates from LocationID 56/103)
- Columns: LocationID (int), h3_res8 (string)
- Generated via prototype notebook cells 5-9: GeoPandas centroid → h3.latlng_to_cell

**Production alternatives (documented, not implemented):**
1. **Cloud NAT** — a NAT gateway on the VPC; VMs stay private but can reach the internet. Standard enterprise pattern. ~$1/day.
2. **Custom Dataproc Image** — bake dependencies into the OS image. Netflix/Spotify/Uber pattern. Zero boot-time install.
3. **Private Artifact Registry** — an internal PyPI mirror inside the VPC. Corporate standard (Artifactory/Nexus).
4. **Pre-staged wheels on GCS** — download `.whl` files, `pip install --no-index`. For air-gapped environments.

**Why this is architecturally correct (not a shortcut):**
- Separation of concerns: reference-data preparation (the Flow 3 domain) vs the enrichment job (the Flow 4 domain)
- The lookup table is a static reference artifact — recomputing 260 rows at every cluster boot is waste
- The same pattern is used in production: dimension tables are pre-built, not rebuilt per job

---

## D-045 | TLC Schema Evolution Handling (Per-Month Read + Union)
**Date:** 2026-06-09
**Status:** LOCKED
**Context:** TLC changed the Parquet schema mid-2023. Reading all 12 files with a single `spark.read.parquet()` fails regardless of approach:
- Default read: `Expected: double, Found: INT64` (passenger_count)
- mergeSchema: `CANNOT_MERGE_INCOMPATIBLE_DATA_TYPE BIGINT and INT`
- Explicit schema + disabled vectorized reader: `MutableDouble cannot be cast to MutableLong`

**Schema differences discovered:**

| Column | Early 2023 | Late 2023 |
|---|---|---|
| VendorID | BIGINT | INT |
| passenger_count | DOUBLE | BIGINT |
| RatecodeID | DOUBLE | BIGINT |
| PULocationID | BIGINT | INT |
| DOLocationID | BIGINT | INT |
| airport_fee | airport_fee | Airport_fee (case!) |

**Decision:** Read each month separately, cast all columns to common types via `F.col().cast()`, then `unionByName`. This is the production pattern for schema evolution in multi-file Parquet datasets.

```python
COMMON_COLS = [
    F.col("VendorID").cast("long"),
    F.col("passenger_count").cast("double"),
    F.col("PULocationID").cast("long"),
    F.col("airport_fee").cast("double"),  # handles case mismatch
    # ... etc
]

dfs = []
for month in range(1, 13):
    path = f"gs://{BUCKET}/raw/tlc_yellow/year=2023/month={month:02d}/*.parquet"
    df_month = spark.read.parquet(path).select(COMMON_COLS)
    dfs.append(df_month)

df_raw = reduce(lambda a, b: a.unionByName(b), dfs)
```

**Why it wasn't caught in the prototype:** The prototype only processed January 2023. Schema changes only appear when reading multiple months. This validates the principle: prototyping on 1 month ≠ validated for 12 months.

**Lesson:** For any multi-file Parquet ingestion from an external source, always inspect the schema of ALL files before designing the read strategy.

---

## D-045a | TLC Schema Evolution — Amendment (January Outlier, Not Mid-Year Drift)
**Date:** 2026-06-25
**Status:** AMENDS D-045
**Trigger:** Schema diff inspection across all 12 months of 2023 TLC Yellow Taxi Parquet revealed the original D-045 framing was imprecise. Captured here for accuracy before publishing the bug-confession post on this finding.

**Corrected finding:** The schema did not "drift mid-2023." January 2023 is a **single-month outlier**. February through December 2023 are consistent. The transition happens at one discrete boundary (Feb 1, 2023), not gradually.

**Corrected schema diff table** (Month 01 vs Months 02-12, all consistent):

| Column | January 2023 | February–December 2023 | Change type |
|---|---|---|---|
| VendorID | int64 | int32 | Storage downcast (legacy waste) |
| passenger_count | double | int64 | Semantic correction (int stored as float) |
| RatecodeID | double | int64 | Semantic correction (int stored as float) |
| store_and_fwd_flag | string | large_string | Arrow representation (writer change) |
| PULocationID | int64 | int32 | Storage downcast |
| DOLocationID | int64 | int32 | Storage downcast |
| airport_fee → Airport_fee | `airport_fee` (lowercase) | `Airport_fee` (capital A) | **Column rename** — silent NULL trap |

**New column missed in original D-045:** `store_and_fwd_flag` (string → large_string). At the Spark layer this reads as StringType in both cases, but pyarrow-aware readers (Polars, direct Arrow ingestion) will see the difference.

**Most dangerous change:** The `airport_fee` → `Airport_fee` rename. Parquet column names are case-sensitive — these are treated as two separate columns at merge time, producing silent NULLs in 1/12 or 11/12 of the rows depending on which name the read targets. No error is raised; the data is just half-empty.

**Why the original framing was wrong:** The original D-045 entry described "early 2023" vs "late 2023" as if the change were gradual. The data shows the change is binary: one boundary, one date. Prototyping on January was prototyping on the only month from the legacy regime. The other 11 months were already on the new schema by the time the data was downloaded.

**Updated lesson (supersedes D-045):**
> Schema changes from external sources tend to ship at discrete boundaries (year start, quarter start, system migration date), not as gradual drift. The first file of a time series is statistically more likely to be from a legacy regime than later files. Inspect the first file with extra suspicion, not less.

**Action items embedded in fix:** No code change required — the `COMMON_COLS` + `unionByName` pattern in D-045 already handles this correctly because it casts every column at read. The fix is independent of how many months are outliers; the lesson is what changes.

**Reproducibility artifact:** `spark/schema_diff.py` — pyarrow-only script that downloads 12 monthly schemas from TLC CloudFront and diffs them against month 01. Runtime ~10 minutes on a residential connection. Output verified the table above on 2026-06-25.

**Forbidden inference for the LinkedIn post:** Do NOT claim "TLC ships schema changes every February." We have one data point (2023). Generalize from "first file is suspicious" only — that's a probabilistic claim about external time-series data in general, defensible from broader engineering experience, not from this single observation.

---

## D-046 | BigQuery Connector JAR (Dataproc 2.2 Built-in)
**Date:** 2026-06-09
**Status:** LOCKED
**Context:** Passing `--jars=gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.12-0.32.2.jar` at job submit caused `ServiceConfigurationError: BigQueryRelationProvider not a subtype`. Root cause: the Dataproc image 2.2-debian12 already includes the spark-bigquery-connector. Adding a second JAR creates a classpath conflict (two versions of the same class).

**Decision:** Do NOT pass `--jars` for the BigQuery connector when using Dataproc 2.2+. The pre-installed connector is sufficient.

**Submit command (final):**
```bash
gcloud dataproc jobs submit pyspark \
  gs://hardy-geo-de-267342/spark_jobs/flow4_h3_enrichment.py \
  --cluster=geoops-spark \
  --region=asia-southeast1 \
  --project=hardy-geo-portofolio
```

---

## Flow 4 Production Results
**Job ID:** dde1578b9bd0415daf87c88cf9315d55
**Runtime:** ~3 minutes (1 master + 2 workers, n2-standard-2)

```
Raw:      38,310,226 rows (12 months TLC Yellow 2023)
Filtered: 34,956,609 (8.8% dropped via D-040)
Final:    34,955,847 (762 null H3 dropped — LocationID 57/105)
Output:   hardy-geo-portofolio.geoops_raw.yellow_trips_h3_enriched
          Partition: DAY(tpep_pickup_datetime)
          Cluster:   h3_pickup_res8, h3_dropoff_res8
```

---

## Pipeline Naming (2026-06-02)

```
kestra/flows/
├── flow_01_tlc_parquet_to_gcs.yaml          ← raw layer (done Day 2)
├── flow_02_osm_pbf_to_gcs.yaml              ← raw layer (TBD)
├── flow_03_taxi_zones_and_h3_grid.yaml      ← raw + derived (Day 3)
└── flow_04_spark_h3_enrichment.yaml         ← transform layer (later)
```

---

## D-055 | Rate Aggregation: Aggregate Totals, Never Average Ratios
**Date:** 2026-06-11 (Day 8)
**Status:** LOCKED
**Context:** `mart_gap_zones` produced an `avg_unmet_demand_rate` as low as -41.26 for 171/185 zones. The map rendered all-red; the KPI "185 undersupplied" was false.

**Root cause:** `avg(unmet_demand_rate)` averaged per-bucket ratios. Buckets with demand ≈ 0 produced extreme rates (e.g. demand=1, supply=42 → rate=-41) that poisoned the zone average. The formula was mathematically correct per bucket but statistically invalid when averaged across buckets.

**Decision:** Compute zone-level rates as a "rate of totals": `safe_divide(sum(demand) - sum(supply), sum(demand))`, NOT `avg(rate)`. Split into three honest metrics: `unmet_demand_rate` [0,1], `supply_demand_ratio`, `oversupply_ratio`. `zone_status` uses a ±10% band (ratio 0.9–1.1 = BALANCED), replacing the magic-number threshold `-5`.

**Scope correction:** The mart now retains all 185 zones with correct classification (13 UNDERSUPPLIED, 13 BALANCED, 159 OVERSUPPLIED). Revenue loss is restricted to UNDERSUPPLIED zones only. The insight is reframed: a misallocation story (oversupply coexists with shortfall), not "185 zones need taxis."

**Guardrail:** dbt range tests on `unmet_demand_rate` [0,1] and `supply_demand_ratio` [0,∞), plus `accepted_values` on `zone_status`, block regression at build time.

**Principle:** Never average a ratio. Aggregate the numerator and denominator separately, then divide. Validate a metric's output range before shipping — a metric that renders is not a metric that is correct.

---

## D-056 | Local Dev Environment (Windows VS Code)
**Date:** Day 9
**Status:** LOCKED
**Trigger:** The GitHub Codespaces free quota (120 core-hrs/mo) was exhausted mid-month.
**Decision:** Migrate to local Windows VS Code instead of paying or waiting for the reset.
**Setup:** venv (not the conda base), `requirements.txt`, `profiles.yml` (oauth via ADC), `.env` with python-dotenv.
**Rationale:** A reproducible local environment is a production-grade skill and a portfolio signal.

## D-057 | OSM Road Density Analysis
**Date:** 2026-06-17 (Day 10)
**Finding:** Undersupplied zones avg 113.8 road segments vs oversupplied 95.1.
Road access is NOT the bottleneck — strengthens fleet misallocation argument.
LaGuardia (9 segments, $15M) vs JFK (192 segments, $26M) — both undersupplied
regardless of physical access. Dispatch/positioning is the root cause.
**Artifact:** osm_streets table in Supabase, road_segment_count column added.