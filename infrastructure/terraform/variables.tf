variable "credentials" {
  description = "GCP Service Account Key"
  default     = "./keys/my-creds.json"
}

variable "project" {
  description = "GCP Project ID"
  default     = "hardy-geo-portofolio"
}

variable "region" {
  description = "GCP Region"
  default     = "asia-southeast1"
}

variable "location" {
  description = "GCP Location"
  default     = "ASIA-SOUTHEAST1"
}

variable "gcs_bucket_name" {
  description = "GCS Raw Data Bucket"
  default     = "hardy-geo-de-267342"
}

variable "bq_dataset_raw" {
  description = "BigQuery Raw Dataset"
  default     = "geoops_raw"
}

variable "bq_dataset_dbt" {
  description = "BigQuery dbt Dev Dataset"
  default     = "geoops_dbt_dev"
}
