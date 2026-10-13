# One-time: create the remote state bucket (D-060). Idempotent — re-running is safe.
# Run from infrastructure/terraform with an authenticated gcloud.
$Project = "hardy-geo-portofolio"
$Bucket  = "hardy-geo-portofolio-tfstate"

gcloud storage buckets describe "gs://$Bucket" --project=$Project *> $null
if ($LASTEXITCODE -ne 0) {
    gcloud storage buckets create "gs://$Bucket" --project=$Project `
        --location=asia-southeast1 --uniform-bucket-level-access --public-access-prevention
}
# Versioning = every state write is recoverable
gcloud storage buckets update "gs://$Bucket" --versioning
Write-Host "State bucket ready: gs://$Bucket"
