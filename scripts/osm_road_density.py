"""
OSM Road Density Analysis — D-057
Computes road_segment_count per H3 cell via PostGIS ST_Intersects.

Pipeline:
  GCS OSM parquet → Supabase (osm_streets table) → ST_Intersects with H3 zones
  → ADD COLUMN road_segment_count to revenue_loss_by_zone
  → correlation analysis: undersupplied vs oversupplied road density

Run from repo root with venv active:
  python scripts/osm_road_density.py
"""

import os
import geopandas as gpd
import psycopg2
import psycopg2.extras
from shapely import wkb
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

GCS_PATH   = "gs://hardy-geo-de-267342/raw/osm_nyc/streets/nyc_streets_drivable.parquet"
DB_URL     = os.environ["SUPABASE_DB_URL"]

# ── STEP 1: Load OSM from GCS ─────────────────────────────────────────────────
print("Step 1: Loading OSM streets from GCS...")
gdf = gpd.read_parquet(GCS_PATH)
print(f"  Loaded {len(gdf):,} segments, CRS={gdf.crs.to_epsg()}")

# ── STEP 2: Load into Supabase as osm_streets table ──────────────────────────
print("\nStep 2: Loading OSM streets into Supabase...")
conn = psycopg2.connect(DB_URL)
cur  = conn.cursor()

cur.execute("DROP TABLE IF EXISTS osm_streets;")
cur.execute("""
    CREATE TABLE osm_streets (
        osm_id   BIGINT PRIMARY KEY,
        highway  TEXT,
        name     TEXT,
        geom     GEOMETRY(LineString, 4326)
    );
""")
cur.execute("CREATE INDEX idx_osm_streets_geom ON osm_streets USING GIST(geom);")
conn.commit()
print("  Table + GIST index created.")

# Batch insert — 1000 rows per batch
batch, batch_size = [], 1000
for i, row in gdf.iterrows():
    wkb_hex = row.geometry.wkb_hex
    batch.append((int(row.osm_id), row.highway, row.name, wkb_hex))
    if len(batch) >= batch_size:
        psycopg2.extras.execute_batch(cur, """
            INSERT INTO osm_streets (osm_id, highway, name, geom)
            VALUES (%s, %s, %s, ST_GeomFromWKB(decode(%s, 'hex'), 4326))
            ON CONFLICT (osm_id) DO NOTHING
        """, batch)
        conn.commit()
        batch = []
        print(f"  Inserted {i+1:,} rows...", end="\r")

# Flush remainder
if batch:
    psycopg2.extras.execute_batch(cur, """
        INSERT INTO osm_streets (osm_id, highway, name, geom)
        VALUES (%s, %s, %s, ST_GeomFromWKB(decode(%s, 'hex'), 4326))
        ON CONFLICT (osm_id) DO NOTHING
    """, batch)
    conn.commit()

cur.execute("SELECT COUNT(*) FROM osm_streets;")
count = cur.fetchone()[0]
print(f"\n  osm_streets loaded: {count:,} rows")

# ── STEP 3: Add road_segment_count column to revenue_loss_by_zone ─────────────
print("\nStep 3: Adding road_segment_count column...")
cur.execute("""
    ALTER TABLE revenue_loss_by_zone
    ADD COLUMN IF NOT EXISTS road_segment_count INTEGER DEFAULT 0;
""")
conn.commit()
print("  Column added.")

# ── STEP 4: ST_Intersects — count segments per H3 zone ───────────────────────
print("\nStep 4: Computing ST_Intersects road density per zone...")
print("  (This may take 30-90 seconds — PostGIS GIST index doing the work)")

cur.execute("""
    UPDATE revenue_loss_by_zone z
    SET road_segment_count = sub.seg_count
    FROM (
        SELECT z.h3_cell,
               COUNT(s.osm_id) AS seg_count
        FROM   revenue_loss_by_zone z
        JOIN   osm_streets s
               ON ST_Intersects(z.geom, s.geom)
        GROUP  BY z.h3_cell
    ) sub
    WHERE z.h3_cell = sub.h3_cell;
""")
conn.commit()

cur.execute("""
    SELECT COUNT(*) FROM revenue_loss_by_zone
    WHERE road_segment_count > 0;
""")
updated = cur.fetchone()[0]
print(f"  Updated {updated} zones with road_segment_count > 0")

# ── STEP 5: Correlation analysis ─────────────────────────────────────────────
print("\nStep 5: Road density analysis by zone_status")
print("-" * 55)

cur.execute("""
    SELECT
        zone_status,
        COUNT(*)                              AS zone_count,
        ROUND(AVG(road_segment_count), 1)     AS avg_road_segments,
        MIN(road_segment_count)               AS min_segments,
        MAX(road_segment_count)               AS max_segments
    FROM revenue_loss_by_zone
    GROUP BY zone_status
    ORDER BY avg_road_segments DESC;
""")
rows = cur.fetchall()
print(f"  {'Status':<15} {'Zones':>6} {'Avg Segs':>10} {'Min':>6} {'Max':>6}")
print("  " + "-" * 47)
for r in rows:
    print(f"  {r[0]:<15} {r[1]:>6} {r[2]:>10} {r[3]:>6} {r[4]:>6}")

# ── STEP 6: Top undersupplied zones by road density ──────────────────────────
print("\nStep 6: Undersupplied zones — road density vs revenue loss")
print("-" * 65)

cur.execute("""
    SELECT
        zone_name,
        road_segment_count,
        ROUND(unmet_demand_rate::numeric * 100, 1)       AS unmet_pct,
        ROUND(estimated_revenue_loss_usd::numeric / 1e6, 2) AS loss_m
    FROM revenue_loss_by_zone
    WHERE zone_status = 'UNDERSUPPLIED'
    ORDER BY estimated_revenue_loss_usd DESC;
""")
rows = cur.fetchall()
print(f"  {'Zone':<30} {'Road Segs':>10} {'Unmet%':>8} {'Loss($M)':>10}")
print("  " + "-" * 62)
for r in rows:
    print(f"  {r[0]:<30} {r[1]:>10} {r[2]:>7}% {r[3]:>9}M")

# ── STEP 7: Key insight ───────────────────────────────────────────────────────
print("\nStep 7: Insight check")
cur.execute("""
    SELECT
        AVG(CASE WHEN zone_status = 'UNDERSUPPLIED' THEN road_segment_count END) AS avg_under,
        AVG(CASE WHEN zone_status = 'OVERSUPPLIED'  THEN road_segment_count END) AS avg_over
    FROM revenue_loss_by_zone;
""")
r = cur.fetchone()
avg_under, avg_over = float(r[0] or 0), float(r[1] or 0)
print(f"  Avg road segments — UNDERSUPPLIED: {avg_under:.1f} | OVERSUPPLIED: {avg_over:.1f}")

if avg_under >= avg_over * 0.8:
    print("\n  ✅ FINDING: Undersupplied zones have comparable road density to oversupplied.")
    print("     Road access is NOT the bottleneck — this is pure fleet misallocation.")
    print("     This STRENGTHENS the misallocation argument.")
else:
    print("\n  ⚠️  FINDING: Undersupplied zones have lower road density.")
    print("     Physical access may be a contributing factor (mitigating argument).")
    print("     JFK/airport zones likely driving this — check separately.")

cur.close()
conn.close()
print("\nDone. road_segment_count column live in Supabase.")
print("Next: update app.py to show road_segment_count in tooltip + zone table.")