"""
Flow 4: TLC Yellow Taxi H3 Enrichment — Full 12-Month 2023
=========================================================
Decisions: D-040 (filtering), D-041 (broadcast join H3), D-042 (hour×dow), D-043 (BQ output)
D-044: Pre-computed lookup CSV (no external pip deps needed on cluster)

Prototype validated: notebooks/prototype_flow4_h3_enrichment.ipynb
  - Jan 2023: 3,066,766 raw -> 2,823,775 (filter) -> 2,823,739 (join, drop null H3)

day_of_week convention:
  pandas dt.dayofweek: 0=Monday, 6=Sunday
  Spark F.dayofweek:   1=Sunday, 7=Saturday
  Normalized: (F.dayofweek + 5) % 7 -> 0=Monday, 6=Sunday (matches prototype)

Schema evolution handling:
  TLC changed Parquet schema mid-2023. Per-month read + cast to common types + union.
  passenger_count: DOUBLE (early months) vs INT64 (later months)
  VendorID/PULocationID/DOLocationID: BIGINT vs INT
  Airport_fee vs airport_fee (case mismatch)

Run:
  gcloud dataproc jobs submit pyspark \
    gs://hardy-geo-de-267342/spark_jobs/flow4_h3_enrichment.py \
    --cluster=geoops-spark \
    --region=asia-southeast1 \
    --project=hardy-geo-portofolio
"""

from functools import reduce
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

# ── Constants ─────────────────────────────────────────────────────────────────
GCS_BUCKET       = "hardy-geo-de-267342"
GCS_LOOKUP_PATH  = f"gs://{GCS_BUCKET}/raw/reference/location_h3_lookup.csv"
BQ_TABLE         = "hardy-geo-portofolio.geoops_raw.yellow_trips_h3_enriched"
BQ_TEMP_BUCKET   = GCS_BUCKET

# ── Spark Session ──────────────────────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("Flow4_H3_Enrichment_2023") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("temporaryGcsBucket", BQ_TEMP_BUCKET) \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("=" * 60)
print("Flow 4: H3 Enrichment — Full 2023")
print("=" * 60)


# ── Step 1: Read Pre-computed H3 Lookup (D-044) ──────────────────────────────
print("\n[Step 1] Reading H3 lookup CSV...")

df_lookup = spark.read.csv(GCS_LOOKUP_PATH, header=True, inferSchema=True)
lookup_count = df_lookup.count()
print(f"  Lookup rows: {lookup_count}")
df_lookup.show(5, truncate=False)


# ── Step 2: Read TLC Parquet — per-month with schema normalization ────────────
# TLC changed schema mid-2023. Read each month separately, cast all columns
# to common types, then union. This is the production pattern for schema evolution.
print("\n[Step 2] Reading TLC Yellow 2023 (per-month schema normalization)...")

COMMON_COLS = [
    F.col("VendorID").cast("long"),
    F.col("tpep_pickup_datetime"),
    F.col("tpep_dropoff_datetime"),
    F.col("passenger_count").cast("double"),
    F.col("trip_distance").cast("double"),
    F.col("RatecodeID").cast("double"),
    F.col("store_and_fwd_flag").cast("string"),
    F.col("PULocationID").cast("long"),
    F.col("DOLocationID").cast("long"),
    F.col("payment_type").cast("long"),
    F.col("fare_amount").cast("double"),
    F.col("extra").cast("double"),
    F.col("mta_tax").cast("double"),
    F.col("tip_amount").cast("double"),
    F.col("tolls_amount").cast("double"),
    F.col("improvement_surcharge").cast("double"),
    F.col("total_amount").cast("double"),
    F.col("congestion_surcharge").cast("double"),
    F.col("airport_fee").cast("double"),
]

dfs = []
for month in range(1, 13):
    path = f"gs://{GCS_BUCKET}/raw/tlc_yellow/year=2023/month={month:02d}/*.parquet"
    df_month = spark.read.parquet(path).select(COMMON_COLS)
    dfs.append(df_month)
    print(f"  Month {month:02d} loaded")

df_raw = reduce(lambda a, b: a.unionByName(b), dfs)

raw_count = df_raw.count()
print(f"  Raw rows: {raw_count:,}")


# ── Step 3: D-040 Filters ─────────────────────────────────────────────────────
print("\n[Step 3] Applying D-040 filters...")

df_filtered = df_raw.filter(
    F.col("tpep_pickup_datetime").isNotNull() &
    F.col("tpep_dropoff_datetime").isNotNull() &
    (F.col("tpep_dropoff_datetime") > F.col("tpep_pickup_datetime")) &
    ((F.unix_timestamp("tpep_dropoff_datetime") -
      F.unix_timestamp("tpep_pickup_datetime")) <= 10800) &
    F.col("PULocationID").isNotNull() &
    F.col("DOLocationID").isNotNull() &
    (~F.col("PULocationID").isin(264, 265)) &
    (~F.col("DOLocationID").isin(264, 265)) &
    F.col("passenger_count").isNotNull() &
    (F.col("passenger_count").cast(IntegerType()) >= 1) &
    (F.col("passenger_count").cast(IntegerType()) <= 8) &
    F.col("trip_distance").isNotNull() &
    (F.col("trip_distance") >= 0.1) &
    (F.col("trip_distance") <= 100.0) &
    F.col("fare_amount").isNotNull() &
    (F.col("fare_amount") >= 2.50) &
    (F.col("fare_amount") <= 500.0) &
    F.col("total_amount").isNotNull() &
    (F.col("total_amount") >= 2.50) &
    (F.col("total_amount") <= 500.0)
)

filtered_count = df_filtered.count()
drop_pct = (raw_count - filtered_count) / raw_count * 100
print(f"  After filter: {filtered_count:,}")
print(f"  Dropped: {raw_count - filtered_count:,} ({drop_pct:.1f}%)")


# ── Step 4: H3 Broadcast Join (D-041) ────────────────────────────────────────
print("\n[Step 4] H3 broadcast join...")

df_pu = df_filtered.join(
    F.broadcast(
        df_lookup
        .withColumnRenamed("LocationID", "_pu_id")
        .withColumnRenamed("h3_res8", "h3_pickup_res8")
    ),
    df_filtered["PULocationID"] == F.col("_pu_id"),
    how="left"
).drop("_pu_id")

df_h3 = df_pu.join(
    F.broadcast(
        df_lookup
        .withColumnRenamed("LocationID", "_do_id")
        .withColumnRenamed("h3_res8", "h3_dropoff_res8")
    ),
    df_pu["DOLocationID"] == F.col("_do_id"),
    how="left"
).drop("_do_id")

df_enriched = df_h3.filter(
    F.col("h3_pickup_res8").isNotNull() &
    F.col("h3_dropoff_res8").isNotNull()
)


# ── Step 5: Temporal Features (D-042) ────────────────────────────────────────
df_final = df_enriched \
    .withColumn(
        "day_of_week",
        ((F.dayofweek("tpep_pickup_datetime") + 5) % 7).cast(IntegerType())
    ) \
    .withColumn(
        "hour_of_day",
        F.hour("tpep_pickup_datetime").cast(IntegerType())
    )

final_count = df_final.count()
null_dropped = filtered_count - final_count
print(f"\n[Step 5] Final enriched rows: {final_count:,}")
print(f"  Null H3 dropped: {null_dropped:,}")


# ── Step 6: Write to BigQuery (D-043) ─────────────────────────────────────────
print(f"\n[Step 6] Writing to BigQuery: {BQ_TABLE}")

df_final \
    .write \
    .format("bigquery") \
    .option("table", BQ_TABLE) \
    .option("partitionField", "tpep_pickup_datetime") \
    .option("partitionType", "DAY") \
    .option("clusteredFields", "h3_pickup_res8,h3_dropoff_res8") \
    .option("createDisposition", "CREATE_IF_NEEDED") \
    .option("writeDisposition", "WRITE_TRUNCATE") \
    .mode("overwrite") \
    .save()

print(f"  Written: {final_count:,} rows")


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print(f"  Raw:      {raw_count:,}")
print(f"  Filtered: {filtered_count:,} ({drop_pct:.1f}% dropped)")
print(f"  Final:    {final_count:,} ({null_dropped:,} null H3 dropped)")
print(f"  Output:   {BQ_TABLE}")
print("=" * 60)

spark.stop()
print("Done.")