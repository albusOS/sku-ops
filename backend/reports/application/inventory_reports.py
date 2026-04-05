"""Inventory and product report queries.

Catalog/product-heavy reports that depend on product state
and withdrawal velocity rather than the financial ledger.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.types import round_money


def _db_catalog():
    return get_database_manager().catalog


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


def _db_inventory():
    return get_database_manager().inventory


class DepartmentInventory(TypedDict):
    count: int
    retail_value: float
    cost_value: float
    margin: float


@dataclass(frozen=True)
class InventoryReport:
    total_products: int
    total_retail_value: float
    total_cost_value: float
    unrealized_margin: float
    margin_pct: float
    potential_profit: float
    low_stock_count: int
    out_of_stock_count: int
    low_stock_items: list[dict]
    by_department: dict[str, DepartmentInventory]


@dataclass(frozen=True)
class ProductPerformanceReport:
    products: list[dict]
    total: int


@dataclass(frozen=True)
class ReorderUrgencyReport:
    products: list[dict]
    total: int


@dataclass(frozen=True)
class ProductActivityReport:
    series: list[dict]
    sku_id: str | None
    days: int


async def inventory_report() -> InventoryReport:
    products = await _db_catalog().list_skus(get_org_id())

    total_products = len(products)
    total_retail = round_money(sum(p.price * p.quantity for p in products))
    total_cost = round_money(sum(p.cost * p.quantity for p in products))
    unrealized_margin = round_money(total_retail - total_cost)
    # float for JSON-friendly percentage
    margin_pct = (
        round(float(unrealized_margin / total_retail * 100), 1) if total_retail > 0 else 0.0
    )
    low_stock = [p for p in products if p.quantity <= p.min_stock]
    out_of_stock = [p for p in products if p.quantity == 0]

    by_department: dict[str, DepartmentInventory] = {}
    for p in products:
        dept = p.category_name or "Unknown"
        if dept not in by_department:
            by_department[dept] = DepartmentInventory(
                count=0, retail_value=0.0, cost_value=0.0, margin=0.0
            )
        by_department[dept]["count"] += 1
        by_department[dept]["retail_value"] += p.price * p.quantity
        by_department[dept]["cost_value"] += p.cost * p.quantity

    for dept_data in by_department.values():
        dept_data["retail_value"] = round_money(dept_data["retail_value"])
        dept_data["cost_value"] = round_money(dept_data["cost_value"])
        dept_data["margin"] = round_money(dept_data["retail_value"] - dept_data["cost_value"])

    return InventoryReport(
        total_products=total_products,
        total_retail_value=total_retail,
        total_cost_value=total_cost,
        unrealized_margin=unrealized_margin,
        margin_pct=margin_pct,
        potential_profit=unrealized_margin,
        low_stock_count=len(low_stock),
        out_of_stock_count=len(out_of_stock),
        low_stock_items=[p.model_dump() for p in low_stock[:20]],
        by_department=by_department,
    )


async def product_performance_report(
    *,
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
) -> ProductPerformanceReport:
    margin_data, products_data, units_sold_map = await asyncio.gather(
        _db_finance().analytics_product_margins(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        ),
        _db_catalog().list_skus(get_org_id()),
        _db_operations().units_sold_by_product(org_id, start_date=start_date, end_date=end_date),
    )

    product_map = {p.id: p for p in products_data}

    result = []
    for m in margin_data:
        pid = m["sku_id"]
        p = product_map.get(pid)
        current_stock = float(p.quantity if p else 0)
        units_sold = float(units_sold_map.get(pid, 0))
        revenue = float(m["revenue"])
        cost = float(m["cost"])
        profit = float(m["profit"])
        margin_pct = float(m["margin_pct"])
        catalog_unit_cost = float(p.cost if p else 0)
        avg_cost = cost / units_sold if units_sold > 0 else 0.0
        sell_through = (
            (units_sold / (units_sold + current_stock) * 100)
            if (units_sold + current_stock) > 0
            else 0.0
        )
        result.append(
            {
                "sku_id": pid,
                "name": p.name if p else "Unknown",
                "sku": p.sku if p else "",
                "department": p.category_name if p else "",
                "base_unit": p.base_unit if p else "each",
                "current_stock": current_stock,
                "catalog_unit_cost": round_money(catalog_unit_cost),
                "units_sold": units_sold,
                "avg_cost_per_unit": round_money(avg_cost),
                "revenue": round_money(revenue),
                "cogs": round_money(cost),
                "gross_profit": round_money(profit),
                # float for JSON-friendly percentage
                "margin_pct": float(margin_pct),
                "sell_through_pct": round(float(sell_through), 1),
            }
        )

    return ProductPerformanceReport(products=result, total=len(result))


async def reorder_urgency_report(
    *,
    days: int = 30,
    limit: int = 50,
) -> ReorderUrgencyReport:
    since = datetime.now(UTC) - timedelta(days=min(days, 365))

    low_stock, _all_products = await asyncio.gather(
        _db_catalog().list_low_stock_skus(get_org_id(), limit=200),
        _db_catalog().list_skus(get_org_id()),
    )

    sku_ids = [p.id for p in low_stock]
    if not sku_ids:
        return ReorderUrgencyReport(products=[], total=0)

    velocity_map = await _db_inventory().withdrawal_velocity(get_org_id(), sku_ids, since)

    result = []
    for p in low_stock:
        total_used = velocity_map.get(p.id, 0)
        avg_daily = total_used / days
        qty = p.quantity
        days_until_zero = round(qty / avg_daily, 1) if avg_daily > 0 else None
        urgency = (
            "critical"
            if days_until_zero is not None and days_until_zero <= 3
            else "high"
            if days_until_zero is not None and days_until_zero <= 7
            else "medium"
            if days_until_zero is not None and days_until_zero <= 30
            else "low"
            if days_until_zero is not None
            else "no_data"
        )
        result.append(
            {
                "sku_id": p.id,
                "name": p.name,
                "sku": p.sku,
                "department": p.category_name,
                "base_unit": p.base_unit,
                "current_stock": qty,
                "min_stock": p.min_stock,
                "avg_daily_use": round(avg_daily, 2),
                "days_until_stockout": days_until_zero,
                "urgency": urgency,
            }
        )

    result.sort(
        key=lambda x: (
            x["days_until_stockout"] is None,
            x["days_until_stockout"] if x["days_until_stockout"] is not None else 9999,
        )
    )

    return ReorderUrgencyReport(products=result[:limit], total=len(result))


async def product_activity_report(
    *,
    sku_id: str | None = None,
    days: int = 365,
) -> ProductActivityReport:
    since = datetime.now(UTC) - timedelta(days=min(days, 730))
    rows = await _db_inventory().daily_withdrawal_activity(get_org_id(), since, sku_id=sku_id)
    return ProductActivityReport(series=rows, sku_id=sku_id, days=days)
