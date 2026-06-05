terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.6.0"
    }
  }
}

provider "google" {
  credentials = file(var.credentials)
  project     = var.project
  region      = var.region
}

resource "google_storage_bucket" "geoops_raw" {
  name          = var.gcs_bucket_name
  location      = var.location
  force_destroy = true

  lifecycle_rule {
    condition { age = 90 }
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

# ──────────────────────────────────────────────────────────
# Dataproc cluster untuk PySpark H3 enrichment (Week 3)
# ──────────────────────────────────────────────────────────
resource "google_dataproc_cluster" "geoops_spark" {
  name   = var.dataproc_cluster_name
  region = var.region

  cluster_config {
    # Master node — 1 instance untuk koordinasi (non-HA, portfolio scale)
    master_config {
      num_instances = 1
      machine_type  = "n2-standard-2" # 2 vCPU, 8 GB RAM
      disk_config {
        boot_disk_size_gb = 100
        boot_disk_type    = "pd-standard"
      }
    }

    # Worker nodes — 2 instance minimum (Dataproc requirement)
    worker_config {
      num_instances = var.dataproc_worker_count
      machine_type  = "n2-standard-2"
      disk_config {
        boot_disk_size_gb = 100
        boot_disk_type    = "pd-standard"
      }
    }

    # Software: Spark 3.5 + Jupyter optional component
    software_config {
      image_version       = "2.2-debian12"
      optional_components = ["JUPYTER"]
      override_properties = {
        "spark:spark.sql.adaptive.enabled"                    = "true"
        "spark:spark.sql.adaptive.coalescePartitions.enabled" = "true"
      }
    }

    # Service account + scope untuk akses GCS dan BigQuery
    gce_cluster_config {
      service_account        = "terraform-runner@${var.project}.iam.gserviceaccount.com"
      service_account_scopes = ["cloud-platform"]
    }

    # AUTO-DELETE setelah 30 menit idle — proteksi cost utama
    lifecycle_config {
      idle_delete_ttl = "1800s"
    }

    # Component Gateway: akses Spark UI, Jupyter, YARN UI via HTTPS
    endpoint_config {
      enable_http_port_access = true
    }
  }

  labels = {
    environment = "dev"
    project     = "nyc-taxi-supply-demand"
    component   = "spark"
  }
}