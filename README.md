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
- [ ] GCP infrastructure (Terraform)
- [ ] Kestra ingestion pipeline
- [ ] PySpark H3 processing
- [ ] dbt models
- [ ] Streamlit dashboard
