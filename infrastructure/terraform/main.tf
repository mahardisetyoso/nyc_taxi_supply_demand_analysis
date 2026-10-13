terraform {
  required_version = ">= 1.5" # import blocks

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.6.0"
    }
  }

  # Remote state (D-060). The bucket is created once by bootstrap.ps1 —
  # it cannot be managed here because the backend must exist before init.
  backend "gcs" {
    bucket = "hardy-geo-portofolio-tfstate"
    prefix = "nyc-taxi-supply-demand"
  }
}

provider "google" {
  # Empty credentials = Application Default Credentials
  # (`gcloud auth application-default login`), same auth as dbt.
  credentials = var.credentials != "" ? file(var.credentials) : null
  project     = var.project
  region      = var.region
}

resource "google_storage_bucket" "geoops_raw" {
  name          = var.gcs_bucket_name
  location      = var.location
  force_destroy = true

  # Only the bulky, re-downloadable TLC Parquet expires (D-060). The 90-day rule
  # used to apply bucket-wide and silently deleted the H3 lookup CSV too.
  lifecycle_rule {
    condition {
      age            = 90
      matches_prefix = ["raw/tlc_yellow/"]
    }
    action { type = "Delete" }
  }

  lifecycle_rule {
    condition { age = 1 }
    action { type = "AbortIncompleteMultipartUpload" }
  }
}

resource "google_bigquery_dataset" "geoops_raw" {
  dataset_id = var.bq_dataset_raw
  location   = var.location
}

resource "google_bigquery_dataset" "geoops_dbt_dev" {
  dataset_id = var.bq_dataset_dbt
  location   = var.location
}

# Dataproc is NOT managed here (D-059). The cluster is ephemeral: Kestra
# flow_04 creates it, submits the job, and deletes it in a `finally` block.
# Keeping it in Terraform caused permanent drift — idle_delete_ttl destroyed
# it after 30 min, so every `terraform plan` wanted to recreate it.
