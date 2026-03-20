"""Workflow registry — run predefined workflows by ID.

Workflows are best-effort: synthesis uses LLM calls and is non-deterministic.
Retries may produce slightly different output. Do not rely on exact output
for critical-path dependencies.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from assistant.application.workflows.health_overview import run_health_overview
from assistant.application.workflows.inventory_overview import run_inventory_overview
from assistant.application.workflows.procurement_overview import run_procurement_overview
from assistant.application.workflows.trend_overview import run_trend_overview
from assistant.application.workflows.weekly_sales import run_weekly_sales_report

if TYPE_CHECKING:
    from assistant.application.workflows.types import WorkflowDeps, WorkflowRunner

logger = logging.getLogger(__name__)

_WORKFLOWS: dict[str, WorkflowRunner[Any]] = {}
WORKFLOW_TOOL_NAMES = frozenset(
    {
        "run_weekly_sales_report",
        "run_inventory_overview",
        "run_procurement_overview",
        "run_trend_overview",
        "run_health_overview",
    }
)


def register(workflow_id: str, runner: WorkflowRunner[Any]) -> None:
    """Register a workflow. Call at module import or startup."""
    _WORKFLOWS[workflow_id] = runner


def _ensure_registered() -> None:
    """Register workflows on first use (idempotent)."""
    if "weekly_sales_report" in _WORKFLOWS:
        return

    async def _weekly_sales(deps: WorkflowDeps) -> Any:
        return await run_weekly_sales_report(days=deps.days)

    async def _inventory_overview(deps: WorkflowDeps) -> Any:
        return await run_inventory_overview()

    async def _procurement_overview(deps: WorkflowDeps) -> Any:
        return await run_procurement_overview()

    async def _trend_overview(deps: WorkflowDeps) -> Any:
        return await run_trend_overview(days=deps.days)

    async def _health_overview(deps: WorkflowDeps) -> Any:
        return await run_health_overview(days=deps.days)

    register("weekly_sales_report", _weekly_sales)
    register("inventory_overview", _inventory_overview)
    register("procurement_overview", _procurement_overview)
    register("trend_overview", _trend_overview)
    register("health_overview", _health_overview)


async def run_workflow(
    workflow_id: str,
    deps: WorkflowDeps,
) -> Any:
    """Run a registered workflow and return its typed result."""
    _ensure_registered()
    runner = _WORKFLOWS.get(workflow_id)
    if runner is None:
        raise ValueError(f"Unknown workflow: {workflow_id}")

    trace_id = deps.trace_id or ""
    start = time.monotonic()
    logger.info(
        "workflow_start",
        extra={"workflow_id": workflow_id, "trace_id": trace_id},
    )
    try:
        result = await runner(deps)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "workflow_end",
            extra={
                "workflow_id": workflow_id,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
            },
        )
        return result
    except Exception:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "workflow_failed",
            extra={
                "workflow_id": workflow_id,
                "trace_id": trace_id,
                "duration_ms": duration_ms,
            },
        )
        raise


def response_agent_label(agent_label: str, tool_calls: list[dict] | None) -> str:
    """Map workflow-driven unified responses to the existing UI report label."""
    if agent_label == "unified" and any(
        (call or {}).get("tool") in WORKFLOW_TOOL_NAMES for call in (tool_calls or [])
    ):
        return "dag"
    return agent_label
