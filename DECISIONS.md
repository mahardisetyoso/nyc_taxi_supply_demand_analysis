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


## 2026-06-02 pipepline naming
kestra/flows/
├── flow_01_tlc_parquet_to_gcs.yaml      ← raw layer
├── flow_02_osm_pbf_to_gcs.yaml          ← raw layer
├── flow_03_h3_grid_generate.yaml        ← raw layer
└── flow_04_spark_h3_enrichment.yaml     ← transform layer (later)