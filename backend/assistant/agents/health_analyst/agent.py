"""Business health analyst sub-agent — cross-domain triage and risk scoring.

Agent construction is deferred to first use so that missing API keys
don't crash the import chain at startup. The module can be imported
safely regardless of environment configuration.
"""

import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.core.contracts import SpecialistResult, UsageInfo
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.model_registry import calc_cost, get_model, get_model_name
from assistant.agents.core.tokens import budget_tool_result
from assistant.agents.finance.analytics_tools import (
    _get_ar_aging,
    _get_carrying_cost,
    _get_department_profitability,
    _get_sku_margins,
)
from assistant.agents.finance.tools import (
    _get_outstanding_balances,
    _get_pl_summary,
)
from assistant.agents.inventory.tools import (
    _forecast_stockout,
    _get_department_health,
    _get_inventory_stats,
    _get_slow_movers,
    _list_low_stock,
)
from assistant.agents.ops.tools import (
    _get_payment_status_breakdown,
)
from assistant.agents.purchasing.tools import (
    _get_vendor_lead_times,
)
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    global _agent
    if _agent is not None:
        return _agent
    _agent = Agent(
        get_model("agent:health"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={"temperature": 0},
    )

    @_agent.tool
    async def get_inventory_stats(ctx: RunContext[AgentDeps]) -> str:
        """Catalogue summary: SKU count, cost value, low/out-of-stock counts."""
        return budget_tool_result(await _get_inventory_stats())

    @_agent.tool
    async def get_department_health(ctx: RunContext[AgentDeps]) -> str:
        """Per-department healthy/low/out-of-stock SKU counts."""
        return budget_tool_result(await _get_department_health())

    @_agent.tool
    async def list_low_stock(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """SKUs at or below reorder point."""
        return budget_tool_result(await _list_low_stock(limit=limit))

    @_agent.tool
    async def forecast_stockout(ctx: RunContext[AgentDeps], limit: int = 15) -> str:
        """SKUs predicted to run out soonest (normalized velocity, outliers excluded)."""
        return budget_tool_result(await _forecast_stockout(limit=limit))

    @_agent.tool
    async def get_slow_movers(ctx: RunContext[AgentDeps], limit: int = 20, days: int = 30) -> str:
        """Dead or slow-moving stock tying up inventory."""
        return budget_tool_result(await _get_slow_movers(limit=limit, days=days))

    @_agent.tool
    async def get_carrying_cost(ctx: RunContext[AgentDeps], holding_rate_pct: float = 25.0) -> str:
        """Estimated holding cost of current inventory, grouped by department."""
        return budget_tool_result(await _get_carrying_cost(holding_rate_pct=holding_rate_pct))

    @_agent.tool
    async def get_vendor_lead_times(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = "", days: int = 180
    ) -> str:
        """Actual vendor lead times from PO data, with drift detection."""
        return budget_tool_result(
            await _get_vendor_lead_times(vendor_id=vendor_id, name=name, days=days)
        )

    @_agent.tool
    async def get_pl_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Revenue, COGS, gross profit and margin."""
        return budget_tool_result(await _get_pl_summary(days=days))

    @_agent.tool
    async def get_outstanding_balances(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Unpaid balances by billing entity."""
        return budget_tool_result(await _get_outstanding_balances(limit=limit))

    @_agent.tool
    async def get_ar_aging(ctx: RunContext[AgentDeps], days: int = 365) -> str:
        """AR aging buckets by entity (current, 1-30, 31-60, 61-90, 90+)."""
        return budget_tool_result(await _get_ar_aging(days=days))

    @_agent.tool
    async def get_sku_margins(ctx: RunContext[AgentDeps], days: int = 30, limit: int = 20) -> str:
        """Per-SKU margins."""
        return budget_tool_result(await _get_sku_margins(days=days, limit=limit))

    @_agent.tool
    async def get_department_profitability(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Revenue, COGS, shrinkage, profit, margin by department."""
        return budget_tool_result(await _get_department_profitability(days=days))

    @_agent.tool
    async def get_payment_status_breakdown(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Totals by paid/invoiced/unpaid."""
        return budget_tool_result(await _get_payment_status_breakdown(days=days))

    return _agent


async def run(question: str, deps: AgentDeps, *, usage=None) -> SpecialistResult:
    """Run the health analyst and return result with usage info."""
    agent = _get_agent()
    msg_history = build_message_history(deps.history)
    run_kwargs = {"message_history": msg_history, "deps": deps}
    if usage is not None:
        run_kwargs["usage"] = usage
    try:
        result = await agent.run(question, **run_kwargs)
    except Exception:
        logger.exception("health_analyst failed")
        return SpecialistResult(
            response="I ran into an issue running health analysis. Please try again.",
            usage=UsageInfo(),
        )
    response = result.output if isinstance(result.output, str) else str(result.output)
    model_name = get_model_name("agent:health")
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
