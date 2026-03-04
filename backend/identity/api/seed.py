"""Seed API routes. Business logic lives in scripts/seed.py to avoid cross-domain imports."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from identity.application.auth_service import require_role
from shared.infrastructure.config import ALLOW_RESET
from shared.infrastructure.database import get_connection
from catalog.application.queries import count_all_products
from identity.infrastructure.org_repo import organization_repo

from scripts.seed import (
    seed_mock_user,
    seed_standard_departments,
    seed_demo_inventory,
    seed_demo_tenants,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/departments")
async def seed_departments(current_user: dict = Depends(require_role("admin"))):
    org_id = current_user.get("organization_id") or "default"
    await seed_standard_departments(org_id)
    return {"message": "Departments ready"}


async def _clear_all_tables(conn) -> None:
    """Delete all data from core tables (FK order)."""
    await conn.execute("DELETE FROM invoice_line_items")
    await conn.execute("DELETE FROM invoice_withdrawals")
    await conn.execute("DELETE FROM invoices")
    await conn.execute("DELETE FROM invoice_counters")
    await conn.execute("DELETE FROM payment_transactions")
    await conn.execute("DELETE FROM material_requests")
    await conn.execute("DELETE FROM withdrawals")
    await conn.execute("DELETE FROM purchase_order_items")
    await conn.execute("DELETE FROM purchase_orders")
    await conn.execute("DELETE FROM stock_transactions")
    await conn.execute("DELETE FROM products")
    await conn.execute("DELETE FROM sku_counters")
    await conn.execute("DELETE FROM vendors")
    await conn.execute("DELETE FROM departments")
    await conn.execute("DELETE FROM users")
    await conn.execute("DELETE FROM organizations")
    await conn.commit()


@router.post("/reset")
async def reset_all():
    """Reset core tables and reseed demo tenants."""
    if not ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Reset not allowed. Set ALLOW_RESET=true or ENV=development.")
    conn = get_connection()
    try:
        await _clear_all_tables(conn)
        logger.info("Full reset complete")
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    await seed_demo_tenants()
    return {"message": "Reset complete. Demo tenants (North, South) seeded with users and inventory."}


@router.post("/reset-empty")
async def reset_empty():
    """Clear all data and reseed minimal (default org, demo user, departments)."""
    if not ALLOW_RESET:
        raise HTTPException(status_code=403, detail="Reset not allowed. Set ALLOW_RESET=true or ENV=development.")
    conn = get_connection()
    try:
        await _clear_all_tables(conn)
        logger.info("Full reset complete (empty)")
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    now = datetime.now(timezone.utc).isoformat()
    await organization_repo.insert({"id": "default", "name": "Default", "slug": "default", "created_at": now})
    await seed_mock_user()
    await seed_standard_departments("default")
    return {"message": "Reset complete. Empty state. Log in with demo credentials (admin@demo.local / demo123)."}


@router.post("/reset-inventory")
async def reset_and_reseed_inventory(current_user: dict = Depends(require_role("admin"))):
    """Reset products and stock, then re-run demo seed."""
    org_id = current_user.get("organization_id") or "default"
    conn = get_connection()
    try:
        await conn.execute("DELETE FROM stock_transactions")
        await conn.execute("DELETE FROM products")
        await conn.execute("DELETE FROM sku_counters")
        await conn.execute("UPDATE departments SET product_count = 0")
        await conn.execute("UPDATE vendors SET product_count = 0")
        await conn.commit()
        logger.info("Inventory reset complete")
        await seed_demo_inventory(org_id)
        count = await count_all_products(org_id)
        return {"message": f"Inventory reset and reseeded with {count} products"}
    except Exception as e:
        logger.error(f"Reset inventory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
