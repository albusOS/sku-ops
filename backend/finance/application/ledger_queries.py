"""Ledger read queries — dimension summaries, analytics, and cross-context delegations.

Cross-context consumers import from here, never from finance.infrastructure directly.
Write operations use the finance database service (see ``ledger_service``).
"""

from typing import TypedDict

from finance.domain.ledger_analytics_rows import (
    ArAgingRow,
    ProductMarginRow,
    TrendPoint,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


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
    return await _db_finance().analytics_trend_series(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )


async def ar_aging(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ArAgingRow]:
    """AR aging buckets by billing entity based on invoice due_date."""
    return await _db_finance().analytics_ar_aging(
        get_org_id(), start_date=start_date, end_date=end_date
    )


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
    return await _db_finance().analytics_product_margins(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )


async def purchase_spend(
    start_date: str | None = None,
    end_date: str | None = None,
) -> float:
    """Total inventory additions from PO receipts in the period."""
    return await _db_finance().analytics_purchase_spend(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def reference_counts(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, int]:
    """Count distinct references by type (withdrawal, return, etc.)."""
    return await _db_finance().analytics_reference_counts(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def returns_total(
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> float:
    """Sum of revenue reversed by returns (positive number)."""
    return await _db_finance().analytics_returns_total(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )


async def inventory_carrying_cost(
    holding_rate_pct: float = 25.0,
) -> list[dict]:
    """Estimated carrying cost per SKU with stock > 0."""
    return await _db_finance().analytics_inventory_carrying_cost(
        get_org_id(), holding_rate_pct=holding_rate_pct
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
    return await _db_finance().ledger_summary_by_account(
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
    return await _db_finance().ledger_summary_by_department(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def summary_by_job(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> JobSummaryResult:
    """Per-job P&L with pagination and search. Returns {rows, total}."""
    return await _db_finance().ledger_summary_by_job(
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
    return await _db_finance().ledger_summary_by_billing_entity(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def summary_by_contractor(
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ContractorSummaryRow]:
    """Per-contractor spend totals."""
    return await _db_finance().ledger_summary_by_contractor(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def units_sold_by_product(
    org_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Delegate to operations context (owns withdrawal data)."""
    return await _db_operations().units_sold_by_product(
        org_id, start_date=start_date, end_date=end_date
    )


async def payment_status_breakdown(
    org_id: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    """Delegate to operations context (owns withdrawal data)."""
    return await _db_operations().payment_status_breakdown(
        org_id, start_date=start_date, end_date=end_date
    )
