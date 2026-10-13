# The original local state was lost when development moved off Codespaces
# (D-056). These blocks adopt the live resources into the remote state on the
# next `terraform apply` instead of recreating them. Safe to keep: once a
# resource is in state, its import block is a no-op.

import {
  to = google_storage_bucket.geoops_raw
  id = "hardy-geo-de-267342"
}

import {
  to = google_bigquery_dataset.geoops_raw
  id = "projects/hardy-geo-portofolio/datasets/geoops_raw"
}

import {
  to = google_bigquery_dataset.geoops_dbt_dev
  id = "projects/hardy-geo-portofolio/datasets/geoops_dbt_dev"
}
