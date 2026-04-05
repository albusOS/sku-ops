"""Health overview workflow — fixed fetch plan + deterministic format.

Runs a bounded cross-domain fetch for broad "what needs attention" questions
and formats into a prioritized markdown health report.
"""

from __future__ import annotations

import json
import logging

from assistant.application.workflows.base import format_workflow_result, run_parallel_fetch
from assistant.application.workflows.types import FetchSpec, HealthOverviewResult

logger = logging.getLogger(__name__)


def _specs(days: int = 30) -> list[FetchSpec]:
    """Build fetch specs for the health overview workflow."""
    return [
        FetchSpec("get_inventory_stats", {}, "inventory_stats"),
        FetchSpec("forecast_stockout", {"limit": 15}, "stockout_forecast_raw"),
        FetchSpec("get_slow_movers", {"limit": 20, "days": days}, "slow_movers_raw"),
        FetchSpec("get_carrying_cost", {"holding_rate_pct": 25.0}, "carrying_cost"),
        FetchSpec("get_pl_summary", {"days": days}, "pl_summary"),
        FetchSpec("get_outstanding_balances", {"limit": 20}, "outstanding_balances_raw"),
        FetchSpec("get_ar_aging", {"days": 365}, "ar_aging"),
        FetchSpec("get_payment_status_breakdown", {"days": days}, "payment_status_breakdown"),
        FetchSpec("list_pending_material_requests", {"limit": 20}, "pending_material_requests_raw"),
    ]


def _format_markdown(data: dict) -> str:
    """Format workflow data into structured markdown for the calling agent."""
    parts: list[str] = ["## Health Overview"]

    # Urgent items first
    forecast = data.get("stockout_forecast", [])
    if forecast:
        lines = ["### Stockout Risk\n| SKU | Name | Days Left |", "| --- | --- | --- |"]
        lines.extend(
            f"| {item.get('sku', '')} | {item.get('name', '')} | {item.get('days_until_stockout', '?')} |"
            for item in forecast[:10]
        )
        parts.append("\n".join(lines))

    pending = data.get("pending_material_requests", [])
    if pending:
        parts.append(f"### Pending Requests\n{len(pending)} material requests awaiting review.")

    # Financial health
    pl = data.get("pl_summary", {})
    if pl:
        parts.append(
            f"### P&L\n"
            f"- Revenue: ${float(pl.get('revenue', 0)):,.2f}\n"
            f"- Gross profit: ${float(pl.get('gross_profit', 0)):,.2f}\n"
            f"- Margin: {pl.get('gross_margin_pct', 0)}%"
        )
    balances = data.get("outstanding_balances", [])
    if balances:
        total = sum(float(item.get("balance", 0) or 0) for item in balances)
        parts.append(f"### Outstanding Balances\nTotal: ${total:,.2f} across {len(balances)} accounts.")
    ar = data.get("ar_aging", {})
    if ar:
        parts.append("### AR Aging\n" + json.dumps(ar, indent=2))
    payments = data.get("payment_status_breakdown", {})
    if payments:
        parts.append("### Payment Status\n" + json.dumps(payments, indent=2))

    # Inventory health
    stats = data.get("inventory_stats", {})
    if stats:
        parts.append(
            f"### Inventory\n"
            f"- Total SKUs: {stats.get('total_skus', 0)}\n"
            f"- Low stock: {stats.get('low_stock_count', 0)}\n"
            f"- Out of stock: {stats.get('out_of_stock_count', 0)}"
        )
    carrying = data.get("carrying_cost", {})
    if carrying:
        parts.append("### Carrying Cost\n" + json.dumps(carrying, indent=2))
    slow = data.get("slow_movers", [])
    if slow:
        parts.append(f"### Slow Movers\n{len(slow)} items with minimal movement tying up inventory.")

    return "\n\n".join(parts)


async def run_health_overview(days: int = 30) -> HealthOverviewResult:
    """Run the health overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(days=days))
    stockout_raw = data.get("stockout_forecast_raw", {})
    slow_raw = data.get("slow_movers_raw", {})
    outstanding_raw = data.get("outstanding_balances_raw", {})
    pending_raw = data.get("pending_material_requests_raw", {})
    stockout_forecast = stockout_raw.get("forecast", []) if isinstance(stockout_raw, dict) else []
    slow_movers = slow_raw.get("slow_movers", []) if isinstance(slow_raw, dict) else []
    outstanding_balances = outstanding_raw.get("balances", []) if isinstance(outstanding_raw, dict) else []
    pending_material_requests = pending_raw.get("pending_requests", []) if isinstance(pending_raw, dict) else []
    data_for_format = {
        "inventory_stats": data.get("inventory_stats", {}),
        "stockout_forecast": stockout_forecast,
        "slow_movers": slow_movers,
        "carrying_cost": data.get("carrying_cost", {}),
        "pl_summary": data.get("pl_summary", {}),
        "outstanding_balances": outstanding_balances,
        "ar_aging": data.get("ar_aging", {}),
        "payment_status_breakdown": data.get("payment_status_breakdown", {}),
        "pending_material_requests": pending_material_requests,
    }
    markdown = format_workflow_result(data_for_format, _format_markdown)
    return HealthOverviewResult(
        inventory_stats=data_for_format["inventory_stats"],
        stockout_forecast=stockout_forecast,
        slow_movers=slow_movers,
        carrying_cost=data_for_format["carrying_cost"],
        pl_summary=data_for_format["pl_summary"],
        outstanding_balances=outstanding_balances,
        ar_aging=data_for_format["ar_aging"],
        payment_status_breakdown=data_for_format["payment_status_breakdown"],
        pending_material_requests=pending_material_requests,
        synthesized_markdown=markdown,
    )
