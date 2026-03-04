"""InsightsAgent tool implementations — DB query helpers."""
import json
import logging
from datetime import datetime, timezone, timedelta

from shared.infrastructure.database import get_connection
from operations.application.queries import list_withdrawals

logger = logging.getLogger(__name__)


async def _get_top_products(args: dict, org_id: str) -> str:
    days = min(int(args.get("days") or 30), 365)
    by = args.get("by", "revenue").lower()
    if by not in ("volume", "revenue"):
        by = "revenue"
    limit = min(int(args.get("limit") or 10), 50)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    withdrawals = await list_withdrawals(start_date=since, limit=10000, organization_id=org_id)
    product_map: dict[str, dict] = {}
    for w in withdrawals:
        for item in (w.get("items") or []):
            sku = item.get("sku") or item.get("name", "unknown")
            name = item.get("name", sku)
            qty = item.get("quantity", 0)
            revenue = item.get("subtotal", 0)
            if sku not in product_map:
                product_map[sku] = {"sku": sku, "name": name, "total_units": 0, "total_revenue": 0.0}
            product_map[sku]["total_units"] += qty
            product_map[sku]["total_revenue"] += revenue
    sort_key = "total_revenue" if by == "revenue" else "total_units"
    ranked = sorted(product_map.values(), key=lambda x: x[sort_key], reverse=True)[:limit]
    for r in ranked:
        r["total_revenue"] = round(r["total_revenue"], 2)
    return json.dumps({"period_days": days, "ranked_by": by, "count": len(ranked), "products": ranked})


async def _get_department_activity(args: dict, org_id: str) -> str:
    dept_code = (args.get("dept_code") or "").strip().upper()
    days = min(int(args.get("days") or 30), 365)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_connection()
    cur = await conn.execute(
        """SELECT p.id, p.sku, p.name, p.quantity, p.min_stock
           FROM products p
           JOIN departments d ON p.department_id = d.id
           WHERE UPPER(d.code) = ?
             AND (p.organization_id = ? OR p.organization_id IS NULL)""",
        (dept_code, org_id),
    )
    products = [dict(r) for r in await cur.fetchall()]
    if not products:
        return json.dumps({"error": f"Department '{dept_code}' not found or has no products"})
    product_ids = [p["id"] for p in products]
    placeholders = ",".join("?" * len(product_ids))
    cur = await conn.execute(
        f"""SELECT
              transaction_type,
              COUNT(*) as txn_count,
              COALESCE(SUM(ABS(quantity_delta)), 0) as total_units
            FROM stock_transactions
            WHERE product_id IN ({placeholders}) AND created_at >= ?
            GROUP BY transaction_type""",
        (*product_ids, since),
    )
    type_summary: dict[str, dict] = {}
    for row in await cur.fetchall():
        type_summary[row["transaction_type"]] = {"transactions": row["txn_count"], "units": int(row["total_units"])}
    withdrawals = type_summary.get("WITHDRAWAL", {"transactions": 0, "units": 0})
    receiving = type_summary.get("RECEIVING", {"transactions": 0, "units": 0})
    imports = type_summary.get("IMPORT", {"transactions": 0, "units": 0})
    low_stock_count = sum(1 for p in products if p["quantity"] <= p["min_stock"])
    return json.dumps({
        "dept_code": dept_code,
        "period_days": days,
        "product_count": len(products),
        "low_stock_count": low_stock_count,
        "withdrawals": withdrawals,
        "receiving": receiving,
        "imports": imports,
        "net_units": (receiving["units"] + imports["units"]) - withdrawals["units"],
    })


async def _forecast_stockout(args: dict, org_id: str) -> str:
    limit = min(int(args.get("limit") or 15), 50)
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    conn = get_connection()
    cur = await conn.execute(
        """SELECT id, sku, name, quantity, min_stock, department_name
           FROM products
           WHERE quantity > 0
             AND (organization_id = ? OR organization_id IS NULL)
           ORDER BY quantity ASC
           LIMIT 200""",
        (org_id,),
    )
    products = [dict(r) for r in await cur.fetchall()]
    if not products:
        return json.dumps({"count": 0, "forecast": []})
    product_ids = [p["id"] for p in products]
    placeholders = ",".join("?" * len(product_ids))
    cur = await conn.execute(
        f"""SELECT product_id, COALESCE(SUM(ABS(quantity_delta)), 0) as total_used
            FROM stock_transactions
            WHERE product_id IN ({placeholders}) AND transaction_type = 'WITHDRAWAL' AND created_at >= ?
            GROUP BY product_id""",
        (*product_ids, since),
    )
    velocity_map = {row["product_id"]: row["total_used"] for row in await cur.fetchall()}
    forecast = []
    for p in products:
        total_used = velocity_map.get(p["id"], 0)
        avg_daily = total_used / 30
        if avg_daily <= 0:
            continue
        days_until_zero = round(p["quantity"] / avg_daily, 1)
        forecast.append({
            "sku": p["sku"],
            "name": p["name"],
            "department": p["department_name"],
            "quantity": p["quantity"],
            "min_stock": p["min_stock"],
            "avg_daily_use": round(avg_daily, 2),
            "days_until_stockout": days_until_zero,
            "risk": "critical" if days_until_zero <= 3 else "high" if days_until_zero <= 7 else "medium",
        })
    forecast.sort(key=lambda x: x["days_until_stockout"])
    return json.dumps({"count": len(forecast), "forecast": forecast[:limit]})
