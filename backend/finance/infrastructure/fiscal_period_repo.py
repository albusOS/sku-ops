"""Fiscal period repository — persistence for fiscal periods."""

from datetime import datetime

from finance.domain.fiscal_period import FiscalPeriod
from shared.infrastructure.db import get_org_id, sql_execute


async def get_period(period_id: str) -> FiscalPeriod | None:
    org_id = get_org_id()
    cursor = await sql_execute(
        "SELECT * FROM fiscal_periods WHERE id = $1 AND organization_id = $2",
        (period_id, org_id),
    )
    row = cursor.rows[0] if cursor.rows else None
    return FiscalPeriod.model_validate(dict(row)) if row else None


async def list_periods(status: str | None = None) -> list[FiscalPeriod]:
    org_id = get_org_id()
    n = 1
    query = f"SELECT * FROM fiscal_periods WHERE organization_id = ${n}"
    params: list = [org_id]
    n += 1
    if status:
        query += f" AND status = ${n}"
        params.append(status)
        n += 1
    query += " ORDER BY start_date DESC"
    cursor = await sql_execute(query, params)
    return [FiscalPeriod.model_validate(dict(r)) for r in cursor.rows]


async def insert_period(
    period_id: str,
    name: str,
    start_date: str,
    end_date: str,
    created_at: datetime,
) -> None:
    org_id = get_org_id()
    await sql_execute(
        """INSERT INTO fiscal_periods (id, name, start_date, end_date, status, organization_id, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        (period_id, name, start_date, end_date, "open", org_id, created_at),
    )


async def close_period(
    period_id: str, closed_by_id: str, closed_at: str
) -> None:
    org_id = get_org_id()
    await sql_execute(
        "UPDATE fiscal_periods SET status = 'closed', closed_by_id = $1, closed_at = $2 WHERE id = $3 AND organization_id = $4",
        (closed_by_id, closed_at, period_id, org_id),
    )


async def find_closed_period_covering(
    entry_date: str | datetime,
) -> tuple[str, str] | None:
    """Return (id, name) of a closed fiscal period covering entry_date, or None."""
    if isinstance(entry_date, str):
        entry_date = datetime.fromisoformat(entry_date)
    org_id = get_org_id()
    cursor = await sql_execute(
        """SELECT id, name FROM fiscal_periods
           WHERE organization_id = $1 AND status = 'closed'
             AND $2 >= start_date AND $3 <= end_date
           LIMIT 1""",
        (org_id, entry_date, entry_date),
    )
    row = cursor.rows[0] if cursor.rows else None
    return (row["id"], row["name"]) if row else None
