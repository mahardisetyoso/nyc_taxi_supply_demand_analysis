import pyarrow.parquet as pq
import requests

# TLC Yellow Taxi 2023 CloudFront URLs
months = list(range(1, 13))
schemas = {}

for month in months:
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-{month:02d}.parquet"
    # Read just metadata, not full file
    try:
        # Download just first few KB to read schema
        response = requests.get(url, headers={"Range": "bytes=0-100000"}, stream=True)
        # Or use pyarrow directly with URL
        import io
        partial = io.BytesIO(response.content)
        schema = pq.read_schema(partial)
        schemas[month] = schema
        print(f"Month {month:02d}: OK")
    except Exception as e:
        print(f"Month {month:02d}: {e}")

# Compare schemas
reference = schemas[1]
for month, schema in schemas.items():
    if month == 1: continue
    diff = []
    for field_ref, field_cur in zip(reference, schema):
        if field_ref.type != field_cur.type:
            diff.append(f"  {field_ref.name}: {field_ref.type} → {field_cur.type}")
    if diff:
        print(f"Month {month:02d} differs from Month 01:")
        for d in diff:
            print(d)