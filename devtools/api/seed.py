"""Seed API routes — operational endpoints only."""

import logging

from fastapi import APIRouter

from shared.api.deps import AdminDep
from shared.infrastructure.database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/departments")
async def seed_departments(current_user: AdminDep):
    """Create standard departments for the org (idempotent)."""
    from datetime import UTC, datetime

    from catalog.application.queries import insert_department
    from catalog.domain.department import Department
    from devtools.scripts.company import DEPARTMENTS

    org_id = current_user.organization_id
    now = datetime.now(UTC).isoformat()
    created = 0
    for dept in DEPARTMENTS:
        try:
            d = Department(
                name=dept.name,
                code=dept.code,
                description=dept.description,
                organization_id=org_id,
                created_at=now,
            )
            await insert_department(d)
            created += 1
        except Exception as e:
            logger.debug("Department %s already exists: %s", dept.code, e)
    return {
        "message": f"Departments ready ({created} created, {len(DEPARTMENTS) - created} already existed)"
    }


@router.post("/backfill-ledger")
async def backfill_ledger(current_user: AdminDep):
    """Replay all historical events into the financial_ledger for existing data."""
    from catalog.application.queries import list_products
    from finance.application.ledger_service import (
        record_adjustment,
        record_payment,
        record_po_receipt,
        record_return,
        record_withdrawal,
    )
    from operations.application.queries import list_returns, list_withdrawals

    org_id = current_user.organization_id
    conn = get_connection()

    await conn.execute("DELETE FROM financial_ledger WHERE organization_id = $1", (org_id,))

    products = await list_products(organization_id=org_id)
    dept_map = {p["id"]: p.get("department_name") for p in products}
    cost_map = {p["id"]: p.get("cost", 0) for p in products}

    withdrawals = await list_withdrawals(limit=100000, organization_id=org_id)
    for w in withdrawals:
        items = [
            {**i, "department_name": dept_map.get(i.get("sku_id"))} for i in w.get("items", [])
        ]
        await record_withdrawal(
            withdrawal_id=w["id"],
            items=items,
            tax=w.get("tax", 0),
            total=w.get("total", 0),
            job_id=w.get("job_id", ""),
            billing_entity=w.get("billing_entity", ""),
            contractor_id=w.get("contractor_id", ""),
            organization_id=org_id,
            performed_by_user_id=w.get("processed_by_id"),
        )
        if w.get("payment_status") == "paid":
            await record_payment(
                withdrawal_id=w["id"],
                amount=w.get("total", 0),
                billing_entity=w.get("billing_entity", ""),
                contractor_id=w.get("contractor_id", ""),
                organization_id=org_id,
                performed_by_user_id=w.get("processed_by_id"),
            )

    returns = await list_returns(limit=100000, organization_id=org_id)
    for r in returns:
        items = [
            {**i, "department_name": dept_map.get(i.get("sku_id"))} for i in r.get("items", [])
        ]
        await record_return(
            return_id=r["id"],
            items=items,
            tax=r.get("tax", 0),
            total=r.get("total", 0),
            job_id=r.get("job_id", ""),
            billing_entity=r.get("billing_entity", ""),
            contractor_id=r.get("contractor_id", ""),
            organization_id=org_id,
            performed_by_user_id=r.get("processed_by_id"),
        )

    cursor = await conn.execute(
        """SELECT po.id, po.vendor_name, po.received_by_id,
                  poi.cost, poi.delivered_qty, poi.sku_id, poi.suggested_department
           FROM purchase_orders po
           JOIN purchase_order_items poi ON po.id = poi.po_id
           WHERE po.organization_id = $1 AND poi.status = 'arrived'""",
        (org_id,),
    )
    po_rows = await cursor.fetchall()
    po_items: dict[str, list] = {}
    po_vendors: dict[str, str] = {}
    po_receivers: dict[str, str] = {}
    for row in po_rows:
        r = dict(row)
        po_id = r["id"]
        po_vendors[po_id] = r["vendor_name"]
        po_receivers[po_id] = r.get("received_by_id") or ""
        po_items.setdefault(po_id, []).append(r)
    for po_id, items in po_items.items():
        await record_po_receipt(
            po_id=po_id,
            items=items,
            vendor_name=po_vendors.get(po_id, ""),
            organization_id=org_id,
            performed_by_user_id=po_receivers.get(po_id) or None,
        )

    cursor = await conn.execute(
        """SELECT sku_id, quantity_delta, reason, user_id
           FROM stock_transactions
           WHERE (organization_id = $1 OR organization_id IS NULL)
             AND transaction_type = 'adjustment'""",
        (org_id,),
    )
    adj_rows = await cursor.fetchall()
    for row in adj_rows:
        r = dict(row)
        sid = r["sku_id"]
        await record_adjustment(
            adjustment_ref_id=sid,
            sku_id=sid,
            product_cost=cost_map.get(sid, 0),
            quantity_delta=r["quantity_delta"],
            department=dept_map.get(sid),
            performed_by_user_id=r.get("user_id"),
        )

    cursor = await conn.execute(
        "SELECT COUNT(*) FROM financial_ledger WHERE organization_id = $1", (org_id,)
    )
    row = await cursor.fetchone()
    total_entries = row[0] if row else 0

    return {
        "message": "Ledger backfill complete",
        "withdrawals": len(withdrawals),
        "returns": len(returns),
        "po_receipts": len(po_items),
        "adjustments": len(adj_rows),
        "total_ledger_entries": total_entries,
    }
