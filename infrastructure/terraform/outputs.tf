output "gcs_bucket" {
  description = "Raw data lake bucket"
  value       = google_storage_bucket.geoops_raw.url
}

output "bq_dataset_raw" {
  description = "BigQuery dataset for Spark output"
  value       = "${var.project}.${google_bigquery_dataset.geoops_raw.dataset_id}"
}

output "bq_dataset_dbt" {
  description = "BigQuery dataset for dbt models"
  value       = "${var.project}.${google_bigquery_dataset.geoops_dbt_dev.dataset_id}"
}

output "region" {
  value = var.region
}
