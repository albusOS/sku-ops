"""Ledger read queries — dimension summaries and cross-context delegations.

Cross-context consumers import from here, never from finance.infrastructure directly.
Write operations use ``get_database_manager().finance`` (see ``ledger_service``).

Analytics queries (trend_series, ar_aging, product_margins, purchase_spend,
reference_counts) live in ledger_analytics.py and are re-exported below.
"""

# Re-export write-path helpers that some callers (tests, ledger_service) need via this module.
# Re-export analytics so callers using `from finance.application import ledger_queries` see everything.
from typing import TypedDict

from finance.application.ledger_analytics import (  # noqa: F401
    ArAgingRow,
    ProductMarginRow,
    TrendPoint,
    ar_aging,
    product_margins,
    purchase_spend,
    reference_counts,
    returns_total,
    trend_series,
)
from operations.application.queries import (
    payment_status_breakdown as _ops_pmt_status,
)
from operations.application.queries import (
    units_sold_by_product as _ops_units_sold,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def get_journal(journal_id: str) -> list[dict]:
    """All ledger lines for a single journal transaction."""
    return await get_database_manager().finance.ledger_get_journal(
        get_org_id(), journal_id
    )


class DepartmentSummaryRow(TypedDict):
    department: str
    revenue: float
    cost: float
    shrinkage: float
    profit: float
    margin_pct: float


class JobSummaryRow(TypedDict):
    job_id: str
    billing_entity: str
    revenue: float
    cost: float
    profit: float
    margin_pct: float
    withdrawal_count: int


class JobSummaryResult(TypedDict):
    rows: list[JobSummaryRow]
    total: int
    all_revenue: float
    all_cost: float


class BillingEntitySummaryRow(TypedDict):
    billing_entity: str
    revenue: float
    cost: float
    profit: float
    ar_balance: float
    transaction_count: int


class ContractorSummaryRow(TypedDict):
    contractor_id: str
    revenue: float
    ar_balance: float
    transaction_count: int
    name: str
    company: str


async def summary_by_account(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> dict[str, float]:
    """P&L summary: {account_name: total_amount}."""
    return await get_database_manager().finance.ledger_summary_by_account(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )


async def summary_by_department(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[DepartmentSummaryRow]:
    """Per-department revenue, cogs, shrinkage."""
    rows = await get_database_manager().finance.ledger_summary_by_department(
        get_org_id(), start_date=start_date, end_date=end_date
    )
    return [DepartmentSummaryRow(**r) for r in rows]


async def summary_by_job(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> JobSummaryResult:
    """Per-job P&L with pagination and search. Returns {rows, total}."""
    return await get_database_manager().finance.ledger_summary_by_job(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        search=search,
    )


async def summary_by_billing_entity(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[BillingEntitySummaryRow]:
    """Per-entity AR balances and revenue."""
    rows = (
        await get_database_manager().finance.ledger_summary_by_billing_entity(
            get_org_id(), start_date=start_date, end_date=end_date
        )
    )
    return [BillingEntitySummaryRow(**r) for r in rows]


async def summary_by_contractor(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ContractorSummaryRow]:
    """Per-contractor spend totals."""
    rows = await get_database_manager().finance.ledger_summary_by_contractor(
        get_org_id(), start_date=start_date, end_date=end_date
    )
    return [ContractorSummaryRow(**r) for r in rows]


async def units_sold_by_product(
    org_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Delegate to operations context (owns withdrawal data)."""
    return await _ops_units_sold(org_id, start_date, end_date)


async def payment_status_breakdown(
    org_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Delegate to operations context (owns withdrawal data)."""
    return await _ops_pmt_status(org_id, start_date, end_date)
