"""Inventory application queries — safe for cross-context import.

Exposes stock transaction analytics without leaking infrastructure details.
"""

from __future__ import annotations

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


async def demand_normalized_velocity(
    sku_ids: list[str],
    days: int = 30,
) -> dict[str, dict]:
    """Per-SKU withdrawal velocity with IQR outlier stripping.

    Returns {sku_id: {raw_total, normalized_total, median_daily, mean_daily,
    outlier_days, total_days}} for each SKU that has any withdrawal activity.
    Days with volume above Q3 + 1.5*IQR are excluded from normalized metrics.
    """
    if not sku_ids:
        return {}
    conn = get_connection()
    org_id = get_org_id()

    ph = ",".join(f"${i}" for i in range(1, len(sku_ids) + 1))
    days_idx = len(sku_ids) + 1
    org_idx = days_idx + 1

    query = f"""
    WITH daily AS (
        SELECT sku_id,
               DATE(created_at) AS day,
               COALESCE(SUM(ABS(quantity_delta)), 0) AS qty
        FROM stock_transactions
        WHERE sku_id IN ({ph})
          AND transaction_type = 'WITHDRAWAL'
          AND created_at >= (NOW() - make_interval(days => ${days_idx}))::text
          AND (organization_id = ${org_idx} OR organization_id IS NULL)
        GROUP BY sku_id, DATE(created_at)
    ),
    iqr AS (
        SELECT sku_id,
               PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY qty) AS q1,
               PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY qty) AS median_daily,
               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY qty) AS q3,
               COUNT(*) AS total_days,
               SUM(qty) AS raw_total,
               AVG(qty) AS mean_daily
        FROM daily
        GROUP BY sku_id
    )
    SELECT i.sku_id,
           i.raw_total,
           i.median_daily,
           i.mean_daily,
           i.total_days,
           i.q1, i.q3,
           COALESCE(SUM(CASE WHEN d.qty <= i.q3 + 1.5 * (i.q3 - i.q1) THEN d.qty END), 0) AS normalized_total,
           COUNT(CASE WHEN d.qty > i.q3 + 1.5 * (i.q3 - i.q1) THEN 1 END) AS outlier_days
    FROM iqr i
    JOIN daily d ON d.sku_id = i.sku_id
    GROUP BY i.sku_id, i.raw_total, i.median_daily, i.mean_daily, i.total_days, i.q1, i.q3
    """
    cur = await conn.execute(query, (*sku_ids, days, org_id))
    result = {}
    for row in await cur.fetchall():
        r = dict(row)
        total_days = r["total_days"] or 1
        clean_days = total_days - (r["outlier_days"] or 0)
        result[r["sku_id"]] = {
            "raw_total": float(r["raw_total"]),
            "normalized_total": float(r["normalized_total"]),
            "median_daily": round(float(r["median_daily"]), 2),
            "mean_daily": round(float(r["mean_daily"]), 2),
            "normalized_daily": round(float(r["normalized_total"]) / max(clean_days, 1), 2),
            "outlier_days": int(r["outlier_days"] or 0),
            "total_days": int(total_days),
        }
    return result


async def seasonal_pattern(
    sku_id: str,
    months: int = 12,
) -> list[dict]:
    """Monthly withdrawal totals for a SKU over the last N months."""
    conn = get_connection()
    org_id = get_org_id()
    cur = await conn.execute(
        """SELECT to_char(DATE(created_at), 'YYYY-MM') AS month,
                  COALESCE(SUM(ABS(quantity_delta)), 0) AS total_qty,
                  COUNT(*) AS transaction_count
           FROM stock_transactions
           WHERE sku_id = $1
             AND transaction_type = 'WITHDRAWAL'
             AND created_at >= (NOW() - make_interval(months => $2))::text
             AND (organization_id = $3 OR organization_id IS NULL)
           GROUP BY month
           ORDER BY month""",
        (sku_id, months, org_id),
    )
    return [dict(r) for r in await cur.fetchall()]


async def sku_demand_profile(
    sku_id: str,
    days: int = 60,
) -> dict:
    """Deep demand profile for a single SKU.

    Returns daily quantities, IQR stats, outlier flags, and job concentration
    (identifies project buys where one job accounts for >40% of volume).
    """
    conn = get_connection()
    org_id = get_org_id()

    daily_cur = await conn.execute(
        """SELECT DATE(st.created_at) AS day,
                  COALESCE(SUM(ABS(st.quantity_delta)), 0) AS qty
           FROM stock_transactions st
           WHERE st.sku_id = $1
             AND st.transaction_type = 'WITHDRAWAL'
             AND st.created_at >= (NOW() - make_interval(days => $2))::text
             AND (st.organization_id = $3 OR st.organization_id IS NULL)
           GROUP BY DATE(st.created_at)
           ORDER BY day""",
        (sku_id, days, org_id),
    )
    daily_rows = [dict(r) for r in await daily_cur.fetchall()]

    if not daily_rows:
        return {
            "sku_id": sku_id,
            "period_days": days,
            "total_days_active": 0,
            "raw_total": 0,
            "daily": [],
            "stats": None,
            "project_buys": [],
        }

    quantities = [float(r["qty"]) for r in daily_rows]
    quantities.sort()
    n = len(quantities)
    q1 = quantities[n // 4] if n >= 4 else quantities[0]
    q3 = quantities[(3 * n) // 4] if n >= 4 else quantities[-1]
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr

    daily_out = []
    raw_total = 0.0
    baseline_total = 0.0
    for r in daily_rows:
        qty = float(r["qty"])
        raw_total += qty
        is_outlier = qty > upper_fence and iqr > 0
        if not is_outlier:
            baseline_total += qty
        daily_out.append(
            {
                "day": str(r["day"]),
                "qty": qty,
                "outlier": is_outlier,
            }
        )

    baseline_days = sum(1 for d in daily_out if not d["outlier"])
    median_val = quantities[n // 2]

    # Job concentration: find jobs that account for >40% of volume
    job_cur = await conn.execute(
        """SELECT w.job_id, SUM(ABS(st.quantity_delta)) AS job_total
           FROM stock_transactions st
           LEFT JOIN withdrawals w
             ON st.reference_id = w.id AND st.reference_type = 'withdrawal'
           WHERE st.sku_id = $1
             AND st.transaction_type = 'WITHDRAWAL'
             AND st.created_at >= (NOW() - make_interval(days => $2))::text
             AND (st.organization_id = $3 OR st.organization_id IS NULL)
             AND w.job_id IS NOT NULL
           GROUP BY w.job_id
           ORDER BY job_total DESC
           LIMIT 10""",
        (sku_id, days, org_id),
    )
    project_buys = []
    for jr in await job_cur.fetchall():
        jd = dict(jr)
        pct = float(jd["job_total"]) / raw_total * 100 if raw_total > 0 else 0
        if pct >= 40:
            project_buys.append(
                {
                    "job_id": jd["job_id"],
                    "total": round(float(jd["job_total"]), 2),
                    "pct_of_total": round(pct, 1),
                }
            )

    return {
        "sku_id": sku_id,
        "period_days": days,
        "total_days_active": n,
        "raw_total": round(raw_total, 2),
        "baseline_total": round(baseline_total, 2),
        "daily": daily_out,
        "stats": {
            "median_daily": round(median_val, 2),
            "mean_daily": round(raw_total / n, 2),
            "baseline_daily": round(baseline_total / max(baseline_days, 1), 2),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "upper_fence": round(upper_fence, 2),
            "outlier_days": n - baseline_days,
        },
        "project_buys": project_buys,
    }
