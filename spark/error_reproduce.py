"""
Reproduce the D-045 failure: reading TLC 2023 January + February in one
spark.read.parquet() call. January uses the legacy schema (D-045a), so both
naive strategies fail. The fix lives in flow4_h3_enrichment.py
(per-month read + cast + unionByName).

Runs on local Spark — no Dataproc, no GCS auth.
Shares the tlc_schemas/ cache with schema_diff.py (run from spark/).

    pip install pyspark==3.5.*    # needs Java 17
    python error_reproduce.py
"""
import os
import urllib.request

from pyspark.sql import SparkSession

os.makedirs("tlc_schemas", exist_ok=True)
paths = []
for month in (1, 2):  # January = legacy schema, February = new schema
    fname = f"tlc_schemas/2023_{month:02d}.parquet"
    if not os.path.exists(fname):
        url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-{month:02d}.parquet"
        print(f"Downloading month {month:02d}...")
        urllib.request.urlretrieve(url, fname)
    paths.append(fname)

spark = SparkSession.builder.master("local[2]").appName("repro_d045").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

attempts = {
    # Schema inferred from one file, applied to both -> type mismatch at scan time
    "default read": lambda: spark.read.parquet(*paths),
    # Spark refuses to merge e.g. passenger_count DOUBLE (Jan) with BIGINT (Feb)
    "mergeSchema": lambda: spark.read.option("mergeSchema", "true").parquet(*paths),
}

for name, read in attempts.items():
    print(f"\n=== {name} ===")
    try:
        # Aggregate forces a real column scan (count() alone can use footer metadata)
        read().selectExpr("sum(passenger_count)", "sum(RatecodeID)").collect()
        print("no error (unexpected — see D-045a)")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {str(e).splitlines()[0][:300]}")

spark.stop()
