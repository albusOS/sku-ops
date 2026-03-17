"""Procurement analyst sub-agent — multi-step reorder optimization and vendor selection.

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
from assistant.agents.inventory.tools import (
    _forecast_stockout,
    _get_reorder_suggestions,
)
from assistant.agents.purchasing.tools import (
    _get_purchase_history,
    _get_reorder_with_vendor_context,
    _get_sku_vendor_options,
    _get_vendor_catalog,
    _get_vendor_performance,
    _list_all_vendors,
)
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    """Lazily construct the pydantic-ai Agent on first use.

    This avoids the eager AnthropicProvider() call at import time
    which crashes when ANTHROPIC_API_KEY is not set.
    """
    global _agent
    if _agent is not None:
        return _agent
    _agent = Agent(
        get_model("agent:unified"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={"temperature": 0},
    )

    @_agent.tool
    async def get_reorder_with_vendor_context(ctx: RunContext[AgentDeps], limit: int = 30) -> str:
        """Low-stock SKUs with vendor options for procurement planning."""
        return budget_tool_result(await _get_reorder_with_vendor_context({"limit": limit}))

    @_agent.tool
    async def forecast_stockout(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Products predicted to run out soonest based on withdrawal velocity."""
        return budget_tool_result(await _forecast_stockout({"limit": limit}))

    @_agent.tool
    async def get_reorder_suggestions(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Priority reorder list ranked by urgency (days until stockout)."""
        return budget_tool_result(await _get_reorder_suggestions({"limit": limit}))

    @_agent.tool
    async def get_vendor_performance(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = "", days: int = 90
    ) -> str:
        """Vendor reliability: PO count, spend, avg lead time, fill rate."""
        return budget_tool_result(
            await _get_vendor_performance({"vendor_id": vendor_id, "name": name, "days": days})
        )

    @_agent.tool
    async def get_vendor_catalog(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = ""
    ) -> str:
        """SKUs supplied by a vendor with cost, lead time, MOQ."""
        return budget_tool_result(await _get_vendor_catalog({"vendor_id": vendor_id, "name": name}))

    @_agent.tool
    async def get_sku_vendor_options(ctx: RunContext[AgentDeps], sku_id: str) -> str:
        """All vendors for a SKU with comparative pricing and lead times."""
        return budget_tool_result(await _get_sku_vendor_options({"sku_id": sku_id}))

    @_agent.tool
    async def get_purchase_history(
        ctx: RunContext[AgentDeps],
        vendor_id: str = "",
        name: str = "",
        days: int = 90,
        limit: int = 20,
    ) -> str:
        """Recent POs for a vendor."""
        return budget_tool_result(
            await _get_purchase_history(
                {
                    "vendor_id": vendor_id,
                    "name": name,
                    "days": days,
                    "limit": limit,
                }
            )
        )

    @_agent.tool
    async def list_all_vendors(ctx: RunContext[AgentDeps]) -> str:
        """All vendors with ID and contact info."""
        return budget_tool_result(await _list_all_vendors())

    return _agent


async def run(question: str, deps: AgentDeps, *, usage=None) -> SpecialistResult:
    """Run the procurement analyst and return result with usage info."""
    agent = _get_agent()
    msg_history = build_message_history(deps.history)
    run_kwargs = {"message_history": msg_history, "deps": deps}
    if usage is not None:
        run_kwargs["usage"] = usage
    try:
        result = await agent.run(question, **run_kwargs)
    except Exception:
        logger.exception("procurement_analyst failed")
        return SpecialistResult(
            response="I ran into an issue running procurement analysis. Please try again.",
            usage=UsageInfo(),
        )
    response = result.output if isinstance(result.output, str) else str(result.output)
    model_name = get_model_name("agent:procurement")
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
