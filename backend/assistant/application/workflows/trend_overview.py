"""Trend overview workflow — fixed fetch plan + deterministic format.

Runs a bounded trend-analysis fetch for broad demand and performance questions
and formats into structured markdown.
"""

from __future__ import annotations

import json
import logging

from assistant.application.workflows.base import format_workflow_result, run_parallel_fetch
from assistant.application.workflows.types import FetchSpec, TrendOverviewResult

logger = logging.getLogger(__name__)


def _specs(days: int = 30) -> list[FetchSpec]:
    """Build fetch specs for the trend overview workflow."""
    group_by = "week" if days > 60 else "day"
    return [
        FetchSpec("get_trend_series", {"days": days, "group_by": group_by}, "trend_series"),
        FetchSpec("get_top_skus", {"days": days, "by": "revenue", "limit": 10}, "top_skus_raw"),
        FetchSpec("get_department_profitability", {"days": days}, "department_profitability_raw"),
        FetchSpec(
            "get_daily_withdrawal_activity",
            {"days": days},
            "daily_withdrawal_activity_raw",
        ),
    ]


def _format_markdown(data: dict) -> str:
    """Format workflow data into structured markdown for the calling agent."""
    parts: list[str] = ["## Trend Overview"]
    series = data.get("trend_series", {})
    if series:
        parts.append("### Period Series\n" + json.dumps(series, indent=2))
    top_skus = data.get("top_skus", [])
    if top_skus:
        lines = ["### Top SKUs by Revenue\n| SKU | Name | Revenue |", "| --- | --- | --- |"]
        for item in top_skus[:10]:
            lines.append(
                f"| {item.get('sku', '')} | {item.get('name', '')} "
                f"| ${float(item.get('total_revenue', 0) or 0):,.2f} |"
            )
        parts.append("\n".join(lines))
    depts = data.get("department_profitability", [])
    if depts:
        lines = ["### Department Performance\n| Department | Profit |", "| --- | --- |"]
        for item in depts[:10]:
            name = item.get("department", item.get("name", "Unknown"))
            lines.append(f"| {name} | ${float(item.get('profit', 0) or 0):,.2f} |")
        parts.append("\n".join(lines))
    activity = data.get("daily_withdrawal_activity", [])
    if activity:
        parts.append(f"### Withdrawal Activity\n{len(activity)} days of activity data available.")
    return "\n\n".join(parts)


async def run_trend_overview(days: int = 30) -> TrendOverviewResult:
    """Run the trend overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(days=days))
    top_raw = data.get("top_skus_raw", {})
    dept_raw = data.get("department_profitability_raw", {})
    activity_raw = data.get("daily_withdrawal_activity_raw", {})
    top_skus = top_raw.get("skus", []) if isinstance(top_raw, dict) else []
    department_profitability = dept_raw.get("departments", []) if isinstance(dept_raw, dict) else []
    daily_withdrawal_activity = (
        activity_raw.get("activity", []) if isinstance(activity_raw, dict) else []
    )
    data_for_format = {
        "trend_series": data.get("trend_series", {}),
        "top_skus": top_skus,
        "department_profitability": department_profitability,
        "daily_withdrawal_activity": daily_withdrawal_activity,
    }
    markdown = format_workflow_result(data_for_format, _format_markdown)
    return TrendOverviewResult(
        trend_series=data_for_format["trend_series"],
        top_skus=top_skus,
        department_profitability=department_profitability,
        daily_withdrawal_activity=daily_withdrawal_activity,
        synthesized_markdown=markdown,
    )
