# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Identify underserved NYC taxi zones and estimate revenue loss from supply-demand gaps using H3 spatial indexing. Analyzes NYC TLC Yellow Taxi data (Jan–Jun 2023).

**Business questions:**
1. Which H3 zones are consistently high-demand but low-supply during peak hours?
2. What is the estimated revenue loss from supply-demand gaps?
3. What predictable temporal patterns (hour/day) exist?

## Stack

| Layer | Tool |
|---|---|
| Orchestration | Kestra |
| Infrastructure | Terraform + GCP (asia-southeast1) |
| Processing | Dataproc / PySpark |
| Warehouse | BigQuery |
| Transformation | dbt |
| Spatial DB | Supabase / PostGIS |
| Serving | Streamlit |

## Architecture Decisions (Locked — Do Not Reopen)

- **Data source:** Direct Parquet download from TLC CloudFront (`https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-0{1-6}.parquet`). Yellow Taxi only, Jan–Jun 2023. Scope is fixed.
- **Spatial unit:** H3 resolution 8 (~460m hexagons). Fixed.
- **Dual DB strategy:** BigQuery for analytical workloads; Supabase/PostGIS for spatial queries (PostGIS is a target skill for the project author).
- **GCP region:** `asia-southeast1` (Singapore). Fixed.

## Infrastructure

Terraform config lives in `infrastructure/terraform/`. Deploy with:

```bash
cd infrastructure/terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

`terraform.tfvars` and all `*.json` credential files are gitignored — never commit them.

## Credential / Secret Handling

The `.gitignore` blocks `*.json`, `keys/`, `credentials/`, `*creds*`, `*secret*`, `service_account*`, and `.env`. GCP service account keys must stay out of the repo.
