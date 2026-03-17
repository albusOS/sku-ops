"""Inventory application queries — safe for cross-context import.

Exposes stock transaction analytics without leaking infrastructure details.
"""

from shared.infrastructure.database import get_connection, get_org_id


async def withdrawal_velocity(
    sku_ids: list[str],
    since: str,
) -> dict[str, float]:
    """Total units withdrawn per SKU since a date. Keyed by sku_id."""
    if not sku_ids:
        return {}
    conn = get_connection()
    org_id = get_org_id()
    placeholders = ",".join(f"${i}" for i in range(1, len(sku_ids) + 1))
    since_idx = len(sku_ids) + 1
    org_idx = since_idx + 1
    cur = await conn.execute(
        "SELECT sku_id, COALESCE(SUM(ABS(quantity_delta)), 0) as total_used"
        " FROM stock_transactions"
        " WHERE sku_id IN ("
        + placeholders
        + f") AND transaction_type = 'WITHDRAWAL' AND created_at >= ${since_idx}"
        f" AND (organization_id = ${org_idx} OR organization_id IS NULL)"
        " GROUP BY sku_id",
        (*sku_ids, since, org_id),
    )
    return {row["sku_id"]: row["total_used"] for row in await cur.fetchall()}


async def daily_withdrawal_activity(
    since: str,
    sku_id: str | None = None,
) -> list[dict]:
    """Daily withdrawal activity: transaction_count + units_moved per day."""
    conn = get_connection()
    org_id = get_org_id()
    params: list = [org_id, since]
    sku_filter = ""
    if sku_id:
        sku_filter = " AND sku_id = $3"
        params.append(sku_id)

    cur = await conn.execute(
        "SELECT DATE(created_at) AS day,"
        " COUNT(*) AS transaction_count,"
        " COALESCE(SUM(ABS(quantity_delta)), 0) AS units_moved"
        " FROM stock_transactions"
        " WHERE (organization_id = $1 OR organization_id IS NULL)"
        " AND transaction_type = 'WITHDRAWAL'"
        " AND created_at >= $2" + sku_filter + " GROUP BY day"
        " ORDER BY day",
        params,
    )
    return [dict(r) for r in await cur.fetchall()]
