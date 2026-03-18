"""Procurement overview workflow — fixed fetch plan + LLM synthesis.

Runs a bounded procurement fetch for broad ordering questions, then
synthesizes a markdown buy-plan style report.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from assistant.application.workflows.base import run_parallel_fetch, run_synthesis
from assistant.application.workflows.types import FetchSpec, ProcurementOverviewResult

logger = logging.getLogger(__name__)

_SYNTHESIS_PROMPT = (Path(__file__).resolve().parent.parent / "dag_synthesis_prompt.md").read_text(
    encoding="utf-8"
)


def _specs(limit: int = 20) -> list[FetchSpec]:
    """Build fetch specs for the procurement overview workflow."""
    return [
        FetchSpec("get_procurement_snapshot", {"limit": limit}, "procurement_snapshot_raw"),
        FetchSpec("get_po_summary", {}, "po_summary"),
    ]


def _build_synthesis_prompt(data: dict) -> str:
    """Build a prompt for the synthesis LLM from raw tool data."""
    parts = []
    snapshot = data.get("procurement_snapshot", [])
    if snapshot:
        parts.append("## Procurement Snapshot\n" + json.dumps(snapshot[:20], indent=2))
    po_summary = data.get("po_summary", {})
    if po_summary:
        parts.append("## Purchase Order Summary\n" + json.dumps(po_summary, indent=2))
    instructions = (
        "## Report Goal\n"
        "Write a concise weekly procurement overview. Lead with what should be ordered now, "
        "group recommendations by vendor when sensible, call out stockout urgency and any "
        "min_stock miscalibration, and mention PO pipeline context if it changes urgency."
    )
    parts.append(instructions)
    return "\n\n".join(parts) if parts else "No data available."


def _fallback_markdown(data: dict) -> str:
    """Fallback when LLM synthesis fails."""
    lines = ["## Procurement Overview"]
    snapshot = data.get("procurement_snapshot", [])
    if snapshot:
        lines.append("")
        lines.append("### Order Now")
        for item in snapshot[:5]:
            vendor = item.get("preferred_vendor") or "unknown vendor"
            days = item.get("days_until_stockout")
            urgency = f"{days} days to stockout" if days is not None else "stockout timing unknown"
            lines.append(
                f"- **{item.get('sku', '')} {item.get('name', '')}**: "
                f"qty {item.get('quantity', 0)} {item.get('sell_uom') or ''}, "
                f"vendor {vendor}, {urgency}"
            )
    po_summary = data.get("po_summary", {})
    by_status = po_summary.get("by_status", {}) if isinstance(po_summary, dict) else {}
    if by_status:
        lines.append("")
        lines.append("### PO Pipeline")
        for status, summary in by_status.items():
            lines.append(
                f"- **{status}**: {summary.get('count', 0)} POs, ${float(summary.get('total', 0) or 0):,.2f}"
            )
    return "\n".join(lines)


async def run_procurement_overview(limit: int = 20) -> ProcurementOverviewResult:
    """Run the procurement overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(limit=limit))
    snapshot_raw = data.get("procurement_snapshot_raw", {})
    procurement_snapshot = snapshot_raw.get("items", []) if isinstance(snapshot_raw, dict) else []
    data_for_synthesis = {
        "procurement_snapshot": procurement_snapshot,
        "po_summary": data.get("po_summary", {}),
    }
    markdown = await run_synthesis(
        data_for_synthesis,
        _SYNTHESIS_PROMPT,
        _build_synthesis_prompt,
        _fallback_markdown,
    )
    return ProcurementOverviewResult(
        procurement_snapshot=procurement_snapshot,
        po_summary=data_for_synthesis["po_summary"],
        synthesized_markdown=markdown,
    )
