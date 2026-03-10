"""Ledger read queries — analytics and reporting.

Cross-context consumers import from here, never from finance.infrastructure directly.
Write operations (insert_entries, entries_exist) remain in finance.infrastructure.ledger_repo.
"""

# Re-export write-path helpers that some callers (tests, ledger_service) need via this module.
from finance.infrastructure.ledger_repo import get_journal, trial_balance  # noqa: F401
from shared.infrastructure.database import get_connection
from shared.infrastructure.db.sql_compat import date_group_expr


def _build_dimension_filter(
    params: list,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
    col_prefix: str = "",
) -> str:
    """Append optional WHERE clauses for dimension drill-down filtering."""
    sql = ""
    p = col_prefix + "." if col_prefix else ""
    if job_id:
        sql += " AND " + p + "job_id = ?"
        params.append(job_id)
    if department:
        sql += " AND " + p + "department = ?"
        params.append(department)
    if billing_entity:
        sql += " AND " + p + "billing_entity = ?"
        params.append(billing_entity)
    return sql


async def summary_by_account(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> dict[str, float]:
    """P&L summary: {account_name: total_amount}."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    query = (
        "SELECT account, ROUND(SUM(amount), 2) AS total"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
    )
    query += date_filter + dim_filter
    query += " GROUP BY account"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def summary_by_department(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Per-department revenue, cogs, shrinkage."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT department,"
        " ROUND(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END), 2) AS cost,"
        " ROUND(SUM(CASE WHEN account = 'shrinkage' THEN amount ELSE 0 END), 2) AS shrinkage"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
        " AND account IN ('revenue', 'cogs', 'shrinkage')"
        " AND department IS NOT NULL"
    )
    query += date_filter
    query += " GROUP BY department"
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round(revenue - cost, 2)
        result.append(
            {
                "department": row["department"],
                "revenue": revenue,
                "cost": cost,
                "shrinkage": row["shrinkage"],
                "profit": profit,
                "margin_pct": round(profit / revenue * 100, 1) if revenue > 0 else 0,
            }
        )
    return result


async def summary_by_job(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> dict:
    """Per-job P&L with pagination and search. Returns {rows, total}."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)

    base = (
        "SELECT job_id,"
        " billing_entity,"
        " ROUND(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END), 2) AS cost,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
        " AND account IN ('revenue', 'cogs')"
        " AND job_id IS NOT NULL"
    )
    base += date_filter
    base += " GROUP BY job_id, billing_entity"

    search_clause = ""
    search_params: list = []
    if search:
        term = f"%{search}%"
        search_clause = " HAVING job_id LIKE ? OR billing_entity LIKE ?"
        search_params = [term, term]

    count_query = f"SELECT COUNT(*) AS cnt, COALESCE(SUM(revenue), 0) AS total_revenue, COALESCE(SUM(cost), 0) AS total_cost FROM ({base}{search_clause})"
    count_cursor = await conn.execute(count_query, [*params, *search_params])
    agg = dict(await count_cursor.fetchone())
    total = agg["cnt"]
    all_revenue = float(agg["total_revenue"])
    all_cost = float(agg["total_cost"])

    data_query = f"{base}{search_clause} ORDER BY revenue DESC LIMIT ? OFFSET ?"
    cursor = await conn.execute(data_query, [*params, *search_params, limit, offset])
    rows = await cursor.fetchall()

    result = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round(revenue - cost, 2)
        result.append(
            {
                "job_id": row["job_id"],
                "billing_entity": row["billing_entity"],
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "margin_pct": round(profit / revenue * 100, 1) if revenue > 0 else 0,
                "withdrawal_count": row["transaction_count"],
            }
        )
    return {"rows": result, "total": total, "all_revenue": all_revenue, "all_cost": all_cost}


async def summary_by_billing_entity(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Per-entity AR balances and revenue."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT billing_entity,"
        " ROUND(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END), 2) AS cost,"
        " ROUND(SUM(CASE WHEN account = 'accounts_receivable' THEN amount ELSE 0 END), 2) AS ar_balance,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
        " AND billing_entity IS NOT NULL"
    )
    query += date_filter
    query += " GROUP BY billing_entity"
    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round(revenue - cost, 2)
        result.append(
            {
                "billing_entity": row["billing_entity"],
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "ar_balance": row["ar_balance"],
                "transaction_count": row["transaction_count"],
            }
        )
    return result


async def summary_by_contractor(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Per-contractor spend totals."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND fl.created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND fl.created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT fl.contractor_id,"
        " COALESCE(MAX(u.name), '') AS name,"
        " COALESCE(MAX(u.company), '') AS company,"
        " ROUND(SUM(CASE WHEN fl.account = 'revenue' THEN fl.amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN fl.account = 'accounts_receivable' THEN fl.amount ELSE 0 END), 2) AS ar_balance,"
        " COUNT(DISTINCT fl.reference_id) AS transaction_count"
        " FROM financial_ledger fl"
        " LEFT JOIN users u ON u.id = fl.contractor_id"
        " WHERE fl.organization_id = ?"
        " AND fl.contractor_id IS NOT NULL"
    )
    query += date_filter
    query += " GROUP BY fl.contractor_id"
    cursor = await conn.execute(query, params)
    return [dict(r) for r in await cursor.fetchall()]


async def trend_series(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    group_by: str = "day",
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[dict]:
    """Time-series of revenue, cost, profit."""
    conn = get_connection()
    period_expr = date_group_expr("created_at", group_by)
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    query = "SELECT "
    query += period_expr
    query += (
        " AS period,"
        " ROUND(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END), 2) AS cost,"
        " ROUND(SUM(CASE WHEN account = 'shrinkage' THEN amount ELSE 0 END), 2) AS shrinkage,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
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
        profit = round(revenue - cost - row["shrinkage"], 2)
        series.append(
            {
                "date": row["period"],
                "revenue": revenue,
                "cost": cost,
                "shrinkage": row["shrinkage"],
                "profit": profit,
                "transaction_count": row["transaction_count"],
            }
        )
    return series


async def ar_aging(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """AR aging buckets by billing entity based on invoice due_date."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND fl.created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND fl.created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT fl.billing_entity,"
        " ROUND(SUM(fl.amount), 2) AS total_ar,"
        " ROUND(SUM(CASE WHEN julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) <= 0 THEN fl.amount ELSE 0 END), 2) AS current_not_due,"
        " ROUND(SUM(CASE WHEN julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) > 0"
        " AND julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) <= 30 THEN fl.amount ELSE 0 END), 2) AS overdue_1_30,"
        " ROUND(SUM(CASE WHEN julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) > 30"
        " AND julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) <= 60 THEN fl.amount ELSE 0 END), 2) AS overdue_31_60,"
        " ROUND(SUM(CASE WHEN julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) > 60"
        " AND julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) <= 90 THEN fl.amount ELSE 0 END), 2) AS overdue_61_90,"
        " ROUND(SUM(CASE WHEN julianday('now') - julianday(COALESCE(inv.due_date, datetime(fl.created_at, '+30 days'))) > 90 THEN fl.amount ELSE 0 END), 2) AS overdue_90_plus"
        " FROM financial_ledger fl"
        " LEFT JOIN invoice_withdrawals iw ON fl.reference_id = iw.withdrawal_id AND fl.reference_type = 'withdrawal'"
        " LEFT JOIN invoices inv ON iw.invoice_id = inv.id"
        " WHERE fl.organization_id = ?"
        " AND fl.account = 'accounts_receivable'"
        " AND fl.billing_entity IS NOT NULL"
    )
    query += date_filter
    query += " GROUP BY fl.billing_entity HAVING ROUND(SUM(fl.amount), 2) != 0"
    cursor = await conn.execute(query, params)
    return [dict(r) for r in await cursor.fetchall()]


async def product_margins(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[dict]:
    """Per-product revenue, COGS, profit, margin."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)
    dim_filter = _build_dimension_filter(
        params, job_id=job_id, department=department, billing_entity=billing_entity
    )

    query = (
        "SELECT product_id,"
        " ROUND(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END), 2) AS revenue,"
        " ROUND(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END), 2) AS cost"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
        " AND account IN ('revenue', 'cogs')"
        " AND product_id IS NOT NULL"
    )
    query += date_filter + dim_filter
    query += " GROUP BY product_id ORDER BY revenue DESC LIMIT ?"
    cursor = await conn.execute(query, [*params, limit])
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        row = dict(r)
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round(revenue - cost, 2)
        result.append(
            {
                "product_id": row["product_id"],
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "margin_pct": round(profit / revenue * 100, 1) if revenue > 0 else 0,
            }
        )
    return result


async def units_sold_by_product(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Sum of quantities sold per product_id from withdrawal_items."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND w.created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND w.created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT wi.product_id, SUM(wi.quantity) AS total_qty"
        " FROM withdrawal_items wi"
        " JOIN withdrawals w ON wi.withdrawal_id = w.id"
        " WHERE w.organization_id = ?"
    )
    query += date_filter
    query += " GROUP BY wi.product_id"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def payment_status_breakdown(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Revenue breakdown by payment status: {Paid: X, Invoiced: Y, Unpaid: Z}."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND w.created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND w.created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT"
        " CASE"
        " WHEN w.payment_status = 'paid' THEN 'Paid'"
        " WHEN w.invoice_id IS NOT NULL THEN 'Invoiced'"
        " ELSE 'Unpaid'"
        " END AS status,"
        " ROUND(SUM(w.total), 2) AS total"
        " FROM withdrawals w"
        " WHERE w.organization_id = ?"
    )
    query += date_filter
    query += " GROUP BY status"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}


async def purchase_spend(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> float:
    """Total inventory additions from PO receipts in the period."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT ROUND(COALESCE(SUM(amount), 0), 2) AS total"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
        " AND account = 'inventory'"
        " AND reference_type = 'po_receipt'"
    )
    query += date_filter
    cursor = await conn.execute(query, params)
    row = await cursor.fetchone()
    return row[0] if row else 0.0


async def reference_counts(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, int]:
    """Count distinct references by type (withdrawal, return, etc.)."""
    conn = get_connection()
    params: list = [org_id]
    date_filter = ""
    if start_date:
        date_filter += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        date_filter += " AND created_at <= ?"
        params.append(end_date)

    query = (
        "SELECT reference_type, COUNT(DISTINCT reference_id) AS cnt"
        " FROM financial_ledger"
        " WHERE organization_id = ?"
    )
    query += date_filter
    query += " GROUP BY reference_type"
    cursor = await conn.execute(query, params)
    return {row[0]: row[1] for row in await cursor.fetchall()}
