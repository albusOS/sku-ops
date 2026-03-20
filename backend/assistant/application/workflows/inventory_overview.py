"""Inventory overview workflow — parallel tool fetch + deterministic format.

Runs get_inventory_stats, get_department_health, list_low_stock, get_slow_movers
in parallel and formats into structured markdown.
"""

from __future__ import annotations

import logging

from assistant.application.workflows.base import format_workflow_result, run_parallel_fetch
from assistant.application.workflows.types import FetchSpec, InventoryOverviewResult

logger = logging.getLogger(__name__)


def _specs(limit: int = 20, days: int = 30) -> list[FetchSpec]:
    """Build fetch specs for the inventory overview workflow."""
    return [
        FetchSpec("get_inventory_stats", {}, "inventory_stats"),
        FetchSpec("get_department_health", {}, "department_health_raw"),
        FetchSpec("list_low_stock", {"limit": limit}, "low_stock_raw"),
        FetchSpec("get_slow_movers", {"limit": limit, "days": days}, "slow_movers_raw"),
    ]


def _format_markdown(data: dict) -> str:
    """Format workflow data into structured markdown for the calling agent."""
    parts: list[str] = ["## Inventory Overview"]
    stats = data.get("inventory_stats", {})
    if stats:
        parts.append(
            f"### Summary\n"
            f"- **Total SKUs**: {stats.get('total_skus', 0)}\n"
            f"- **Total value**: ${float(stats.get('total_cost_value', 0)):,.2f}\n"
            f"- **Low stock**: {stats.get('low_stock_count', 0)}\n"
            f"- **Out of stock**: {stats.get('out_of_stock_count', 0)}"
        )
    depts = data.get("department_health", [])
    if depts:
        lines = [
            "### Department Health\n| Department | SKUs | Low | Out |",
            "| --- | --- | --- | --- |",
        ]
        for d in depts[:15]:
            lines.append(
                f"| {d.get('name', '')} | {d.get('sku_count', 0)} "
                f"| {d.get('low_stock', 0)} | {d.get('out_of_stock', 0)} |"
            )
        parts.append("\n".join(lines))
    low = data.get("low_stock", [])
    if low:
        lines = [
            "### Low Stock\n| SKU | Name | Qty | Min | Dept |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in low[:20]:
            lines.append(
                f"| {item.get('sku', '')} | {item.get('name', '')} "
                f"| {item.get('quantity', 0)} {item.get('sell_uom', '')} "
                f"| {item.get('min_stock', 0)} | {item.get('department', '')} |"
            )
        parts.append("\n".join(lines))
    slow = data.get("slow_movers", [])
    if slow:
        parts.append(f"### Slow Movers\n{len(slow)} items with minimal movement.")
    return "\n\n".join(parts)


async def run_inventory_overview(
    limit: int = 20,
    days: int = 30,
) -> InventoryOverviewResult:
    """Run the inventory overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(limit=limit, days=days))
    department_health = (
        data.get("department_health_raw", {}).get("departments", [])
        if isinstance(data.get("department_health_raw"), dict)
        else []
    )
    low_stock = (
        data.get("low_stock_raw", {}).get("skus", [])
        if isinstance(data.get("low_stock_raw"), dict)
        else []
    )
    slow_movers = (
        data.get("slow_movers_raw", {}).get("slow_movers", [])
        if isinstance(data.get("slow_movers_raw"), dict)
        else []
    )
    data_for_format = {
        "inventory_stats": data.get("inventory_stats", {}),
        "department_health": department_health,
        "low_stock": low_stock,
        "slow_movers": slow_movers,
    }
    markdown = format_workflow_result(data_for_format, _format_markdown)
    return InventoryOverviewResult(
        inventory_stats=data_for_format["inventory_stats"],
        department_health=department_health,
        low_stock=low_stock,
        slow_movers=slow_movers,
        synthesized_markdown=markdown,
    )
