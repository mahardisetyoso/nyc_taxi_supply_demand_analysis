"""
Quick TLC 2023 schema diff — finds transition month.
Uses pyarrow only. No Spark, no GCS auth.
"""
import pyarrow.parquet as pq
import urllib.request
import os

os.makedirs("tlc_schemas", exist_ok=True)
schemas = {}

for month in range(1, 13):
    fname = f"tlc_schemas/2023_{month:02d}.parquet"
    if not os.path.exists(fname):
        url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-{month:02d}.parquet"
        print(f"Downloading month {month:02d}...")
        urllib.request.urlretrieve(url, fname)
    schemas[month] = pq.read_schema(fname)
    print(f"Month {month:02d}: {len(schemas[month])} columns")

# Compare to month 01
ref = {f.name: str(f.type) for f in schemas[1]}

print("\n" + "=" * 60)
print("SCHEMA DIFFERENCES FROM MONTH 01")
print("=" * 60)

for month in range(2, 13):
    cur = {f.name: str(f.type) for f in schemas[month]}
    type_changes = []
    missing = []
    added = []
    for name, ref_type in ref.items():
        if name not in cur:
            missing.append(name)
        elif cur[name] != ref_type:
            type_changes.append(f"  {name}: {ref_type} → {cur[name]}")
    for name in cur:
        if name not in ref:
            added.append(f"  + {name}: {cur[name]}")
    if type_changes or missing or added:
        print(f"\nMonth {month:02d}:")
        for t in type_changes: print(t)
        for m in missing: print(f"  - MISSING: {m}")
        for n in added: print(n)