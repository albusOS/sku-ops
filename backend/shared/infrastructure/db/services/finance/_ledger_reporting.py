"""Ledger summaries and analytics via bound SQLAlchemy ``text()`` (explicit ``org_id``)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

from finance.domain.ledger_analytics_rows import (
    ArAgingRow,
    ProductMarginRow,
    TrendPoint,
)
from shared.infrastructure.db.orm_utils import parse_date_param
from shared.kernel.types import round_money

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _build_dimension_sql(
    params: dict[str, Any],
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
    col_prefix: str = "",
) -> str:
    p = col_prefix + "." if col_prefix else ""
    frag = ""
    if job_id:
        params["dim_job_id"] = job_id
        frag += f" AND {p}job_id = CAST(:dim_job_id AS uuid)"
    if department:
        params["dim_department"] = department
        frag += f" AND {p}department = :dim_department"
    if billing_entity:
        params["dim_billing_entity"] = billing_entity
        frag += f" AND {p}billing_entity = :dim_billing_entity"
    return frag


def _ledger_date_sql(
    params: dict[str, Any],
    *,
    start_date: str | None,
    end_date: str | None,
    column: str = "created_at",
) -> str:
    """Bind ISO date strings as datetimes so asyncpg encodes ``timestamptz`` params."""
    frag = ""
    start_bound = parse_date_param(start_date)
    if start_bound is not None:
        params["start_date"] = start_bound
        frag += f" AND {column} >= CAST(:start_date AS timestamptz)"
    end_bound = parse_date_param(end_date)
    if end_bound is not None:
        params["end_date"] = end_bound
        frag += f" AND {column} <= CAST(:end_date AS timestamptz)"
    return frag


async def summary_by_account(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> dict[str, float]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    dim_sql = _build_dimension_sql(
        params,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )
    sql = (
        "SELECT account, ROUND(CAST(SUM(amount) AS NUMERIC), 2) AS total"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id" + date_sql + dim_sql + " GROUP BY account"
    )
    r = await session.execute(text(sql), params)
    return {row[0]: float(row[1]) for row in r.all()}


async def trend_series(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    group_by: str = "day",
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[TrendPoint]:
    if group_by == "week":
        period_expr = "to_char(created_at::date, 'IYYY-\"W\"IW')"
    elif group_by == "month":
        period_expr = "to_char(created_at::date, 'YYYY-MM')"
    else:
        period_expr = "to_char(created_at::date, 'YYYY-MM-DD')"
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    dim_sql = _build_dimension_sql(
        params,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )
    sql = (
        f"SELECT {period_expr} AS period,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost,"
        " ROUND(CAST(SUM(CASE WHEN account = 'shrinkage' THEN amount ELSE 0 END) AS NUMERIC), 2) AS shrinkage,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND account IN ('revenue', 'cogs', 'shrinkage')"
        + date_sql
        + dim_sql
        + " GROUP BY period ORDER BY period"
    )
    r = await session.execute(text(sql), params)
    series: list[TrendPoint] = []
    for row in r.mappings().all():
        revenue = row["revenue"]
        cost = row["cost"]
        shrinkage = row["shrinkage"]
        profit = round_money(revenue - cost - shrinkage)
        series.append(
            TrendPoint(
                date=row["period"],
                revenue=revenue,
                cost=cost,
                shrinkage=shrinkage,
                profit=profit,
                transaction_count=row["transaction_count"],
            )
        )
    return series


async def ar_aging(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ArAgingRow]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(
        params,
        start_date=start_date,
        end_date=end_date,
        column="fl.created_at",
    )
    fallback = "fl.created_at::timestamp + INTERVAL '30 days'"
    due = f"COALESCE(inv.due_date::timestamp, {fallback})"
    age = f"EXTRACT(EPOCH FROM (NOW() - {due})) / 86400.0"
    sql = (
        "SELECT fl.billing_entity,"
        " ROUND(CAST(SUM(fl.amount) AS NUMERIC), 2) AS total_ar,"
        f" ROUND(CAST(SUM(CASE WHEN {age} <= 0 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS current_not_due,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 0 AND {age} <= 30 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_1_30,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 30 AND {age} <= 60 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_31_60,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 60 AND {age} <= 90 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_61_90,"
        f" ROUND(CAST(SUM(CASE WHEN {age} > 90 THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS overdue_90_plus"
        " FROM financial_ledger fl"
        " LEFT JOIN invoice_withdrawals iw ON fl.reference_id = iw.withdrawal_id::text AND fl.reference_type = 'withdrawal'"
        " LEFT JOIN invoices inv ON iw.invoice_id = inv.id"
        " WHERE fl.organization_id = :org_id"
        " AND fl.account = 'accounts_receivable'"
        " AND fl.billing_entity IS NOT NULL"
        + date_sql
        + " GROUP BY fl.billing_entity HAVING ROUND(CAST(SUM(fl.amount) AS NUMERIC), 2) != 0"
    )
    r = await session.execute(text(sql), params)
    return [ArAgingRow(**dict(m)) for m in r.mappings().all()]


async def product_margins(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> list[ProductMarginRow]:
    params: dict[str, Any] = {"org_id": org_id, "lim": limit}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    dim_sql = _build_dimension_sql(
        params,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )
    sql = (
        "SELECT sku_id::text AS sku_id,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND account IN ('revenue', 'cogs')"
        " AND sku_id IS NOT NULL"
        + date_sql
        + dim_sql
        + " GROUP BY sku_id ORDER BY revenue DESC LIMIT :lim"
    )
    r = await session.execute(text(sql), params)
    result: list[ProductMarginRow] = []
    for row in r.mappings().all():
        revenue = row["revenue"]
        cost = row["cost"]
        profit = round_money(revenue - cost)
        rev_f = float(revenue)
        result.append(
            ProductMarginRow(
                sku_id=row["sku_id"],
                revenue=revenue,
                cost=cost,
                profit=profit,
                margin_pct=round(float(profit) / rev_f * 100, 1) if rev_f > 0 else 0.0,
            )
        )
    return result


async def purchase_spend(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> float:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    sql = (
        "SELECT ROUND(CAST(COALESCE(SUM(amount), 0) AS NUMERIC), 2) AS total"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND account = 'inventory'"
        " AND reference_type = 'po_receipt'" + date_sql
    )
    r = await session.execute(text(sql), params)
    row = r.first()
    return float(row[0]) if row and row[0] is not None else 0.0


async def reference_counts(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, int]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    sql = (
        "SELECT reference_type, COUNT(DISTINCT reference_id) AS cnt"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id" + date_sql + " GROUP BY reference_type"
    )
    r = await session.execute(text(sql), params)
    return {row[0]: row[1] for row in r.all()}


async def returns_total(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> float:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    dim_sql = _build_dimension_sql(
        params,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )
    sql = (
        "SELECT COALESCE(ROUND(CAST(ABS(SUM(amount)) AS NUMERIC), 2), 0)"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND reference_type = 'return'"
        " AND account = 'revenue'" + date_sql + dim_sql
    )
    r = await session.execute(text(sql), params)
    row = r.first()
    return float(row[0]) if row and row[0] is not None else 0.0


async def summary_by_department(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    sql = (
        "SELECT department,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost,"
        " ROUND(CAST(SUM(CASE WHEN account = 'shrinkage' THEN amount ELSE 0 END) AS NUMERIC), 2) AS shrinkage"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND account IN ('revenue', 'cogs', 'shrinkage')"
        " AND department IS NOT NULL" + date_sql + " GROUP BY department"
    )
    r = await session.execute(text(sql), params)
    return [dict(row._mapping) for row in r.all()]


async def summary_by_billing_entity(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    sql = (
        "SELECT billing_entity,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost,"
        " ROUND(CAST(SUM(CASE WHEN account = 'accounts_receivable' THEN amount ELSE 0 END) AS NUMERIC), 2) AS ar_balance,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND billing_entity IS NOT NULL" + date_sql + " GROUP BY billing_entity"
    )
    r = await session.execute(text(sql), params)
    return [dict(row._mapping) for row in r.all()]


async def summary_by_contractor_raw(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(
        params,
        start_date=start_date,
        end_date=end_date,
        column="fl.created_at",
    )
    sql = (
        "SELECT fl.contractor_id::text AS contractor_id,"
        " ROUND(CAST(SUM(CASE WHEN fl.account = 'revenue' THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN fl.account = 'accounts_receivable' THEN fl.amount ELSE 0 END) AS NUMERIC), 2) AS ar_balance,"
        " COUNT(DISTINCT fl.reference_id) AS transaction_count"
        " FROM financial_ledger fl"
        " WHERE fl.organization_id = :org_id"
        " AND fl.contractor_id IS NOT NULL" + date_sql + " GROUP BY fl.contractor_id"
    )
    r = await session.execute(text(sql), params)
    return [dict(row._mapping) for row in r.all()]


async def summary_by_job_aggregate(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, float, float]:
    """Returns (page rows, total count, all_revenue, all_cost)."""
    params: dict[str, Any] = {"org_id": org_id}
    date_sql = _ledger_date_sql(params, start_date=start_date, end_date=end_date)
    base = (
        "SELECT job_id::text AS job_id,"
        " billing_entity,"
        " ROUND(CAST(SUM(CASE WHEN account = 'revenue' THEN amount ELSE 0 END) AS NUMERIC), 2) AS revenue,"
        " ROUND(CAST(SUM(CASE WHEN account = 'cogs' THEN amount ELSE 0 END) AS NUMERIC), 2) AS cost,"
        " COUNT(DISTINCT reference_id) AS transaction_count"
        " FROM financial_ledger"
        " WHERE organization_id = :org_id"
        " AND account IN ('revenue', 'cogs')"
        " AND job_id IS NOT NULL" + date_sql + " GROUP BY job_id, billing_entity"
    )
    search_clause = ""
    if search:
        term = f"%{search}%"
        params["search_a"] = term
        params["search_b"] = term
        search_clause = (
            " HAVING CAST(job_id AS text) LIKE :search_a OR billing_entity LIKE :search_b"
        )
    count_sql = (
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(revenue), 0) AS total_revenue,"
        " COALESCE(SUM(cost), 0) AS total_cost FROM (" + base + search_clause + ") t"
    )
    cr = await session.execute(text(count_sql), params)
    crow = cr.mappings().first()
    total = int(crow["cnt"]) if crow else 0
    all_revenue = float(crow["total_revenue"]) if crow else 0.0
    all_cost = float(crow["total_cost"]) if crow else 0.0
    params_page = {**params, "lim": limit, "off": offset}
    data_sql = base + search_clause + " ORDER BY revenue DESC LIMIT :lim OFFSET :off"
    dr = await session.execute(text(data_sql), params_page)
    rows = [dict(row._mapping) for row in dr.all()]
    return rows, total, all_revenue, all_cost


async def inventory_carrying_cost(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    holding_rate_pct: float = 25.0,
) -> list[dict]:
    sql = text(
        """WITH last_receipt AS (
               SELECT sku_id,
                      MAX(created_at::timestamp) AS last_received_at
               FROM stock_transactions
               WHERE transaction_type IN ('receiving', 'RECEIVING', 'import', 'IMPORT')
                 AND organization_id = :org_id
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
             AND s.organization_id = :org_id
             AND s.deleted_at IS NULL
           ORDER BY s.quantity * s.cost DESC"""
    )
    r = await session.execute(sql, {"org_id": org_id})
    daily_rate = holding_rate_pct / 100.0 / 365.0
    results = []
    for row in r.mappings().all():
        row = dict(row)
        inv_value = row["quantity"] * row["cost"]
        days = float(row["days_held"])
        carrying = round(float(inv_value) * daily_rate * days, 2)
        results.append(
            {
                "sku_id": str(row["sku_id"]),
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
