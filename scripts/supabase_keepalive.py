"""Keep the Supabase free-tier project from auto-pausing.

Supabase pauses free projects after ~7 days without activity. This script runs
a tiny real query against the dashboard tables so the project registers as
active, and fails loudly if the DB is unreachable (e.g. already paused).

Usage:
    python scripts/supabase_keepalive.py

Reads SUPABASE_DB_URL from the environment (or .env at repo root).
Never prints the connection string.
"""
import os
import sys
from datetime import datetime, timezone

import psycopg2

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

EXPECTED = {"revenue_loss_by_zone": 185, "osm_streets": 72005}


def main() -> int:
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("SUPABASE_DB_URL is not set", file=sys.stderr)
        return 1

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        conn = psycopg2.connect(db_url, connect_timeout=20)
    except psycopg2.OperationalError as e:
        # Strip anything that might echo credentials back
        print(f"[{ts}] connect FAILED ({type(e).__name__}) - project may be paused", file=sys.stderr)
        return 2

    ok = True
    with conn, conn.cursor() as cur:
        for table, expected in EXPECTED.items():
            cur.execute(f"SELECT count(*) FROM {table}")
            n = cur.fetchone()[0]
            flag = "OK" if n == expected else f"MISMATCH (expected {expected})"
            ok &= n == expected
            print(f"[{ts}] {table}: {n} rows {flag}")
    conn.close()

    # Row-count drift is a warning, not a failure: the ping itself succeeded.
    if not ok:
        print("WARNING: row counts differ from REACTIVATE.md baseline", file=sys.stderr)
    print(f"[{ts}] keepalive OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
