# Decisions Log

Semua keputusan teknis yang sudah dibuat dan TIDAK dibuka ulang.

---

## 2026-06-01 — Data Source
**Keputusan:** Direct Parquet download dari TLC CloudFront URL, bukan Socrata API.  
**Alasan:** Full dataset, format native PySpark, URL pattern predictable untuk Kestra.  
**Scope:** Yellow Taxi only, Jan–Jun 2023. Fixed. Tidak ditambah.

## 2026-06-01 — Spatial Aggregation Unit  
**Keputusan:** H3 resolution 8 sebagai unit analisis utama.  
**Alasan:** Balance antara granularitas (~460m hexagon) dan query performance.

## 2026-06-01 — Dual Database Strategy
**Keputusan:** BigQuery untuk analytical workload, Supabase/PostGIS untuk spatial queries.  
**Alasan:** PostGIS gap di target JD (Pano AI). Supabase sudah familiar, production-grade.

## 2026-06-01 — GCP Region
**Keputusan:** asia-southeast1 (Singapore).  
**Alasan:** Latency dari Tokyo, konsisten dengan Zoomcamp setup.
