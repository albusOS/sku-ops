"""Procurement overview workflow — fixed fetch plan + deterministic format.

Runs a bounded procurement fetch for broad ordering questions and
formats into a structured markdown buy-plan report.
"""

from __future__ import annotations

import logging

from assistant.application.workflows.base import format_workflow_result, run_parallel_fetch
from assistant.application.workflows.types import FetchSpec, ProcurementOverviewResult

logger = logging.getLogger(__name__)


def _specs(limit: int = 20) -> list[FetchSpec]:
    """Build fetch specs for the procurement overview workflow."""
    return [
        FetchSpec("get_procurement_snapshot", {"limit": limit}, "procurement_snapshot_raw"),
        FetchSpec("get_po_summary", {}, "po_summary"),
    ]


def _format_markdown(data: dict) -> str:
    """Format workflow data into structured markdown for the calling agent."""
    lines: list[str] = ["## Procurement Overview"]
    snapshot = data.get("procurement_snapshot", [])
    if snapshot:
        lines.append("")
        lines.append("### Items to Order\n| SKU | Name | Qty | UOM | Vendor | Stockout |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in snapshot[:20]:
            vendor = item.get("preferred_vendor") or "unknown"
            days = item.get("days_until_stockout")
            urgency = f"{days}d" if days is not None else "?"
            lines.append(
                f"| {item.get('sku', '')} | {item.get('name', '')} "
                f"| {item.get('quantity', 0)} | {item.get('sell_uom') or ''} "
                f"| {vendor} | {urgency} |"
            )
    po_summary = data.get("po_summary", {})
    by_status = po_summary.get("by_status", {}) if isinstance(po_summary, dict) else {}
    if by_status:
        lines.append("")
        lines.append("### PO Pipeline")
        for status, summary in by_status.items():
            lines.append(
                f"- **{status}**: {summary.get('count', 0)} POs, "
                f"${float(summary.get('total', 0) or 0):,.2f}"
            )
    return "\n".join(lines)


async def run_procurement_overview(limit: int = 20) -> ProcurementOverviewResult:
    """Run the procurement overview workflow and return a typed result."""
    data = await run_parallel_fetch(_specs(limit=limit))
    snapshot_raw = data.get("procurement_snapshot_raw", {})
    procurement_snapshot = snapshot_raw.get("items", []) if isinstance(snapshot_raw, dict) else []
    data_for_format = {
        "procurement_snapshot": procurement_snapshot,
        "po_summary": data.get("po_summary", {}),
    }
    markdown = format_workflow_result(data_for_format, _format_markdown)
    return ProcurementOverviewResult(
        procurement_snapshot=procurement_snapshot,
        po_summary=data_for_format["po_summary"],
        synthesized_markdown=markdown,
    )
