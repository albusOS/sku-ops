"""OpsAgent: contractors, withdrawals, jobs, material requests."""
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.contracts import load_agent_config
from assistant.agents.deps import AgentDeps
from assistant.agents.model_registry import get_model
from assistant.agents.agent_utils import (
    build_model_settings,
    build_message_history,
    run_agent_with_reflection,
)
from assistant.agents.tokens import budget_tool_result
from .tools import (
    _get_contractor_history,
    _get_job_materials,
    _list_recent_withdrawals,
    _list_pending_material_requests,
)

logger = logging.getLogger(__name__)

_config = load_agent_config("ops")

SYSTEM_PROMPT = (
    "You are an operations specialist for SKU-Ops, a hardware store management system.\n"
    "\n"
    "TOOLS \u2014 use them when the user asks about field operations, contractors, or jobs:\n"
    "- get_contractor_history(name, limit): withdrawal history for a specific contractor\n"
    "- get_job_materials(job_id): all materials pulled for a specific job\n"
    "- list_recent_withdrawals(days, limit): recent material withdrawals across all jobs\n"
    "- list_pending_material_requests(limit): material requests awaiting approval\n"
    "\n"
    "WHEN TO USE EACH TOOL:\n"
    '- "what has [contractor] taken / history for [name]" \u2192 get_contractor_history\n'
    '- "what was pulled for job [ID] / job materials" \u2192 get_job_materials\n'
    '- "recent withdrawals / last week\'s activity / what\'s been pulled lately" \u2192 list_recent_withdrawals\n'
    '- "pending requests / awaiting approval / material requests" \u2192 list_pending_material_requests\n'
    "\n"
    "FORMAT \u2014 respond in GitHub-flavored markdown:\n"
    "- For withdrawal lists, use a markdown table with a separator row:\n"
    "\n"
    "| Date | Contractor | Job | Total | Status |\n"
    "|------|-----------|-----|-------|--------|\n"
    "| 2026-03-01 | John Smith | JOB-123 | $150.00 | unpaid |\n"
    "\n"
    "- Use **bold** for key names, unpaid totals, and anything needing attention\n"
    "- Use bullet lists for summaries; save tables for 3+ row datasets\n"
    '- Lead with the pattern ("**3 of 5 jobs unpaid, $420 outstanding**") before listing rows\n'
    "\n"
    "Never make up operational data \u2014 always use a tool.\n"
    "Amounts in dollars rounded to 2 decimal places.\n"
    "\n"
    "REASONING \u2014 think before acting:\n"
    "1. Identify what the question is really asking \u2014 contractor profile? single job? recent trends?\n"
    "2. If a question has multiple parts, call independent tools together in the same turn\n"
    "3. After results, assess completeness \u2014 if a contractor has many jobs, note the pattern, not just raw rows\n"
    '4. For vague names (e.g. "John"), use partial matching and clarify if multiple contractors match\n'
    "5. Summarise patterns in results (total spend, most active job, payment status spread) rather than\n"
    "   dumping raw rows \u2014 give the user insight, not just data"
)

_agent = Agent(
    get_model("agent:ops"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


@_agent.tool
async def get_contractor_history(ctx: RunContext[AgentDeps], name: str, limit: int = 20) -> str:
    """Withdrawal history for a contractor (by name). Shows jobs, materials pulled, amounts."""
    return budget_tool_result(await _get_contractor_history({"name": name, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_job_materials(ctx: RunContext[AgentDeps], job_id: str) -> str:
    """All materials pulled for a specific job ID. Shows each item, quantity, cost."""
    return budget_tool_result(await _get_job_materials({"job_id": job_id}, ctx.deps.org_id))


@_agent.tool
async def list_recent_withdrawals(ctx: RunContext[AgentDeps], days: int = 7, limit: int = 20) -> str:
    """Recent material withdrawals across all jobs. Filter by last N days."""
    return budget_tool_result(await _list_recent_withdrawals({"days": days, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def list_pending_material_requests(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Material requests from contractors that are awaiting approval."""
    return budget_tool_result(await _list_pending_material_requests({"limit": limit}, ctx.deps.org_id))


async def run(user_message: str, history: list[dict] | None, deps: AgentDeps, mode: str = "fast", session_id: str = "") -> dict:
    model_settings = build_model_settings(_config, mode)

    return await run_agent_with_reflection(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings,
        agent_name="OpsAgent", agent_label="ops",
        session_id=session_id, mode=mode, history=history,
        config=_config,
    )