"""
GeneralAgent: cross-domain assistant for the dashboard.
Covers inventory, ops, finance, and insights with a curated tool set.
"""
import logging

from pydantic_ai import Agent, RunContext

from shared.infrastructure.config import (
    AGENT_THINKING_BUDGET,
    DEFAULT_DEEP_THINKING_BUDGET,
)
from assistant.agents.deps import AgentDeps
from assistant.agents.model_registry import get_model
from assistant.agents.agent_utils import (
    build_message_history,
    run_agent_with_reflection,
)
from assistant.agents.tokens import budget_tool_result

# Import tool implementations from specialist agents
from assistant.agents.inventory import (
    _search_products,
    _get_inventory_stats,
    _list_low_stock,
    _get_reorder_suggestions,
    _get_department_health,
)
from assistant.agents.ops import (
    _list_recent_withdrawals,
    _list_pending_material_requests,
)
from assistant.agents.finance import (
    _get_revenue_summary,
    _get_outstanding_balances,
    _get_pl_summary,
)
from assistant.agents.insights import (
    _get_top_products,
    _forecast_stockout,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the **dashboard assistant** for SKU-Ops, a hardware store management system.
You answer cross-domain questions from the main dashboard — inventory health, revenue, outstanding balances, pending requests, and stockout risk.
For deep specialist work (e.g. searching a specific product, drilling into a job, analysing a department), tell the user which page to navigate to (Inventory, Operations, Financials, Reports).

TOOLS:
Inventory:
- search_products(query, limit): find products by name, SKU, or barcode
- get_inventory_stats(): catalogue summary — SKU count, cost value, low/out-of-stock counts
- list_low_stock(limit): products at or below their reorder point
- get_reorder_suggestions(limit): priority reorder list by urgency
- get_department_health(): per-department stock health breakdown

Operations:
- list_recent_withdrawals(days, limit): recent material withdrawals across all jobs
- list_pending_material_requests(limit): material requests awaiting approval

Finance:
- get_revenue_summary(days): revenue, tax, and transaction count for a period
- get_outstanding_balances(limit): unpaid balances grouped by billing entity
- get_pl_summary(days): profit & loss — revenue vs cost, gross margin

Insights:
- get_top_products(days, by, limit): top products by volume or revenue
- forecast_stockout(limit): products predicted to run out soon

WHEN TO USE EACH TOOL — match the question to the domain:
- "find / search / do we have X" → search_products
- "low stock / needs reordering" → list_low_stock or get_reorder_suggestions
- "inventory health / overview" → get_inventory_stats + get_department_health
- "recent withdrawals / activity" → list_recent_withdrawals
- "pending requests" → list_pending_material_requests
- "revenue / sales / P&L / margin" → get_revenue_summary + get_pl_summary
- "who owes us / outstanding" → get_outstanding_balances
- "top products / best sellers" → get_top_products
- "stockout forecast / running out" → forecast_stockout

DASHBOARD OVERVIEW — when asked for a general overview or summary, call in parallel:
  get_inventory_stats() + get_revenue_summary(days=7) + get_outstanding_balances() + forecast_stockout()
  Then write a structured report: Inventory Health, Week Revenue, Outstanding, Stockout Risk.

FORMAT — respond in GitHub-flavored markdown:
- Use markdown tables for lists of 3+ rows
- Use **bold** for critical numbers and key names
- Lead with a headline for multi-section responses
- Be concise — 1-3 sentences for simple queries, structured sections for reports

RULES:
- Never make up data — always use a tool
- Call independent tools in the same turn (parallel tool use)
- After tool results, assess if you have enough to answer — call more tools if not"""

_agent = Agent(
    get_model("agent:general"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


@_agent.tool
async def search_products(ctx: RunContext[AgentDeps], query: str, limit: int = 20) -> str:
    """Search products by name, SKU, or barcode."""
    return budget_tool_result(await _search_products({"query": query, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_inventory_stats(ctx: RunContext[AgentDeps]) -> str:
    """Catalogue summary: SKU count, cost value, low/out-of-stock counts."""
    return budget_tool_result(await _get_inventory_stats(ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def list_low_stock(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Products at or below their reorder point."""
    return budget_tool_result(await _list_low_stock({"limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_reorder_suggestions(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Priority reorder list ranked by urgency (days until stockout)."""
    return budget_tool_result(await _get_reorder_suggestions({"limit": limit}, ctx.deps.org_id), max_tokens=600)


@_agent.tool
async def get_department_health(ctx: RunContext[AgentDeps]) -> str:
    """Per-department breakdown: healthy, low-stock, and out-of-stock product counts."""
    return budget_tool_result(await _get_department_health(ctx.deps.org_id))


@_agent.tool
async def list_recent_withdrawals(ctx: RunContext[AgentDeps], days: int = 7, limit: int = 20) -> str:
    """Recent material withdrawals across all jobs."""
    return budget_tool_result(await _list_recent_withdrawals({"days": days, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def list_pending_material_requests(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Material requests from contractors awaiting approval."""
    return budget_tool_result(await _list_pending_material_requests({"limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_revenue_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
    """Revenue summary: total revenue, tax, transaction count for last N days."""
    return budget_tool_result(await _get_revenue_summary({"days": days}, ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_outstanding_balances(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
    """Unpaid balances grouped by billing entity — who owes money."""
    return budget_tool_result(await _get_outstanding_balances({"limit": limit}, ctx.deps.org_id))


@_agent.tool
async def get_pl_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
    """Profit & loss: revenue, cost of goods, gross profit and margin."""
    return budget_tool_result(await _get_pl_summary({"days": days}, ctx.deps.org_id), max_tokens=300)


@_agent.tool
async def get_top_products(ctx: RunContext[AgentDeps], days: int = 30, by: str = "revenue", limit: int = 10) -> str:
    """Top products ranked by units or revenue over the last N days."""
    return budget_tool_result(await _get_top_products({"days": days, "by": by, "limit": limit}, ctx.deps.org_id))


@_agent.tool
async def forecast_stockout(ctx: RunContext[AgentDeps], limit: int = 15) -> str:
    """Products predicted to run out soonest based on withdrawal velocity."""
    return budget_tool_result(await _forecast_stockout({"limit": limit}, ctx.deps.org_id), max_tokens=600)


async def run(user_message: str, history: list[dict] | None, deps: AgentDeps, mode: str = "fast", session_id: str = "") -> dict:
    deep = mode == "deep"
    thinking_budget = (AGENT_THINKING_BUDGET or DEFAULT_DEEP_THINKING_BUDGET) if deep else 0
    model_settings: dict = {}
    if thinking_budget > 0:
        model_settings["anthropic_thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    return await run_agent_with_reflection(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings or None,
        agent_name="GeneralAgent", agent_label="general",
        session_id=session_id, mode=mode, history=history,
    )
