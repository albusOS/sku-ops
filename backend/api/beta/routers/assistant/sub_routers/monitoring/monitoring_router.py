"""Agent monitoring API - internal endpoints for observability."""

from fastapi import APIRouter, Query

from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _db_assistant():
    return get_database_manager().assistant


router = APIRouter(prefix="/admin/agents", tags=["agent-monitoring"])


@router.get("/runs")
async def agent_runs(
    current_user: AdminDep,
    agent: str | None = Query(None),
    session_id: str | None = Query(None),
    minutes: int = Query(60, ge=1, le=10080),
    limit: int = Query(50, ge=1, le=200),
    validation_failed_only: bool = Query(False),
):
    """Recent agent runs with full details. Pass validation_failed_only=true to filter to runs that failed grounding checks."""
    return await _db_assistant().list_agent_runs(
        get_org_id(),
        agent_name=agent,
        session_id=session_id,
        minutes=minutes,
        limit=limit,
        validation_failed_only=validation_failed_only,
    )


@router.get("/stats")
async def agent_stats(
    _current_user: AdminDep,
    hours: int = Query(24, ge=1, le=720),
):
    """Aggregate stats: runs per agent, total tokens, total cost, avg duration, error rate."""
    return await _db_assistant().agent_run_stats(get_org_id(), hours=hours)


@router.get("/sessions/{session_id}")
async def session_trace(
    session_id: str,
    _current_user: AdminDep,
):
    """Full trace of a session: every agent run, tool calls, tokens, in order."""
    return await _db_assistant().agent_session_trace(get_org_id(), session_id)


@router.get("/costs")
async def cost_breakdown(
    _current_user: AdminDep,
    days: int = Query(7, ge=1, le=90),
    group_by: str = Query("agent", pattern="^(agent|model|org)$"),
):
    """Cost breakdown by agent, model, or org."""
    return await _db_assistant().agent_cost_breakdown(get_org_id(), days=days, group_by=group_by)


@router.get("/validation")
async def validation_summary(
    _current_user: AdminDep,
    hours: int = Query(24, ge=1, le=720),
):
    """Validation pass/fail rates per agent and most common failure types.

    failure_type_counts keys:
    - no_tools_called: data question answered without calling any tool
    - ungrounded_numbers: numbers in response not found in tool results
    - domain_mismatch: tools used don't match the question domain
    """
    return await _db_assistant().agent_validation_summary(get_org_id(), hours=hours)
