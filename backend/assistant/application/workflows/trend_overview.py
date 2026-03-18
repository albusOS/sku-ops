"""Trend overview workflow — fixed fetch plan + LLM synthesis.

Runs a bounded trend-analysis fetch for broad demand and performance questions,
then synthesizes a concise markdown report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from assistant.application.workflows.base import run_parallel_fetch, run_synthesis
from assistant.application.workflows.types import FetchSpec, TrendOverviewResult

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT = (Path(__file__).resolve().parent.parent / "dag_synthesis_prompt.md").read_text(
    encoding="utf-8"
)


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


def _build_synthesis_prompt(data: dict) -> str:
    """Build a prompt for the synthesis LLM from raw tool data."""
    parts = []
    series = data.get("trend_series", {})
    if series:
        parts.append("## Trend Series\n" + json.dumps(series, indent=2))
    top_skus = data.get("top_skus", [])
    if top_skus:
        parts.append("## Top SKUs\n" + json.dumps(top_skus[:10], indent=2))
    depts = data.get("department_profitability", [])
    if depts:
        parts.append("## Department Profitability\n" + json.dumps(depts[:15], indent=2))
    activity = data.get("daily_withdrawal_activity", [])
    if activity:
        parts.append("## Withdrawal Activity\n" + json.dumps(activity[:30], indent=2))
    parts.append(
        "## Report Goal\n"
        "Write a concise trend overview. Lead with the strongest demand or performance shift, "
        "compare the current period to the recent baseline when the data supports it, "
        "call out anomalies or concentration risk, and explain what the trend means for "
        "ordering, stocking, or pricing."
    )
    return "\n\n".join(parts) if parts else "No data available."


def _fallback_markdown(data: dict) -> str:
    """Fallback when LLM synthesis fails."""
    lines = ["## Trend Overview"]
    top_skus = data.get("top_skus", [])
    if top_skus:
        lines.append("")
        lines.append("### Top SKUs")
        for item in top_skus[:5]:
            lines.append(
                f"- **{item.get('sku', '')} {item.get('name', '')}**: "
                f"${float(item.get('total_revenue', 0) or 0):,.2f} revenue"
            )
    depts = data.get("department_profitability", [])
    if depts:
        lines.append("")
        lines.append("### Department Performance")
        for item in depts[:5]:
            lines.append(
                f"- **{item.get('department', item.get('name', 'Unknown'))}**: "
                f"${float(item.get('profit', 0) or 0):,.2f} profit"
            )
    return "\n".join(lines)


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
    data_for_synthesis = {
        "trend_series": data.get("trend_series", {}),
        "top_skus": top_skus,
        "department_profitability": department_profitability,
        "daily_withdrawal_activity": daily_withdrawal_activity,
    }
    markdown = await run_synthesis(
        data_for_synthesis,
        _SYNTHESIS_PROMPT,
        _build_synthesis_prompt,
        _fallback_markdown,
    )
    return TrendOverviewResult(
        trend_series=data_for_synthesis["trend_series"],
        top_skus=top_skus,
        department_profitability=department_profitability,
        daily_withdrawal_activity=daily_withdrawal_activity,
        synthesized_markdown=markdown,
    )
