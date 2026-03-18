"""Health overview workflow — fixed fetch plan + LLM synthesis.

Runs a bounded cross-domain fetch for broad "what needs attention" questions,
then synthesizes a prioritized markdown health report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from assistant.application.workflows.base import run_parallel_fetch, run_synthesis
from assistant.application.workflows.types import FetchSpec, HealthOverviewResult

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT = (Path(__file__).resolve().parent.parent / "dag_synthesis_prompt.md").read_text(
    encoding="utf-8"
)


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


def _build_synthesis_prompt(data: dict) -> str:
    """Build a prompt for the synthesis LLM from raw tool data."""
    parts = []
    if data.get("inventory_stats"):
        parts.append("## Inventory Stats\n" + json.dumps(data["inventory_stats"], indent=2))
    if data.get("stockout_forecast"):
        parts.append(
            "## Stockout Forecast\n" + json.dumps(data["stockout_forecast"][:15], indent=2)
        )
    if data.get("slow_movers"):
        parts.append("## Slow Movers\n" + json.dumps(data["slow_movers"][:20], indent=2))
    if data.get("carrying_cost"):
        parts.append("## Carrying Cost\n" + json.dumps(data["carrying_cost"], indent=2))
    if data.get("pl_summary"):
        parts.append("## P&L Summary\n" + json.dumps(data["pl_summary"], indent=2))
    if data.get("outstanding_balances"):
        parts.append(
            "## Outstanding Balances\n" + json.dumps(data["outstanding_balances"][:20], indent=2)
        )
    if data.get("ar_aging"):
        parts.append("## AR Aging\n" + json.dumps(data["ar_aging"], indent=2))
    if data.get("payment_status_breakdown"):
        parts.append(
            "## Payment Status Breakdown\n" + json.dumps(data["payment_status_breakdown"], indent=2)
        )
    if data.get("pending_material_requests"):
        parts.append(
            "## Pending Material Requests\n"
            + json.dumps(data["pending_material_requests"][:20], indent=2)
        )
    parts.append(
        "## Report Goal\n"
        "Write a concise health overview. Rank issues by urgency and business impact. "
        "Cover what is at risk, what is tying up cash or inventory, and what needs action today. "
        "End with prioritized action items."
    )
    return "\n\n".join(parts) if parts else "No data available."


def _fallback_markdown(data: dict) -> str:
    """Fallback when LLM synthesis fails."""
    lines = ["## Health Overview", "", "### Priority Issues"]
    forecast = data.get("stockout_forecast", [])
    if forecast:
        top = forecast[0]
        lines.append(
            f"- **Stockout risk**: {top.get('sku', '')} {top.get('name', '')} "
            f"may run out in {top.get('days_until_stockout', 'unknown')} days."
        )
    balances = data.get("outstanding_balances", [])
    if balances:
        total = sum(float(item.get("balance", 0) or 0) for item in balances)
        lines.append(f"- **Outstanding balances**: ${total:,.2f} currently unpaid.")
    pending = data.get("pending_material_requests", [])
    if pending:
        lines.append(f"- **Pending material requests**: {len(pending)} awaiting review.")
    slow = data.get("slow_movers", [])
    if slow:
        lines.append(f"- **Slow movers**: {len(slow)} items appear to be tying up inventory.")
    return "\n".join(lines)


async def run_health_overview(days: int = 30) -> HealthOverviewResult:
    """Run the health overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(days=days))
    stockout_raw = data.get("stockout_forecast_raw", {})
    slow_raw = data.get("slow_movers_raw", {})
    outstanding_raw = data.get("outstanding_balances_raw", {})
    pending_raw = data.get("pending_material_requests_raw", {})
    stockout_forecast = stockout_raw.get("forecast", []) if isinstance(stockout_raw, dict) else []
    slow_movers = slow_raw.get("slow_movers", []) if isinstance(slow_raw, dict) else []
    outstanding_balances = (
        outstanding_raw.get("balances", []) if isinstance(outstanding_raw, dict) else []
    )
    pending_material_requests = (
        pending_raw.get("pending_requests", []) if isinstance(pending_raw, dict) else []
    )
    data_for_synthesis = {
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
    markdown = await run_synthesis(
        data_for_synthesis,
        _SYNTHESIS_PROMPT,
        _build_synthesis_prompt,
        _fallback_markdown,
    )
    return HealthOverviewResult(
        inventory_stats=data_for_synthesis["inventory_stats"],
        stockout_forecast=stockout_forecast,
        slow_movers=slow_movers,
        carrying_cost=data_for_synthesis["carrying_cost"],
        pl_summary=data_for_synthesis["pl_summary"],
        outstanding_balances=outstanding_balances,
        ar_aging=data_for_synthesis["ar_aging"],
        payment_status_breakdown=data_for_synthesis["payment_status_breakdown"],
        pending_material_requests=pending_material_requests,
        synthesized_markdown=markdown,
    )
