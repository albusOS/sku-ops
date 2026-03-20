"""Ledger analytics — time series, AR aging, product margins, purchase analytics.

Split from ledger_queries.py for file-size discipline. All functions are
re-exported from ledger_queries so existing callers are unaffected.
"""

from typing import TypedDict

from shared.infrastructure.database import get_connection, get_org_id
from shared.kernel.types import round_money


class TrendPoint(TypedDict):
    date: str
    revenue: float
    cost: float
    shrinkage: float
    profit: float
    transaction_count: int


class ArAgingRow(TypedDict):
    billing_entity: str
    total_ar: float
    current_not_due: float
    overdue_1_30: float
    overdue_31_60: float
    overdue_61_90: float
    overdue_90_plus: float


class ProductMarginRow(TypedDict):
    sku_id: str
    revenue: float
    cost: float
    profit: float
    margin_pct: float


def _date_group_expr(column: str, grain: str) -> str:
    if grain == "week":
        return f"to_char({column}::date, 'IYYY-\"W\"IW')"
    if grain == "month":
        return f"to_char({column}::date, 'YYYY-MM')"
    return f"to_char({column}::date, 'YYYY-MM-DD')"


def _build_dimension_filter(
    params: list,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
    col_prefix: str = "",
) -> str:
    """Append optional WHERE clauses for dimension drill-down filtering.

    Uses len(params)+1 to determine the next $N placeholder index, so callers
    must pass the same params list they are building for the overall query.
    """
    sql = ""
    p = col_prefix + "." if col_prefix else ""
    if job_id:
        n = len(params) + 1
        sql += f" AND {p}job_id = ${n}"
        params.append(job_id)
    if department:
        n = len(params) + 1
        sql += f" AND {p}department = ${n}"
        params.append(department)
    if billing_entity:
        n = len(params) + 1
        sql += f" AND {p}billing_entity = ${n}"
        params.append(billing_entity)
    return sql


async def trend_series(
    start_date: str | None = None,
    end_date: str | None = None,
    group_by: str = "day",
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[TrendPoint]:
    """Time-series of revenue, cost, profit."""
    conn = get_connection()
    period_expr = _date_group_expr("created_at", group_by)
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND created_at <= ${n}"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    query = "SELECT "
    query += period_expr
    query += (
        " AS period,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost,"
        " ROUND(CAST(SUM(CASE WHEN account = 'shrinkage' THEN amount ELSE 0 END) AS NUMERIC), 2) AS shrinkage,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = $1"
        " AND account IN ('revenue', 'cogs', 'shrinkage')"
    )
    query += date_filter + dim_filter
    query += " GROUP BY period ORDER BY period"
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    series = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round_money(revenue - cost - row["shrinkage"])
        series.append(
            TrendPoint(
                date=row["period"],
                revenue=revenue,
                cost=cost,
                shrinkage=row["shrinkage"],
                profit=profit,
                transaction_count=row["transaction_count"],
            )
        )
    return series


async def ar_aging(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ArAgingRow]:
    """AR aging buckets by billing entity based on invoice due_date."""
    conn = get_connection()
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND fl.created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND fl.created_at <= ${n}"
        params.append(end_date)

    fallback = "fl.created_at::timestamp + INTERVAL '30 days'"
    due = f"COALESCE(inv.due_date::timestamp, {fallback})"
    age = f"EXTRACT(EPOCH FROM (NOW() - {due})) / 86400.0"

    query = (
        "SELECT fl.billing_entity,"
        " ROUND(CAST(SUM(fl.amount) AS NUMERIC), 2) AS total_ar,"
        f" ROUND(CAST(SUM(CASE WHEN {age} <= 0 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS current_not_due,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 0 AND {age} <= 30 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_1_30,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 30 AND {age} <= 60 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_31_60,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 60 AND {age} <= 90 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_61_90,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 90 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_90_plus"
        " FROM financial_ledger fl"
        " LEFT JOIN invoice_withdrawals iw ON fl.reference_id = iw.withdrawal_id AND fl.reference_type = 'withdrawal'"
        " LEFT JOIN invoices inv ON iw.invoice_id = inv.id"
        " WHERE fl.organization_id = $1"
        " AND fl.account = 'accounts_receivable'"
        " AND fl.billing_entity IS NOT NULL"
    )
    query += date_filter
    query += " GROUP BY fl.billing_entity HAVING ROUND(CAST(SUM(fl.amount) AS NUMERIC), 2) != 0"
    cursor = await conn.execute(query, params)
    return [ArAgingRow(**dict(r)) for r in await cursor.fetchall()]


async def product_margins(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[ProductMarginRow]:
    """Per-product revenue, COGS, profit, margin."""
    conn = get_connection()
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND created_at <= ${n}"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    limit_n = len(params) + 1
    query = (
        "SELECT sku_id,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost"
        " FROM financial_ledger"
        " WHERE organization_id = $1"
        " AND account IN ('revenue', 'cogs')"
        " AND sku_id IS NOT NULL"
    )
    query += date_filter + dim_filter
    query += f" GROUP BY sku_id ORDER BY revenue DESC LIMIT ${limit_n}"
    cursor = await conn.execute(query, [*params, limit])
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round_money(revenue - cost)
        result.append(
            ProductMarginRow(
                sku_id=row["sku_id"],
                revenue=revenue,
                cost=cost,
                profit=profit,
                # float for JSON-friendly percentage
                margin_pct=round(float(profit / revenue * 100), 1) if revenue > 0 else 0.0,
            )
        )
    return result


async def purchase_spend(
    start_date: str | None = None,
    end_date: str | None = None,
) -> float:
    """Total inventory additions from PO receipts in the period."""
    conn = get_connection()
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND created_at <= ${n}"
        params.append(end_date)

    query = (
        "SELECT ROUND(CAST(COALESCE(SUM(amount), 0) AS NUMERIC), 2) AS total"
        " FROM financial_ledger"
        " WHERE organization_id = $1"
        " AND account = 'inventory'"
        " AND reference_type = 'po_receipt'"
    )
    query += date_filter
    cursor = await conn.execute(query, params)
    row = await cursor.fetchone()
    return row[0] if row else 0.0


async def reference_counts(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, int]:
    """Count distinct references by type (withdrawal, return, etc.)."""
    conn = get_connection()
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND created_at <= ${n}"
        params.append(end_date)

    query = (
        "SELECT reference_type, COUNT(DISTINCT reference_id) AS cnt"
        " FROM financial_ledger"
        " WHERE organization_id = $1"
    )
    query += date_filter
    query += " GROUP BY reference_type"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def returns_total(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> float:
    """Sum of revenue reversed by returns (positive number)."""
    conn = get_connection()
    params: list = [get_org_id()]
    date_filter = ""
    if start_date:
        n = len(params) + 1
        date_filter += f" AND created_at >= ${n}"
        params.append(start_date)
    if end_date:
        n = len(params) + 1
        date_filter += f" AND created_at <= ${n}"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    query = (
        "SELECT COALESCE(ROUND(CAST(ABS(SUM(amount)) AS NUMERIC), 2), 0)"
        " FROM financial_ledger"
        " WHERE organization_id = $1"
        " AND reference_type = 'return'"
        " AND account = 'revenue'"
    )
    query += date_filter + dim_filter
    cursor = await conn.execute(query, params)
    row = await cursor.fetchone()
    return float(row[0]) if row and row[0] else 0.0


async def inventory_carrying_cost(
    holding_rate_pct: float = 25.0,
) -> list[dict]:
    """Estimated carrying cost per SKU with stock > 0.

    Uses last receiving event from stock_transactions to estimate how long
    inventory has been held. Groups by department. Annual holding rate defaults
    to 25% (industry standard for building materials — capital, storage,
    insurance, obsolescence).
    """
    conn = get_connection()
    org_id = get_org_id()

    cursor = await conn.execute(
        """WITH last_receipt AS (
               SELECT sku_id,
                      MAX(created_at::timestamp) AS last_received_at
               FROM stock_transactions
               WHERE transaction_type IN ('receiving', 'RECEIVING', 'import', 'IMPORT')
                 AND organization_id = $1
               GROUP BY sku_id
           )
           SELECT s.id AS sku_id, s.sku, s.name, s.quantity, s.cost,
                  s.category_name AS department, s.sell_uom,
                  COALESCE(
                      EXTRACT(EPOCH FROM (NOW() - lr.last_received_at)) / 86400.0,
                      EXTRACT(EPOCH FROM (NOW() - s.created_at::timestamp)) / 86400.0
                  ) AS days_held
           FROM skus s
           LEFT JOIN last_receipt lr ON lr.sku_id = s.id
           WHERE s.quantity > 0
             AND s.cost > 0
             AND s.organization_id = $1
             AND s.deleted_at IS NULL
           ORDER BY s.quantity * s.cost DESC""",
        (org_id,),
    )
    rows = await cursor.fetchall()
    daily_rate = holding_rate_pct / 100.0 / 365.0
    results = []
    for r in rows:
        row = dict(r)
        inv_value = row["quantity"] * row["cost"]
        days = float(row["days_held"])
        carrying = round(float(inv_value) * daily_rate * days, 2)
        results.append(
            {
                "sku_id": row["sku_id"],
                "sku": row["sku"],
                "name": row["name"],
                "quantity": row["quantity"],
                "cost": row["cost"],
                "inventory_value": round_money(inv_value),
                "days_held": round(days, 0),
                "carrying_cost": carrying,
                "department": row["department"],
                "sell_uom": row["sell_uom"],
            }
        )
    return results
