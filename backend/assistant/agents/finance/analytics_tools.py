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
from finance.application.ledger_analytics import (
    ar_aging,
    inventory_carrying_cost,
    product_margins,
    purchase_spend,
    trend_series,
)
from finance.application.ledger_queries import (
    summary_by_billing_entity,
    summary_by_contractor,
    summary_by_department,
    summary_by_job,
)

logger = logging.getLogger(__name__)


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


async def _get_trend_series(days: int = 30, group_by: str = "day") -> str:
    """Revenue/cost/profit time series grouped by day, week, or month."""
    days = min(days, 365)
    if group_by not in ("day", "week", "month"):
        group_by = "week" if days > 60 else "day"
    start, end = _date_range(days)
    series = await trend_series(start, end, group_by)
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
    buckets = await ar_aging(start, end)
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
    margins = await product_margins(start, end, limit)
    return SkuMarginsResult(
        period_days=days,
        count=len(margins),
        skus=margins,
    ).serialize()


async def _get_department_profitability(days: int = 30) -> str:
    """Revenue, COGS, shrinkage, profit, and margin by department."""
    days = min(days, 365)
    start, end = _date_range(days)
    depts = await summary_by_department(start, end)
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
    result = await summary_by_job(start, end, limit=limit)
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
    entities = await summary_by_billing_entity(start, end)
    return EntitySummaryResult(
        period_days=days,
        entity_count=len(entities),
        entities=entities,
    ).serialize()


async def _get_contractor_spend(days: int = 30) -> str:
    """Spend summary by contractor."""
    days = min(days, 365)
    start, end = _date_range(days)
    contractors = await summary_by_contractor(start, end)
    return ContractorSpendResult(
        period_days=days,
        contractor_count=len(contractors),
        contractors=contractors,
    ).serialize()


async def _get_purchase_spend(days: int = 30) -> str:
    """Total purchase order spend over a period."""
    days = min(days, 365)
    start, end = _date_range(days)
    total = await purchase_spend(start, end)
    return PurchaseSpendResult(
        period_days=days,
        total_purchase_spend=float(total),
    ).serialize()


async def _get_carrying_cost(holding_rate_pct: float = 25.0) -> str:
    """Estimated holding cost of current inventory, grouped by department."""
    rate = float(holding_rate_pct)
    items = await inventory_carrying_cost(rate)
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
