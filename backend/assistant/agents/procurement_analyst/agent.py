"""Procurement analyst sub-agent — vendor reliability, smart reorder, lead times.

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
from assistant.agents.inventory.tools import (
    _forecast_stockout,
)
from assistant.agents.purchasing.tools import (
    _get_procurement_snapshot,
    _get_purchase_history,
    _get_reorder_with_vendor_context,
    _get_sku_vendor_options,
    _get_smart_reorder_points,
    _get_vendor_catalog,
    _get_vendor_lead_times,
    _get_vendor_performance,
)
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    global _agent
    if _agent is not None:
        return _agent
    cfg = load_agent_config("procurement_analyst")
    _agent = Agent(
        get_model("agent:procurement"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        },
    )

    @_agent.tool
    async def get_procurement_snapshot(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Use first for broad buy-plan questions. Returns bundled reorder risk, stockout timing, smart min_stock gaps, and preferred vendor context."""
        return budget_tool_result(await _get_procurement_snapshot(limit=limit))

    @_agent.tool
    async def get_reorder_with_vendor_context(ctx: RunContext[AgentDeps], limit: int = 30) -> str:
        """Use when you need the raw low-stock list and vendor options per SKU for ordering decisions."""
        return budget_tool_result(await _get_reorder_with_vendor_context(limit=limit))

    @_agent.tool
    async def get_smart_reorder_points(ctx: RunContext[AgentDeps], limit: int = 30) -> str:
        """Use for reorder-policy questions. Returns velocity-based reorder points vs static min_stock and flags miscalibrations."""
        return budget_tool_result(await _get_smart_reorder_points(limit=limit))

    @_agent.tool
    async def get_vendor_lead_times(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = "", days: int = 180
    ) -> str:
        """Use for vendor delivery-risk questions. Returns actual lead times from PO history plus drift detection."""
        return budget_tool_result(
            await _get_vendor_lead_times(vendor_id=vendor_id, name=name, days=days)
        )

    @_agent.tool
    async def forecast_stockout(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Use for urgency questions. Returns SKUs predicted to run out soonest based on normalized demand velocity."""
        return budget_tool_result(await _forecast_stockout(limit=limit))

    @_agent.tool
    async def get_vendor_performance(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = "", days: int = 90
    ) -> str:
        """Use for vendor scorecard questions. Returns PO count, spend, average lead time, and fill rate."""
        return budget_tool_result(
            await _get_vendor_performance(vendor_id=vendor_id, name=name, days=days)
        )

    @_agent.tool
    async def get_vendor_catalog(
        ctx: RunContext[AgentDeps], vendor_id: str = "", name: str = ""
    ) -> str:
        """Use when the user asks what a vendor sells. Returns SKUs supplied by a vendor with cost, lead time, and MOQ."""
        return budget_tool_result(await _get_vendor_catalog(vendor_id=vendor_id, name=name))

    @_agent.tool
    async def get_sku_vendor_options(ctx: RunContext[AgentDeps], sku_id: str) -> str:
        """Use for SKU sourcing and alternatives. Returns all vendor options for one SKU with comparative pricing and lead times."""
        return budget_tool_result(await _get_sku_vendor_options(sku_id=sku_id))

    @_agent.tool
    async def get_purchase_history(
        ctx: RunContext[AgentDeps],
        vendor_id: str = "",
        name: str = "",
        days: int = 90,
        limit: int = 20,
    ) -> str:
        """Use only when you need supporting evidence. Returns recent POs for a vendor with item summaries."""
        return budget_tool_result(
            await _get_purchase_history(vendor_id=vendor_id, name=name, days=days, limit=limit)
        )

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
