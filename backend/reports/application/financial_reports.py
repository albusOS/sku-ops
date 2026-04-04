"""Financial reports: sales, trends, margins, P&L, AR aging, KPI summary.

All read from the financial_ledger via the finance database service.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.types import round_money

if TYPE_CHECKING:
    from finance.domain.ledger_analytics_rows import (
        ArAgingRow,
        ProductMarginRow,
        TrendPoint,
    )


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


def _db_catalog():
    return get_database_manager().catalog


@dataclass(frozen=True)
class SalesReport:
    gross_revenue: float
    returns_total: float
    net_revenue: float
    total_cogs: float
    gross_profit: float
    gross_margin_pct: float
    total_tax: float
    total_transactions: int
    return_count: int
    average_transaction: float
    by_payment_status: dict[str, float]
    top_products: list[dict]
    total_revenue: float


@dataclass(frozen=True)
class TrendsTotals:
    revenue: float
    cost: float
    profit: float


@dataclass(frozen=True)
class TrendsReport:
    series: list[TrendPoint]
    totals: TrendsTotals


@dataclass(frozen=True)
class ProductMarginsReport:
    products: list[ProductMarginRow]


@dataclass(frozen=True)
class JobPlReport:
    jobs: list[dict]
    total: int
    total_revenue: float
    total_cost: float
    total_profit: float
    total_margin_pct: float


@dataclass(frozen=True)
class PlSummary:
    revenue: float
    cogs: float
    gross_profit: float
    margin_pct: float
    tax_collected: float = 0.0
    shrinkage: float = 0.0


@dataclass(frozen=True)
class PlReport:
    group_by: str
    summary: PlSummary
    rows: list[dict]
    label_key: str
    total_rows: int | None = None


@dataclass(frozen=True)
class KpiReport:
    period_days: int
    total_revenue: float
    total_cogs: float
    gross_profit: float
    gross_margin_pct: float
    inventory_cost_value: float
    inventory_turnover: float
    dio: float
    sell_through_pct: float
    total_units_sold: int


async def sales_report(
    *,
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> SalesReport:
    dim_kw = {
        "job_id": job_id,
        "department": department,
        "billing_entity": billing_entity,
    }

    (
        accounts,
        top_products,
        counts,
        catalog,
        payment_status,
        ret_total,
    ) = await asyncio.gather(
        _db_finance().ledger_summary_by_account(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            **dim_kw,
        ),
        _db_finance().analytics_product_margins(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            limit=10,
            **dim_kw,
        ),
        _db_finance().analytics_reference_counts(get_org_id(), start_date=start_date, end_date=end_date),
        _db_catalog().list_skus(get_org_id()),
        _db_operations().payment_status_breakdown(org_id, start_date=start_date, end_date=end_date),
        _db_finance().analytics_returns_total(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            **dim_kw,
        ),
    )
    product_map = {p.id: p for p in catalog}
    enriched_products = []
    for m in top_products:
        p = product_map.get(m["sku_id"])
        enriched_products.append(
            {
                **m,
                "name": p.name if p else "Unknown",
                "sku": p.sku if p else "",
                "base_unit": p.base_unit if p else "each",
            }
        )

    net_revenue = accounts.get("revenue", 0.0)
    cogs = accounts.get("cogs", 0.0)
    tax = accounts.get("tax_collected", 0.0)
    gross_revenue = round_money(net_revenue + ret_total)
    gross_profit = round_money(net_revenue - cogs)
    tx_count = counts.get("withdrawal", 0)
    return_count = counts.get("return", 0)

    return SalesReport(
        gross_revenue=gross_revenue,
        returns_total=round_money(ret_total),
        net_revenue=round_money(net_revenue),
        total_cogs=round_money(cogs),
        gross_profit=gross_profit,
        # float for JSON-friendly percentage
        gross_margin_pct=round(float(gross_profit / net_revenue * 100), 1) if net_revenue > 0 else 0.0,
        total_tax=round_money(tax),
        total_transactions=tx_count,
        return_count=return_count,
        average_transaction=round_money(net_revenue / tx_count) if tx_count > 0 else 0.0,
        by_payment_status=payment_status,
        top_products=enriched_products,
        total_revenue=round_money(net_revenue),
    )


async def trends_report(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    group_by: str = "day",
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> TrendsReport:
    series = await _db_finance().analytics_trend_series(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        group_by=group_by,
        job_id=job_id,
        department=department,
        billing_entity=billing_entity,
    )
    return TrendsReport(
        series=series,
        totals=TrendsTotals(
            revenue=round_money(sum(r["revenue"] for r in series)),
            cost=round_money(sum(r["cost"] for r in series)),
            profit=round_money(sum(r["profit"] for r in series)),
        ),
    )


async def product_margins_report(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> ProductMarginsReport:
    margin_data, catalog = await asyncio.gather(
        _db_finance().analytics_product_margins(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            job_id=job_id,
            department=department,
            billing_entity=billing_entity,
        ),
        _db_catalog().list_skus(get_org_id()),
    )
    product_map = {p.id: p for p in catalog}
    enriched = []
    for m in margin_data:
        p = product_map.get(m["sku_id"])
        enriched.append(
            {
                **m,
                "name": p.name if p else "Unknown",
                "sku": p.sku if p else "",
                "base_unit": p.base_unit if p else "each",
            }
        )
    return ProductMarginsReport(products=enriched)


async def job_pl_report(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> JobPlReport:
    result = await _db_finance().ledger_summary_by_job(
        get_org_id(),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        search=search,
    )
    jobs = result["rows"]
    total_revenue = sum(j["revenue"] for j in jobs)
    total_cost = sum(j["cost"] for j in jobs)
    total_profit = total_revenue - total_cost

    return JobPlReport(
        jobs=jobs,
        total=result["total"],
        total_revenue=round_money(total_revenue),
        total_cost=round_money(total_cost),
        total_profit=round_money(total_profit),
        # float for JSON-friendly percentage
        total_margin_pct=round(
            float(total_profit / total_revenue * 100) if total_revenue > 0 else 0.0,
            1,
        ),
    )


async def pl_report(
    *,
    group_by: str = "overall",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> PlReport:
    date_kw = {"start_date": start_date, "end_date": end_date}
    dim_kw = {
        "job_id": job_id,
        "department": department,
        "billing_entity": billing_entity,
    }
    total_rows = None

    if group_by == "overall":
        accounts = await _db_finance().ledger_summary_by_account(get_org_id(), **date_kw, **dim_kw)
        revenue = accounts.get("revenue", 0.0)
        cogs = accounts.get("cogs", 0.0)
        tax = accounts.get("tax_collected", 0.0)
        shrinkage = accounts.get("shrinkage", 0.0)
        profit = round_money(revenue - cogs - shrinkage)
        return PlReport(
            group_by="overall",
            summary=PlSummary(
                revenue=round_money(revenue),
                cogs=round_money(cogs),
                tax_collected=round_money(tax),
                shrinkage=round_money(shrinkage),
                gross_profit=profit,
                # float for JSON-friendly percentage
                margin_pct=round(float(profit / revenue * 100), 1) if revenue > 0 else 0.0,
            ),
            rows=[],
            label_key="name",
        )

    all_revenue_override = None
    all_cost_override = None

    if group_by == "job":
        result = await _db_finance().ledger_summary_by_job(
            get_org_id(), **date_kw, limit=limit, offset=offset, search=search
        )
        rows = result["rows"]
        total_rows = result["total"]
        all_revenue_override = result["all_revenue"]
        all_cost_override = result["all_cost"]
        label_key = "job_id"
    elif group_by == "contractor":
        rows = await _db_finance().ledger_summary_by_contractor(get_org_id(), **date_kw)
        label_key = "contractor_id"
    elif group_by == "department":
        rows = await _db_finance().ledger_summary_by_department(get_org_id(), **date_kw)
        label_key = "department"
    elif group_by == "entity":
        rows = await _db_finance().ledger_summary_by_billing_entity(get_org_id(), **date_kw)
        label_key = "billing_entity"
    elif group_by == "product":
        margin_rows, catalog = await asyncio.gather(
            _db_finance().analytics_product_margins(get_org_id(), **date_kw, limit=limit),
            _db_catalog().list_skus(get_org_id()),
        )
        pmap = {p.id: p for p in catalog}
        rows = [
            {
                **m,
                "name": pmap[m["sku_id"]].name if m["sku_id"] in pmap else "Unknown",
                "base_unit": pmap[m["sku_id"]].base_unit if m["sku_id"] in pmap else "each",
            }
            for m in margin_rows
        ]
        label_key = "name"
    else:
        rows = []
        label_key = "name"

    total_revenue = (
        all_revenue_override if all_revenue_override is not None else sum(r.get("revenue", 0.0) for r in rows)
    )
    total_cost = all_cost_override if all_cost_override is not None else sum(r.get("cost", 0.0) for r in rows)
    total_profit = round_money(total_revenue - total_cost)

    return PlReport(
        group_by=group_by,
        summary=PlSummary(
            revenue=round_money(total_revenue),
            cogs=round_money(total_cost),
            gross_profit=total_profit,
            # float for JSON-friendly percentage
            margin_pct=round(float(total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0,
        ),
        rows=rows,
        label_key=label_key,
        total_rows=total_rows,
    )


async def ar_aging_report(
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[ArAgingRow]:
    return await _db_finance().analytics_ar_aging(get_org_id(), start_date=start_date, end_date=end_date)


async def kpi_report(
    *,
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    job_id: str | None = None,
    department: str | None = None,
    billing_entity: str | None = None,
) -> KpiReport:
    accounts, products_data, units_sold_map = await asyncio.gather(
        _db_finance().ledger_summary_by_account(
            get_org_id(),
            start_date=start_date,
            end_date=end_date,
            job_id=job_id,
            department=department,
            billing_entity=billing_entity,
        ),
        _db_catalog().list_skus(get_org_id()),
        _db_operations().units_sold_by_product(org_id, start_date=start_date, end_date=end_date),
    )

    total_revenue = accounts.get("revenue", 0.0)
    total_cogs = accounts.get("cogs", 0.0)
    inventory_cost_value = sum(p.cost * p.quantity for p in products_data)

    if start_date and end_date:
        try:
            d_start = datetime.fromisoformat(start_date)
            d_end = datetime.fromisoformat(end_date)
            period_days = max((d_end - d_start).days, 1)
        except ValueError:
            period_days = 365
    else:
        period_days = 365

    # float for JSON-friendly ratios and percentages
    inv_cost_f = float(inventory_cost_value)
    cogs_f = float(total_cogs)
    rev_f = float(total_revenue)
    inventory_turnover = cogs_f / inv_cost_f if inv_cost_f > 0 else 0.0
    dio = (inv_cost_f / cogs_f * period_days) if cogs_f > 0 else 0.0
    gross_margin_pct = ((rev_f - cogs_f) / rev_f * 100) if rev_f > 0 else 0.0

    total_units_sold = sum(units_sold_map.values())
    total_stock = sum(p.quantity for p in products_data)
    # float for JSON-friendly percentage
    units_f = float(total_units_sold)
    stock_f = float(total_stock)
    sell_through_pct = (units_f / (units_f + stock_f) * 100) if (units_f + stock_f) > 0 else 0.0

    return KpiReport(
        period_days=period_days,
        total_revenue=round_money(total_revenue),
        total_cogs=round_money(total_cogs),
        gross_profit=round_money(total_revenue - total_cogs),
        gross_margin_pct=round(gross_margin_pct, 1),
        inventory_cost_value=round_money(inventory_cost_value),
        inventory_turnover=round(inventory_turnover, 2),
        dio=round(dio, 1),
        sell_through_pct=round(sell_through_pct, 1),
        total_units_sold=int(total_units_sold),
    )
