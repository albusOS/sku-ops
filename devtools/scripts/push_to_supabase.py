"""Execute SQL batch files against Supabase production DB.

Usage:
    SUPABASE_DATABASE_URL=postgresql://... PYTHONPATH=backend:. uv run python -m devtools.scripts.push_to_supabase

Reads SUPABASE_DATABASE_URL from environment or backend/.env.
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

SQL_DIR = Path(__file__).resolve().parent.parent / "data" / "real" / "sql_mega"

# Order matters: families before SKUs, SKUs before vendor_items/counters
FILE_ORDER = (
    [f"families_{i}.sql" for i in range(6)]
    + [f"skus_{i}.sql" for i in range(13)]
    + ["counters.sql", "vendor_items.sql", "dept_updates.sql"]
)


def _get_db_url() -> str:
    url = os.environ.get("SUPABASE_DATABASE_URL")
    if url:
        return url
    env_path = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("SUPABASE_DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    print("Error: set SUPABASE_DATABASE_URL in env or backend/.env")
    sys.exit(1)


async def main():
    db_url = _get_db_url()
    print("Connecting to Supabase...")
    conn = await asyncpg.connect(db_url)
    print("Connected.\n")

    for fname in FILE_ORDER:
        path = SQL_DIR / fname
        if not path.exists():
            print(f"  SKIP {fname} (not found)")
            continue
        sql = path.read_text()
        try:
            await conn.execute(sql)
            print(f"  OK   {fname}")
        except Exception as e:
            print(f"  FAIL {fname}: {e}")
            sys.exit(1)

    # Verify counts
    families = await conn.fetchval("SELECT COUNT(*) FROM products")
    skus = await conn.fetchval("SELECT COUNT(*) FROM skus")
    vendors = await conn.fetchval("SELECT COUNT(*) FROM vendor_items")
    print("\nVerification:")
    print(f"  Families:     {families}")
    print(f"  SKUs:         {skus}")
    print(f"  Vendor items: {vendors}")

    await conn.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
