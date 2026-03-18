"""Trend analyst sub-agent — demand patterns, outlier detection, seasonality.

Agent construction is deferred to first use so that missing API keys
don't crash the import chain at startup. The module can be imported
safely regardless of environment configuration.
"""

import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.core.config import load_agent_config
from assistant.agents.core.contracts import SpecialistResult, UsageInfo
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.model_registry import calc_cost, get_model, get_model_name
from assistant.agents.core.tokens import budget_tool_result
from assistant.agents.finance.analytics_tools import (
    _get_department_profitability,
    _get_trend_series,
)
from assistant.agents.inventory.tools import (
    _get_demand_profile,
    _get_seasonal_pattern,
    _get_top_skus,
)
from assistant.agents.ops.tools import (
    _get_daily_withdrawal_activity,
)
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    global _agent
    if _agent is not None:
        return _agent
    cfg = load_agent_config("trend_analyst")
    _agent = Agent(
        get_model("agent:trend"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        },
    )

    @_agent.tool
    async def get_trend_series(
        ctx: RunContext[AgentDeps], days: int = 30, group_by: str = "day"
    ) -> str:
        """Revenue/cost/profit time series. group_by: 'day', 'week', or 'month'."""
        return budget_tool_result(await _get_trend_series(days=days, group_by=group_by))

    @_agent.tool
    async def get_daily_withdrawal_activity(
        ctx: RunContext[AgentDeps], days: int = 30, sku_id: str = ""
    ) -> str:
        """Daily withdrawal volume over the last N days."""
        return budget_tool_result(await _get_daily_withdrawal_activity(days=days, sku_id=sku_id))

    @_agent.tool
    async def get_demand_profile(ctx: RunContext[AgentDeps], sku: str = "", days: int = 60) -> str:
        """Deep demand profile for a SKU — outlier flags, baseline vs. spikes, project buys."""
        return budget_tool_result(await _get_demand_profile(sku=sku, days=days))

    @_agent.tool
    async def get_seasonal_pattern(
        ctx: RunContext[AgentDeps], sku: str = "", months: int = 12
    ) -> str:
        """Monthly withdrawal totals for seasonality analysis."""
        return budget_tool_result(await _get_seasonal_pattern(sku=sku, months=months))

    @_agent.tool
    async def get_top_skus(
        ctx: RunContext[AgentDeps], days: int = 30, by: str = "revenue", limit: int = 10
    ) -> str:
        """Top SKUs by volume or revenue."""
        return budget_tool_result(await _get_top_skus(days=days, by=by, limit=limit))

    @_agent.tool
    async def get_department_profitability(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Revenue, COGS, shrinkage, profit, and margin by department."""
        return budget_tool_result(await _get_department_profitability(days=days))

    return _agent


async def run(question: str, deps: AgentDeps, *, usage=None) -> SpecialistResult:
    """Run the trend analyst and return result with usage info."""
    agent = _get_agent()
    msg_history = build_message_history(deps.history)
    run_kwargs = {"message_history": msg_history, "deps": deps}
    if usage is not None:
        run_kwargs["usage"] = usage
    try:
        result = await agent.run(question, **run_kwargs)
    except Exception:
        logger.exception("trend_analyst failed")
        return SpecialistResult(
            response="I ran into an issue running trend analysis. Please try again.",
            usage=UsageInfo(),
        )
    response = result.output if isinstance(result.output, str) else str(result.output)
    model_name = get_model_name("agent:trend")
    usage = result.usage()
    return SpecialistResult(
        response=response,
        usage=UsageInfo(
            cost_usd=calc_cost(model_name, usage),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=model_name,
        ),
    )
