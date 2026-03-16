"""
One-time fix: update purchase_order_items with status='received' to status='arrived'.

POItemStatus allows: ordered, pending, arrived. 'received' is invalid for items
(PO-level status only). Old or bad data causes Pydantic validation errors.

Run against demo DB (DATABASE_URL in backend/.env or env):
    uv run python -m devtools.scripts.fix_po_item_status_received
"""

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_root))

# Load .env from backend/ so DATABASE_URL is available when run against demo
for env_path in (_root / "backend" / ".env", _root / ".env"):
    if env_path.exists():
        from dotenv import load_dotenv

        load_dotenv(env_path)
        break


async def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set")
    conn = await asyncpg.connect(url)
    result = await conn.execute(
        """UPDATE purchase_order_items SET status = 'arrived' WHERE status = 'received'"""
    )
    # Result format: "UPDATE N"
    print(result)
    await conn.close()
    print("Done. purchase_order_items with status='received' now have status='arrived'.")


if __name__ == "__main__":
    asyncio.run(main())
