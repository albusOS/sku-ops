"""Ledger analytics — time series, AR aging, product margins, purchase analytics.

Split from ledger_queries.py for file-size discipline. All functions are
re-exported from ledger_queries so existing callers are unaffected.

Implementation lives in ``FinanceDatabaseService`` (SQLAlchemy session + ``text()``).
"""

from finance.domain.ledger_analytics_rows import (
    ArAgingRow,
    ProductMarginRow,
    TrendPoint,
)
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


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
    return await get_database_manager().finance.analytics_trend_series(
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
    return await get_database_manager().finance.analytics_ar_aging(
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
    return await get_database_manager().finance.analytics_product_margins(
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
    return await get_database_manager().finance.analytics_purchase_spend(
        get_org_id(), start_date=start_date, end_date=end_date
    )


async def reference_counts(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, int]:
    """Count distinct references by type (withdrawal, return, etc.)."""
    return await get_database_manager().finance.analytics_reference_counts(
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
    return await get_database_manager().finance.analytics_returns_total(
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
    return (
        await get_database_manager().finance.analytics_inventory_carrying_cost(
            get_org_id(), holding_rate_pct=holding_rate_pct
        )
    )
