import os
import json
import urllib.request
from google.cloud import storage

APP_TOKEN = os.environ["NYC_APP_TOKEN"]
GCS_BUCKET = "hardy-geo-de-267342"
GCS_PATH = "raw/reference/nyc_taxi_zones.geojson"
DATASET_ID = "8meu-9t5y"

url = f"https://data.cityofnewyork.us/api/geospatial/{DATASET_ID}?method=export&type=GeoJSON"
print(f"Fetching: {url}")

req = urllib.request.Request(url, headers={"X-App-Token": APP_TOKEN})
with urllib.request.urlopen(req) as r:
    raw = r.read()

gj = json.loads(raw)
features = gj.get("features", [])
print(f"Features fetched: {len(features)}")

sample = features[0]["properties"] if features else {}
print(f"Sample properties: {list(sample.keys())}")

client = storage.Client()
bucket = client.bucket(GCS_BUCKET)
blob = bucket.blob(GCS_PATH)
blob.upload_from_string(raw, content_type="application/json")
print(f"Uploaded to gs://{GCS_BUCKET}/{GCS_PATH}")
print(f"Size: {len(raw) / 1024:.1f} KB")
