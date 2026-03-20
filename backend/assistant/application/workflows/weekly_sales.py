"""Weekly sales report workflow — parallel tool fetch + deterministic format.

Runs 4 finance tools in parallel and formats into a structured markdown
report.  The calling agent interprets and presents the data.
"""

from __future__ import annotations

import json
import logging

from assistant.application.workflows.base import format_workflow_result, run_parallel_fetch
from assistant.application.workflows.types import FetchSpec, WeeklySalesReportResult

logger = logging.getLogger(__name__)


def _specs(days: int) -> list[FetchSpec]:
    """Build fetch specs for the weekly sales workflow."""
    return [
        FetchSpec("get_revenue_summary", {"days": days}, "revenue_summary"),
        FetchSpec("get_pl_summary", {"days": days}, "pl_summary"),
        FetchSpec("get_top_skus", {"days": days, "limit": 10}, "top_skus_raw"),
        FetchSpec("get_outstanding_balances", {"limit": 20}, "outstanding_balances_raw"),
    ]


def _format_markdown(data: dict) -> str:
    """Format workflow data into structured markdown for the calling agent."""
    parts: list[str] = ["## Weekly Sales Report"]
    pl = data.get("pl_summary", {})
    if pl:
        parts.append(
            f"### P&L\n"
            f"- **Revenue**: ${float(pl.get('revenue', 0)):,.2f}\n"
            f"- **COGS**: ${float(pl.get('cost_of_goods', 0)):,.2f}\n"
            f"- **Gross profit**: ${float(pl.get('gross_profit', 0)):,.2f}\n"
            f"- **Margin**: {pl.get('gross_margin_pct', 0)}%"
        )
    rev = data.get("revenue_summary", {})
    if rev:
        parts.append("### Revenue Detail\n" + json.dumps(rev, indent=2))
    top_skus = data.get("top_skus", [])
    if top_skus:
        lines = ["### Top SKUs\n| SKU | Name | Revenue |", "| --- | --- | --- |"]
        for item in top_skus[:10]:
            lines.append(
                f"| {item.get('sku', '')} | {item.get('name', '')} "
                f"| ${float(item.get('total_revenue', 0) or 0):,.2f} |"
            )
        parts.append("\n".join(lines))
    balances = data.get("outstanding_balances", [])
    if balances:
        total = sum(float(b.get("balance", 0) or 0) for b in balances)
        parts.append(f"### Outstanding Balances\n**Total outstanding**: ${total:,.2f}")
    return "\n\n".join(parts)


async def run_weekly_sales_report(days: int = 30) -> WeeklySalesReportResult:
    """Run the weekly sales workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(days))

    top_raw = data.get("top_skus_raw", {})
    top_skus = top_raw.get("skus", []) if isinstance(top_raw, dict) else []
    bal_raw = data.get("outstanding_balances_raw", {})
    outstanding_balances = bal_raw.get("balances", []) if isinstance(bal_raw, dict) else []

    data_for_format = {
        "revenue_summary": data.get("revenue_summary", {}),
        "pl_summary": data.get("pl_summary", {}),
        "top_skus": top_skus,
        "outstanding_balances": outstanding_balances,
    }
    markdown = format_workflow_result(data_for_format, _format_markdown)

    return WeeklySalesReportResult(
        revenue_summary=data_for_format["revenue_summary"],
        pl_summary=data_for_format["pl_summary"],
        top_skus=top_skus,
        outstanding_balances=outstanding_balances,
        synthesized_markdown=markdown,
    )
