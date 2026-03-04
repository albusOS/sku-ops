"""Inventory agent tool implementations — DB queries and search helpers."""
import json
import logging
from datetime import datetime, timezone, timedelta

from shared.infrastructure.config import OPENAI_API_KEY
from shared.infrastructure.database import get_connection
from assistant.agents.search import get_index
from catalog.application.queries import (
    list_products as catalog_list_products,
    list_low_stock as catalog_list_low_stock,
    list_departments as catalog_list_departments,
    list_vendors as catalog_list_vendors,
    get_sku_counters,
)

logger = logging.getLogger(__name__)


async def _search_products(args: dict, org_id: str) -> str:
    query = (args.get("query") or "").strip()
    limit = min(int(args.get("limit") or 20), 50)
    items = await catalog_list_products(search=query, limit=limit, organization_id=org_id)
    out = [
        {
            "sku": p.get("sku"),
            "name": p.get("name"),
            "quantity": p.get("quantity"),
            "sell_uom": p.get("sell_uom", "each"),
            "min_stock": p.get("min_stock"),
            "department": p.get("department_name"),
        }
        for p in items
    ]
    return json.dumps({"count": len(out), "products": out})


async def _search_semantic(args: dict, org_id: str) -> str:
    query = (args.get("query") or "").strip()
    limit = min(int(args.get("limit") or 10), 30)
    index = await get_index(org_id)
    if OPENAI_API_KEY and index._embeddings is not None:
        results = await index.search_semantic(query, limit=limit, api_key=OPENAI_API_KEY)
        method = "embedding"
    else:
        results = index.search_bm25(query, limit=limit)
        method = "bm25"
    out = [
        {
            "sku": p.get("sku"),
            "name": p.get("name"),
            "quantity": p.get("quantity"),
            "sell_uom": p.get("sell_uom", "each"),
            "min_stock": p.get("min_stock"),
            "department": p.get("department_name"),
        }
        for p in results
    ]
    return json.dumps({"count": len(out), "products": out, "method": method})


async def _get_product_details(args: dict, org_id: str) -> str:
    sku = (args.get("sku") or "").strip().upper()
    conn = get_connection()
    cur = await conn.execute(
        "SELECT * FROM products WHERE UPPER(sku) = ? AND (organization_id = ? OR organization_id IS NULL)",
        (sku, org_id),
    )
    row = await cur.fetchone()
    if not row:
        return json.dumps({"error": f"Product with SKU '{sku}' not found"})
    p = dict(row)
    return json.dumps({
        "sku": p.get("sku"),
        "name": p.get("name"),
        "description": p.get("description"),
        "price": p.get("price"),
        "cost": p.get("cost"),
        "quantity": p.get("quantity"),
        "min_stock": p.get("min_stock"),
        "department": p.get("department_name"),
        "vendor": p.get("vendor_name"),
        "original_sku": p.get("original_sku"),
        "barcode": p.get("barcode"),
        "base_unit": p.get("base_unit"),
        "sell_uom": p.get("sell_uom"),
        "pack_qty": p.get("pack_qty"),
    })


async def _get_inventory_stats(org_id: str) -> str:
    conn = get_connection()
    cur = await conn.execute(
        "SELECT COUNT(*) FROM products WHERE (organization_id = ? OR organization_id IS NULL)",
        (org_id,),
    )
    total_skus = (await cur.fetchone())[0]
    cur = await conn.execute(
        "SELECT COALESCE(SUM(quantity * cost), 0) FROM products WHERE (organization_id = ? OR organization_id IS NULL)",
        (org_id,),
    )
    total_value = round(float((await cur.fetchone())[0] or 0), 2)
    cur = await conn.execute(
        "SELECT COUNT(*) FROM products WHERE quantity <= min_stock AND (organization_id = ? OR organization_id IS NULL)",
        (org_id,),
    )
    low_count = (await cur.fetchone())[0]
    cur = await conn.execute(
        "SELECT COUNT(*) FROM products WHERE quantity = 0 AND (organization_id = ? OR organization_id IS NULL)",
        (org_id,),
    )
    out_of_stock = (await cur.fetchone())[0]
    return json.dumps({
        "total_skus": total_skus,
        "_note": "total_skus is the count of distinct product lines. No meaningful total unit count exists because products are measured in different units (each, gallon, box, etc.).",
        "total_cost_value": total_value,
        "low_stock_count": low_count,
        "out_of_stock_count": out_of_stock,
    })


async def _list_low_stock(args: dict, org_id: str) -> str:
    limit = min(int(args.get("limit") or 20), 50)
    items = await catalog_list_low_stock(limit=limit, organization_id=org_id)
    out = [
        {
            "sku": p.get("sku"),
            "name": p.get("name"),
            "quantity": p.get("quantity"),
            "sell_uom": p.get("sell_uom", "each"),
            "min_stock": p.get("min_stock"),
            "department": p.get("department_name"),
        }
        for p in items
    ]
    return json.dumps({"count": len(out), "products": out})


async def _list_departments(org_id: str) -> str:
    depts = await catalog_list_departments(organization_id=org_id)
    counters = await get_sku_counters()
    out = []
    for d in depts:
        code = d.get("code", "")
        next_num = counters.get(code, 0) + 1
        next_sku = f"{code}-ITM-{str(next_num).zfill(6)}"
        out.append({
            "name": d.get("name"),
            "code": code,
            "product_count": d.get("product_count", 0),
            "next_sku": next_sku,
        })
    return json.dumps({"departments": out})


async def _list_vendors(org_id: str) -> str:
    vendors = await catalog_list_vendors(organization_id=org_id)
    out = [{"name": v.get("name"), "product_count": v.get("product_count", 0)} for v in vendors]
    return json.dumps({"vendors": out})


async def _get_usage_velocity(args: dict, org_id: str) -> str:
    sku = (args.get("sku") or "").strip().upper()
    days = min(int(args.get("days") or 30), 365)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_connection()
    cur = await conn.execute(
        "SELECT id, name, quantity, sell_uom FROM products WHERE UPPER(sku) = ? AND (organization_id = ? OR organization_id IS NULL)",
        (sku, org_id),
    )
    row = await cur.fetchone()
    if not row:
        return json.dumps({"error": f"Product '{sku}' not found"})
    product_id, product_name, current_qty, sell_uom = row["id"], row["name"], row["quantity"], row["sell_uom"] or "each"
    cur = await conn.execute(
        """SELECT COUNT(*) as txn_count, COALESCE(SUM(ABS(quantity_delta)), 0) as total_used
           FROM stock_transactions
           WHERE product_id = ? AND transaction_type = 'WITHDRAWAL' AND created_at >= ?""",
        (product_id, since),
    )
    row = await cur.fetchone()
    txn_count = row["txn_count"] if row else 0
    total_used = int(row["total_used"]) if row else 0
    avg_daily = round(total_used / days, 2)
    days_until_zero = round(current_qty / avg_daily, 1) if avg_daily > 0 else None
    return json.dumps({
        "sku": sku,
        "name": product_name,
        "sell_uom": sell_uom,
        "current_quantity": current_qty,
        "period_days": days,
        "total_withdrawn": total_used,
        "withdrawal_transactions": txn_count,
        "avg_daily_use": avg_daily,
        "days_until_stockout": days_until_zero,
        "_note": None if days_until_zero is not None else "days_until_stockout is null because avg_daily_use=0 — no withdrawals recorded in this period, not a data error.",
    })


async def _get_reorder_suggestions(args: dict, org_id: str) -> str:
    limit = min(int(args.get("limit") or 20), 50)
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    conn = get_connection()
    low_stock = await catalog_list_low_stock(limit=100, organization_id=org_id)
    if not low_stock:
        return json.dumps({"count": 0, "suggestions": []})
    product_ids = [p["id"] for p in low_stock]
    placeholders = ",".join("?" * len(product_ids))
    cur = await conn.execute(
        f"""SELECT product_id, COALESCE(SUM(ABS(quantity_delta)), 0) as total_used
            FROM stock_transactions
            WHERE product_id IN ({placeholders}) AND transaction_type = 'WITHDRAWAL' AND created_at >= ?
            GROUP BY product_id""",
        (*product_ids, since),
    )
    velocity_map = {row["product_id"]: row["total_used"] for row in await cur.fetchall()}
    suggestions = []
    for p in low_stock:
        total_used = velocity_map.get(p["id"], 0)
        avg_daily = total_used / 30
        qty = p.get("quantity", 0)
        days_until_zero = round(qty / avg_daily, 1) if avg_daily > 0 else None
        urgency = (
            "critical" if days_until_zero is not None and days_until_zero <= 3
            else "high" if days_until_zero is not None and days_until_zero <= 7
            else "medium" if days_until_zero is not None
            else "no_velocity_data"
        )
        suggestions.append({
            "sku": p.get("sku"),
            "name": p.get("name"),
            "quantity": qty,
            "sell_uom": p.get("sell_uom", "each"),
            "min_stock": p.get("min_stock"),
            "avg_daily_use": round(avg_daily, 2),
            "days_until_stockout": days_until_zero,
            "urgency": urgency,
        })
    suggestions.sort(key=lambda x: (
        x["days_until_stockout"] is None,
        x["days_until_stockout"] if x["days_until_stockout"] is not None else 9999,
    ))
    return json.dumps({
        "count": len(suggestions),
        "suggestions": suggestions[:limit],
        "_note": "urgency='no_velocity_data' means the product has no withdrawal history in the last 30 days — it is still below reorder point and may need restocking.",
    })


async def _get_department_health(org_id: str) -> str:
    conn = get_connection()
    cur = await conn.execute(
        """SELECT d.name, d.code,
                  COUNT(p.id) as product_count,
                  SUM(CASE WHEN p.quantity = 0 THEN 1 ELSE 0 END) as out_of_stock,
                  SUM(CASE WHEN p.quantity > 0 AND p.quantity <= p.min_stock THEN 1 ELSE 0 END) as low_stock,
                  SUM(CASE WHEN p.quantity > p.min_stock THEN 1 ELSE 0 END) as healthy
           FROM departments d
           LEFT JOIN products p ON p.department_id = d.id
             AND (p.organization_id = ? OR p.organization_id IS NULL)
           WHERE (d.organization_id = ? OR d.organization_id IS NULL)
           GROUP BY d.id, d.name, d.code
           ORDER BY (out_of_stock + low_stock) DESC""",
        (org_id, org_id),
    )
    rows = [dict(r) for r in await cur.fetchall()]
    return json.dumps({"departments": rows})


async def _get_slow_movers(args: dict, org_id: str) -> str:
    limit = min(int(args.get("limit") or 20), 100)
    days = min(int(args.get("days") or 30), 365)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_connection()
    cur = await conn.execute(
        """SELECT p.id, p.sku, p.name, p.quantity, p.sell_uom, p.min_stock,
                  p.department_name,
                  COALESCE(txn.total_used, 0) as units_withdrawn
           FROM products p
           LEFT JOIN (
               SELECT product_id, SUM(ABS(quantity_delta)) as total_used
               FROM stock_transactions
               WHERE transaction_type = 'WITHDRAWAL' AND created_at >= ?
               GROUP BY product_id
           ) txn ON p.id = txn.product_id
           WHERE (p.organization_id = ? OR p.organization_id IS NULL)
             AND p.quantity > 0
           ORDER BY COALESCE(txn.total_used, 0) ASC, p.quantity DESC
           LIMIT ?""",
        (since, org_id, limit),
    )
    rows = [dict(r) for r in await cur.fetchall()]
    out = [
        {
            "sku": r["sku"],
            "name": r["name"],
            "quantity": r["quantity"],
            "sell_uom": r["sell_uom"] or "each",
            "department": r["department_name"],
            "units_withdrawn_30d": int(r["units_withdrawn"]),
        }
        for r in rows
    ]
    return json.dumps({"period_days": days, "count": len(out), "slow_movers": out})
