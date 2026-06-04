# NYC Taxi Supply-Demand Gap Analysis

> Identifying underserved zones and lost revenue windows using spatial aggregation and H3 indexing.

## Business Questions
1. Which H3 zones are consistently high-demand but low-supply during peak hours?
2. What is the estimated revenue loss from supply-demand gaps?
3. What predictable temporal patterns (hour/day) exist?

## Stack
| Layer | Tool |
|---|---|
| Orchestration | Kestra |
| Infrastructure | Terraform + GCP |
| Processing | Dataproc / PySpark |
| Warehouse | BigQuery |
| Transformation | dbt |
| Spatial DB | Supabase / PostGIS |
| Serving | Streamlit |

## Data Source
NYC TLC Yellow Taxi 2023 Jan–Jun  
Direct Parquet download: `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-0{1-6}.parquet`

## Architecture
## Project Status
- [x] Repository setup
- [x] GCP infrastructure (Terraform)
- [x] Kestra ingestion pipeline
- [ ] PySpark H3 processing
- [ ] dbt models
- [ ] Streamlit dashboard


kestra/flows/
├── flow_01_tlc_parquet_to_gcs.yaml          ← raw layer (done)
├── flow_02_osm_pbf_to_gcs.yaml              ← raw layer (TBD)
├── flow_03_taxi_zones_and_h3_grid.yaml      ← raw + derived (done)
└── flow_04_spark_h3_enrichment.yaml         ← transform layer (later)

✅ GCS Raw Layer:
├── raw/tlc_yellow/year=2023/month={01..12}/yellow_tripdata_*.parquet  (12 files, 606 MB)
├── raw/reference/nyc_taxi_zones.geojson                                (3.8 MB)
└── raw/h3_grid/h3_res8_nyc.parquet                                     (~80 KB, 1,070 cells)

⏳ Pending:
├── Flow 2 — OSM PBF streets ingestion
├── Flow 4 — Spark H3 enrichment (trip × H3 cell join)
├── BQ raw layer load
├── dbt staging/marts
├── Supabase PostGIS sync
└── Streamlit dashboard