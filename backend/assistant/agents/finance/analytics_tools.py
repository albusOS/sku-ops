"""Finance analytics tools — expose ledger dimensional queries to the agent."""

import logging
from datetime import UTC, datetime, timedelta

from assistant.agents.tools.models import (
    ArAgingResult,
    CarryingCostResult,
    ContractorSpendResult,
    DeptProfitabilityResult,
    EntitySummaryResult,
    JobProfitabilityResult,
    PurchaseSpendResult,
    SkuMarginsResult,
    TrendSeriesResult,
)
from assistant.agents.tools.registry import register as _reg
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


def _date_range(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    return start, end


async def _get_trend_series(days: int = 30, group_by: str = "day") -> str:
    """Revenue/cost/profit time series grouped by day, week, or month."""
    days = min(days, 365)
    if group_by not in ("day", "week", "month"):
        group_by = "week" if days > 60 else "day"
    start, end = _date_range(days)
    series = await _db_finance().analytics_trend_series(
        get_org_id(),
        start_date=start,
        end_date=end,
        group_by=group_by,
    )
    return TrendSeriesResult(
        period_days=days,
        group_by=group_by,
        data_points=len(series),
        series=series,
    ).serialize()


async def _get_ar_aging(days: int = 365) -> str:
    """AR aging buckets by entity (current, 1-30, 31-60, 61-90, 90+)."""
    days = min(days, 730)
    start, end = _date_range(days)
    buckets = await _db_finance().analytics_ar_aging(get_org_id(), start_date=start, end_date=end)
    total_ar = round(sum(float(b.get("total_ar", 0)) for b in buckets), 2)
    return ArAgingResult(
        total_ar=total_ar,
        entity_count=len(buckets),
        buckets=buckets,
    ).serialize()


async def _get_sku_margins(days: int = 30, limit: int = 20) -> str:
    """Per-SKU margins over a period."""
    days = min(days, 365)
    limit = min(limit, 50)
    start, end = _date_range(days)
    margins = await _db_finance().analytics_product_margins(
        get_org_id(), start_date=start, end_date=end, limit=limit
    )
    return SkuMarginsResult(
        period_days=days,
        count=len(margins),
        skus=margins,
    ).serialize()


async def _get_department_profitability(days: int = 30) -> str:
    """Revenue, COGS, shrinkage, profit, and margin by department."""
    days = min(days, 365)
    start, end = _date_range(days)
    depts = await _db_finance().ledger_summary_by_department(
        get_org_id(), start_date=start, end_date=end
    )
    return DeptProfitabilityResult(
        period_days=days,
        department_count=len(depts),
        departments=depts,
    ).serialize()


async def _get_job_profitability(days: int = 30, limit: int = 20) -> str:
    """Revenue, cost, margin by job."""
    days = min(days, 365)
    limit = min(limit, 50)
    start, end = _date_range(days)
    result = await _db_finance().ledger_summary_by_job(
        get_org_id(), start_date=start, end_date=end, limit=limit
    )
    return JobProfitabilityResult(
        period_days=days,
        total_jobs=result.get("total", 0),
        all_revenue=float(result.get("all_revenue", 0)),
        all_cost=float(result.get("all_cost", 0)),
        jobs=result.get("rows", []),
    ).serialize()


async def _get_entity_summary(days: int = 30) -> str:
    """Revenue summary by billing entity."""
    days = min(days, 365)
    start, end = _date_range(days)
    entities = await _db_finance().ledger_summary_by_billing_entity(
        get_org_id(), start_date=start, end_date=end
    )
    return EntitySummaryResult(
        period_days=days,
        entity_count=len(entities),
        entities=entities,
    ).serialize()


async def _get_contractor_spend(days: int = 30) -> str:
    """Spend summary by contractor."""
    days = min(days, 365)
    start, end = _date_range(days)
    contractors = await _db_finance().ledger_summary_by_contractor(
        get_org_id(), start_date=start, end_date=end
    )
    return ContractorSpendResult(
        period_days=days,
        contractor_count=len(contractors),
        contractors=contractors,
    ).serialize()


async def _get_purchase_spend(days: int = 30) -> str:
    """Total purchase order spend over a period."""
    days = min(days, 365)
    start, end = _date_range(days)
    total = await _db_finance().analytics_purchase_spend(
        get_org_id(), start_date=start, end_date=end
    )
    return PurchaseSpendResult(
        period_days=days,
        total_purchase_spend=float(total),
    ).serialize()


async def _get_carrying_cost(holding_rate_pct: float = 25.0) -> str:
    """Estimated holding cost of current inventory, grouped by department."""
    rate = float(holding_rate_pct)
    items = await _db_finance().analytics_inventory_carrying_cost(
        get_org_id(), holding_rate_pct=rate
    )
    total = round(sum(float(i["carrying_cost"]) for i in items), 2)
    by_dept: dict[str, float] = {}
    for i in items:
        dept = i["department"] or "Unknown"
        by_dept[dept] = round(by_dept.get(dept, 0) + float(i["carrying_cost"]), 2)
    return CarryingCostResult(
        holding_rate_pct=rate,
        total_carrying_cost=total,
        sku_count=len(items),
        by_department=by_dept,
        top_items=items[:20],
        _note=f"Carrying cost = inventory_value * {rate}% annual rate * days_held / 365",
    ).serialize()


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "get_trend_series",
    "finance_analytics",
    _get_trend_series,
    use_cases=["trends", "time series", "revenue chart"],
)
_reg(
    "get_ar_aging",
    "finance_analytics",
    _get_ar_aging,
    use_cases=["AR aging", "receivables", "overdue"],
)
_reg(
    "get_sku_margins",
    "finance_analytics",
    _get_sku_margins,
    use_cases=["margins", "profitability by SKU"],
)
_reg(
    "get_department_profitability",
    "finance_analytics",
    _get_department_profitability,
    use_cases=["department profit", "dept margins"],
)
_reg(
    "get_job_profitability",
    "finance_analytics",
    _get_job_profitability,
    use_cases=["job profitability", "job margins"],
)
_reg(
    "get_entity_summary",
    "finance_analytics",
    _get_entity_summary,
    use_cases=["entity summary", "billing entity"],
)
_reg(
    "get_contractor_spend",
    "finance_analytics",
    _get_contractor_spend,
    use_cases=["contractor spend", "contractor cost"],
)
_reg(
    "get_purchase_spend",
    "finance_analytics",
    _get_purchase_spend,
    use_cases=["purchase spend", "PO spend"],
)
_reg(
    "get_carrying_cost",
    "finance_analytics",
    _get_carrying_cost,
    use_cases=["carrying cost", "holding cost", "inventory cost"],
)
