"""Inventory agent tool implementations — facade-backed queries and search helpers."""

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from assistant.agents.tools.models import (
    DemandProfileResult,
    DepartmentActivityResult,
    DepartmentHealth,
    DepartmentHealthResult,
    DepartmentInfo,
    DepartmentListResult,
    ErrorResult,
    InventoryStats,
    ReorderSuggestion,
    ReorderSuggestionsResult,
    SeasonalPatternResult,
    SemanticEntityResult,
    SemanticSearchResult,
    SkuDetail,
    SkuRanked,
    SkuSearchResult,
    SkuSummary,
    SlowMover,
    SlowMoversResult,
    StockoutForecastResult,
    StockoutItem,
    TopSkusResult,
    UsageVelocityResult,
    VendorListResult,
    VendorSummary,
)
from assistant.agents.tools.registry import register as _reg
from assistant.agents.tools.search import get_index
from catalog.application.queries import (
    count_all_skus as catalog_count_all,
)
from catalog.application.queries import (
    count_low_stock as catalog_count_low_stock,
)
from catalog.application.queries import (
    find_sku_by_sku_code as catalog_find_by_sku,
)
from catalog.application.queries import (
    get_department_by_code as catalog_get_dept_by_code,
)
from catalog.application.queries import (
    list_departments as catalog_list_departments,
)
from catalog.application.queries import (
    list_low_stock as catalog_list_low_stock,
)
from catalog.application.queries import (
    list_skus as catalog_list_skus,
)
from catalog.application.queries import (
    list_vendors as catalog_list_vendors,
)
from inventory.application.queries import (
    demand_normalized_velocity,
    seasonal_pattern,
    sku_demand_profile,
    withdrawal_velocity,
)
from operations.application.queries import list_withdrawals
from shared.infrastructure.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


def _sku_summary(p) -> SkuSummary:
    return SkuSummary(
        sku=p.sku,
        name=p.name,
        quantity=float(p.quantity),
        sell_uom=p.sell_uom or "each",
        min_stock=float(p.min_stock),
        department=p.category_name or "",
    )


async def _search_skus(query: str = "", limit: int = 20) -> str:
    """Search SKUs by name, SKU code, or barcode."""
    query = query.strip()
    limit = min(limit, 50)
    items = await catalog_list_skus(search=query, limit=limit)
    return SkuSearchResult(
        count=len(items),
        skus=[_sku_summary(p) for p in items],
    ).serialize()


async def _search_semantic(query: str = "", limit: int = 10) -> str:
    """Semantic/concept search for SKUs. Use when exact search fails or query is descriptive."""
    query = query.strip()
    limit = min(limit, 30)
    index = await get_index()
    if OPENAI_API_KEY and index._embeddings is not None:
        results = await index.search_semantic(query, limit=limit, api_key=OPENAI_API_KEY)
        method = "embedding"
    else:
        results = index.search_bm25(query, limit=limit)
        method = "bm25"
    return SemanticSearchResult(
        count=len(results),
        skus=[_sku_summary(p) for p in results],
        method=method,
    ).serialize()


async def _get_sku_details(sku: str = "") -> str:
    """Get full details for one SKU: price, cost, vendor, UOM, barcode, reorder point."""
    sku = sku.strip().upper()
    p = await catalog_find_by_sku(sku)
    if not p:
        return ErrorResult(error=f"SKU '{sku}' not found").serialize()
    return SkuDetail(
        sku=p.sku,
        name=p.name,
        description=p.description,
        price=float(p.price),
        cost=float(p.cost),
        quantity=float(p.quantity),
        min_stock=float(p.min_stock),
        department=p.category_name,
        barcode=p.barcode,
        base_unit=p.base_unit,
        sell_uom=p.sell_uom,
        pack_qty=float(p.pack_qty) if p.pack_qty else None,
        purchase_uom=p.purchase_uom,
        purchase_pack_qty=float(p.purchase_pack_qty) if p.purchase_pack_qty else None,
    ).serialize()


async def _get_inventory_stats() -> str:
    """Catalogue summary: total_skus, total_cost_value, low_stock_count, out_of_stock_count."""
    total_skus = await catalog_count_all()
    low_count = await catalog_count_low_stock()
    skus = await catalog_list_skus()
    total_value = round(sum(float(p.quantity) * float(p.cost) for p in skus), 2)
    out_of_stock = sum(1 for p in skus if p.quantity == 0)
    return InventoryStats(
        total_skus=total_skus,
        total_cost_value=total_value,
        low_stock_count=low_count,
        out_of_stock_count=out_of_stock,
    ).serialize()


async def _list_low_stock(limit: int = 20) -> str:
    """List SKUs at or below their reorder point."""
    limit = min(limit, 50)
    items = await catalog_list_low_stock(limit=limit)
    return SkuSearchResult(
        count=len(items),
        skus=[_sku_summary(p) for p in items],
    ).serialize()


async def _list_departments() -> str:
    """List all departments with SKU counts."""
    depts = await catalog_list_departments()
    return DepartmentListResult(
        departments=[
            DepartmentInfo(
                name=d.name,
                code=d.code,
                sku_count=d.sku_count,
                sku_format=f"{d.code}-FAMILYSLUG-NN",
            )
            for d in depts
        ],
    ).serialize()


async def _list_vendors() -> str:
    """List all vendors."""
    vendors = await catalog_list_vendors()
    return VendorListResult(
        vendors=[VendorSummary(id=v.id, name=v.name) for v in vendors],
    ).serialize()


async def _get_usage_velocity(sku: str = "", days: int = 30) -> str:
    """Usage velocity for a single SKU over the last N days."""
    sku = sku.strip().upper()
    days = min(days, 365)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    p = await catalog_find_by_sku(sku)
    if not p:
        return ErrorResult(error=f"SKU '{sku}' not found").serialize()
    vel = await withdrawal_velocity([p.id], since)
    total_used = float(vel.get(p.id, 0))
    avg_daily = round(total_used / days, 2)
    days_until_zero = round(float(p.quantity) / avg_daily, 1) if avg_daily > 0 else None
    return UsageVelocityResult(
        sku=sku,
        name=p.name,
        sell_uom=p.sell_uom or "each",
        current_quantity=float(p.quantity),
        period_days=days,
        total_withdrawn=total_used,
        avg_daily_use=avg_daily,
        days_until_stockout=days_until_zero,
        _note=None
        if days_until_zero is not None
        else "days_until_stockout is null because avg_daily_use=0 — no withdrawals recorded in this period, not a data error.",
    ).serialize()


async def _get_reorder_suggestions(limit: int = 20) -> str:
    """Low-stock SKUs with urgency scoring based on normalized velocity."""
    limit = min(limit, 50)
    low_stock = await catalog_list_low_stock(limit=100)
    if not low_stock:
        return ReorderSuggestionsResult(count=0, suggestions=[]).serialize()
    sku_ids = [p.id for p in low_stock]
    vel_map = await demand_normalized_velocity(sku_ids, 30)
    suggestions: list[ReorderSuggestion] = []
    for p in low_stock:
        vel = vel_map.get(p.id)
        avg_daily = vel["normalized_daily"] if vel else 0
        qty = float(p.quantity)
        days_until_zero = round(qty / avg_daily, 1) if avg_daily > 0 else None
        urgency = (
            "critical"
            if days_until_zero is not None and days_until_zero <= 3
            else "high"
            if days_until_zero is not None and days_until_zero <= 7
            else "medium"
            if days_until_zero is not None
            else "no_velocity_data"
        )
        suggestions.append(
            ReorderSuggestion(
                sku=p.sku,
                name=p.name,
                quantity=qty,
                sell_uom=p.sell_uom,
                min_stock=float(p.min_stock),
                avg_daily_use=round(float(avg_daily), 2),
                days_until_stockout=days_until_zero,
                urgency=urgency,
                outlier_days_excluded=vel["outlier_days"] if vel else 0,
            )
        )
    suggestions.sort(
        key=lambda x: (
            x.days_until_stockout is None,
            x.days_until_stockout if x.days_until_stockout is not None else 9999,
        )
    )
    return ReorderSuggestionsResult(
        count=len(suggestions),
        suggestions=suggestions[:limit],
    ).serialize()


async def _get_department_health() -> str:
    """Per-department healthy/low/out-of-stock SKU counts."""
    depts = await catalog_list_departments()
    all_skus = await catalog_list_skus()
    by_dept: dict[str, list] = defaultdict(list)
    for p in all_skus:
        if p.category_id:
            by_dept[p.category_id].append(p)
    rows: list[DepartmentHealth] = []
    for d in depts:
        dept_skus = by_dept.get(d.id, [])
        out_of_stock = sum(1 for p in dept_skus if p.quantity == 0)
        low = sum(1 for p in dept_skus if p.quantity > 0 and p.quantity <= p.min_stock)
        healthy = sum(1 for p in dept_skus if p.quantity > p.min_stock)
        rows.append(
            DepartmentHealth(
                name=d.name,
                code=d.code,
                sku_count=len(dept_skus),
                out_of_stock=out_of_stock,
                low_stock=low,
                healthy=healthy,
            )
        )
    rows.sort(key=lambda r: r.out_of_stock + r.low_stock, reverse=True)
    return DepartmentHealthResult(departments=rows).serialize()


async def _get_top_skus(days: int = 30, by: str = "revenue", limit: int = 10) -> str:
    """Top SKUs by volume or revenue over a period."""
    days = min(days, 365)
    if by not in ("volume", "revenue"):
        by = "revenue"
    limit = min(limit, 50)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    withdrawals = await list_withdrawals(start_date=since, limit=10000)
    sku_map: dict[str, dict] = {}
    for w in withdrawals:
        for item in w.items:
            sku = item.sku or item.name or "unknown"
            name = item.name or sku
            qty = float(item.quantity)
            revenue = float(item.subtotal)
            if sku not in sku_map:
                sku_map[sku] = {"sku": sku, "name": name, "total_units": 0.0, "total_revenue": 0.0}
            sku_map[sku]["total_units"] += qty
            sku_map[sku]["total_revenue"] += revenue
    sort_key = "total_revenue" if by == "revenue" else "total_units"
    ranked_dicts = sorted(sku_map.values(), key=lambda x: x[sort_key], reverse=True)[:limit]
    ranked = [
        SkuRanked(
            sku=r["sku"],
            name=r["name"],
            total_units=round(r["total_units"], 2),
            total_revenue=round(r["total_revenue"], 2),
        )
        for r in ranked_dicts
    ]
    return TopSkusResult(
        period_days=days,
        ranked_by=by,
        count=len(ranked),
        skus=ranked,
    ).serialize()


async def _get_department_activity(dept_code: str = "", days: int = 30) -> str:
    """Withdrawal activity summary for a department."""
    dept_code = dept_code.strip().upper()
    days = min(days, 365)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    dept = await catalog_get_dept_by_code(dept_code)
    if not dept:
        return ErrorResult(error=f"Department '{dept_code}' not found or has no SKUs").serialize()
    skus = await catalog_list_skus(category_id=dept.id)
    if not skus:
        return ErrorResult(error=f"Department '{dept_code}' not found or has no SKUs").serialize()
    sku_ids = [p.id for p in skus]
    vel = await withdrawal_velocity(sku_ids, since)
    total_withdrawn = sum(float(v) for v in vel.values())
    low_stock_count = sum(1 for p in skus if p.quantity <= p.min_stock)
    return DepartmentActivityResult(
        dept_code=dept_code,
        period_days=days,
        sku_count=len(skus),
        low_stock_count=low_stock_count,
        withdrawals={"units": total_withdrawn},
    ).serialize()


async def _forecast_stockout(limit: int = 15) -> str:
    """SKUs predicted to run out soonest based on normalized velocity."""
    limit = min(limit, 50)
    skus = await catalog_list_skus()
    in_stock = [s for s in skus if s.quantity > 0]
    in_stock.sort(key=lambda s: s.quantity)
    in_stock = in_stock[:200]
    if not in_stock:
        return StockoutForecastResult(count=0, forecast=[]).serialize()
    sku_ids = [p.id for p in in_stock]
    vel_map = await demand_normalized_velocity(sku_ids, 30)
    forecast: list[StockoutItem] = []
    for p in in_stock:
        vel = vel_map.get(p.id)
        if not vel:
            continue
        avg_daily = float(vel["normalized_daily"])
        if avg_daily <= 0:
            continue
        days_until_zero = round(float(p.quantity) / avg_daily, 1)
        forecast.append(
            StockoutItem(
                sku=p.sku,
                name=p.name,
                department=p.category_name,
                quantity=float(p.quantity),
                sell_uom=p.sell_uom,
                min_stock=float(p.min_stock),
                avg_daily_use=round(avg_daily, 2),
                days_until_stockout=days_until_zero,
                risk="critical"
                if days_until_zero <= 3
                else "high"
                if days_until_zero <= 7
                else "medium",
                outlier_days_excluded=vel["outlier_days"],
            )
        )
    forecast.sort(key=lambda x: x.days_until_stockout)
    return StockoutForecastResult(
        count=len(forecast),
        forecast=forecast[:limit],
    ).serialize()


async def _get_slow_movers(limit: int = 20, days: int = 30) -> str:
    """In-stock SKUs with lowest withdrawal volume."""
    limit = min(limit, 100)
    days = min(days, 365)
    since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    skus = await catalog_list_skus()
    in_stock = [s for s in skus if s.quantity > 0]
    if not in_stock:
        return SlowMoversResult(period_days=days, count=0, slow_movers=[]).serialize()
    sku_ids = [p.id for p in in_stock]
    velocity_map = await withdrawal_velocity(sku_ids, since)
    ranked = []
    for p in in_stock:
        withdrawn = float(velocity_map.get(p.id, 0))
        ranked.append((withdrawn, -float(p.quantity), p, withdrawn))
    ranked.sort(key=lambda t: (t[0], t[1]))
    movers = [
        SlowMover(
            sku=p.sku,
            name=p.name,
            quantity=float(p.quantity),
            sell_uom=p.sell_uom or "each",
            department=p.category_name,
            units_withdrawn_30d=withdrawn,
        )
        for _, _, p, withdrawn in ranked[:limit]
    ]
    return SlowMoversResult(period_days=days, count=len(movers), slow_movers=movers).serialize()


async def _search_vendors_semantic(query: str = "", limit: int = 10) -> str:
    """Semantic search over vendors."""
    query = query.strip()
    limit = min(limit, 30)
    index = await get_index()
    results = await index.search_entity(query, "vendor", limit=limit)
    items = [{"id": r.entity_id, "score": round(r.score, 3), **r.data} for r in results]
    return SemanticEntityResult(count=len(items), items=items, entity_type="vendor").serialize()


async def _search_pos_semantic(query: str = "", limit: int = 10) -> str:
    """Semantic search over purchase orders."""
    query = query.strip()
    limit = min(limit, 30)
    index = await get_index()
    results = await index.search_entity(query, "purchase_order", limit=limit)
    items = [{"id": r.entity_id, "score": round(r.score, 3), **r.data} for r in results]
    return SemanticEntityResult(
        count=len(items), items=items, entity_type="purchase_order"
    ).serialize()


async def _search_jobs_semantic(query: str = "", limit: int = 10) -> str:
    """Semantic search over jobs."""
    query = query.strip()
    limit = min(limit, 30)
    index = await get_index()
    results = await index.search_entity(query, "job", limit=limit)
    items = [{"job_id": r.entity_id, "score": round(r.score, 3), **r.data} for r in results]
    return SemanticEntityResult(count=len(items), items=items, entity_type="job").serialize()


async def _get_demand_profile(sku: str = "", days: int = 60) -> str:
    """Deep demand profile for one SKU — outlier flags, baseline vs. spikes, project buys."""
    sku_code = sku.strip().upper()
    days = min(days, 365)
    p = await catalog_find_by_sku(sku_code)
    if not p:
        return ErrorResult(error=f"SKU '{sku_code}' not found").serialize()
    profile = await sku_demand_profile(p.id, days)
    profile["sku"] = sku_code
    profile["name"] = p.name
    profile["sell_uom"] = p.sell_uom or "each"
    profile["current_quantity"] = float(p.quantity)
    return DemandProfileResult(profile=profile).serialize()


async def _get_seasonal_pattern(sku: str = "", months: int = 12) -> str:
    """Monthly withdrawal totals for seasonality analysis."""
    sku_code = sku.strip().upper()
    months = min(months, 24)
    p = await catalog_find_by_sku(sku_code)
    if not p:
        return ErrorResult(error=f"SKU '{sku_code}' not found").serialize()
    rows = await seasonal_pattern(p.id, months)
    return SeasonalPatternResult(
        sku=sku_code,
        name=p.name,
        sell_uom=p.sell_uom or "each",
        months_requested=months,
        months_with_data=len(rows),
        monthly=rows,
    ).serialize()


# ── Registry ──────────────────────────────────────────────────────────────────

_reg(
    "search_skus", "inventory", _search_skus, use_cases=["find SKU", "lookup SKU", "barcode search"]
)
_reg(
    "search_semantic",
    "inventory",
    _search_semantic,
    use_cases=["concept search", "find by description", "fuzzy SKU search"],
)
_reg(
    "get_sku_details",
    "inventory",
    _get_sku_details,
    use_cases=["SKU details", "single SKU", "SKU info"],
)
_reg(
    "get_inventory_stats",
    "inventory",
    _get_inventory_stats,
    use_cases=["inventory summary", "catalogue stats", "stock counts"],
)
_reg(
    "list_low_stock",
    "inventory",
    _list_low_stock,
    use_cases=["low stock", "reorder point", "needs reorder"],
)
_reg("list_departments", "inventory", _list_departments, use_cases=["departments", "categories"])
_reg("list_vendors", "inventory", _list_vendors, use_cases=["vendors", "suppliers"])
_reg(
    "get_usage_velocity",
    "inventory",
    _get_usage_velocity,
    use_cases=["usage rate", "velocity", "daily use"],
)
_reg(
    "get_reorder_suggestions",
    "inventory",
    _get_reorder_suggestions,
    use_cases=["reorder suggestions", "what to buy"],
)
_reg(
    "get_department_health",
    "inventory",
    _get_department_health,
    use_cases=["department health", "stock health by dept"],
)
_reg("get_slow_movers", "inventory", _get_slow_movers, use_cases=["slow movers", "dead stock"])
_reg(
    "get_top_skus",
    "inventory",
    _get_top_skus,
    use_cases=["top sellers", "best sellers", "highest revenue SKUs"],
)
_reg(
    "get_department_activity",
    "inventory",
    _get_department_activity,
    use_cases=["department activity", "dept withdrawals"],
)
_reg(
    "forecast_stockout",
    "inventory",
    _forecast_stockout,
    use_cases=["stockout forecast", "running out", "at risk"],
)
_reg(
    "search_vendors_semantic",
    "inventory",
    _search_vendors_semantic,
    use_cases=["find vendor", "vendor search"],
)
_reg(
    "search_pos_semantic",
    "inventory",
    _search_pos_semantic,
    use_cases=["find PO", "purchase order search"],
)
_reg(
    "search_jobs_semantic", "inventory", _search_jobs_semantic, use_cases=["find job", "job search"]
)
_reg(
    "get_demand_profile",
    "inventory",
    _get_demand_profile,
    use_cases=["demand profile", "usage pattern"],
)
_reg(
    "get_seasonal_pattern",
    "inventory",
    _get_seasonal_pattern,
    use_cases=["seasonality", "monthly pattern"],
)
