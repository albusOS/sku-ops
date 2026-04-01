"""Unified orchestrator agent — lookup tools + sub-agent delegation.

Single entry point for all chat messages. The LLM handles lookups directly and
delegates analytical tasks to specialist sub-agents.

Agent construction is deferred to first use so that missing API keys
don't crash the import chain at startup.
"""

import asyncio
import logging

from pydantic_ai import Agent, RunContext

from assistant.agents.analyst import agent as _analyst_agent_mod
from assistant.agents.core.config import load_agent_config
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import build_message_history
from assistant.agents.core.model_registry import get_model
from assistant.agents.core.runner import run_specialist
from assistant.agents.core.tokens import budget_tool_result
from assistant.agents.core.tool_results import (
    ToolResult,
    blocks_from_inventory_stats,
    blocks_from_list_data,
    blocks_from_pl_summary,
)
from assistant.agents.finance.tools import (
    _get_invoice_summary,
    _get_pl_summary,
)
from assistant.agents.health_analyst import agent as _health_agent_mod
from assistant.agents.inventory.tools import (
    _get_inventory_stats,
    _get_sku_details,
    _list_departments,
    _list_low_stock,
    _list_vendors,
    _search_semantic,
    _search_skus,
)
from assistant.agents.ops.tools import (
    _get_contractor_history,
    _get_job_materials,
    _get_payment_status_breakdown,
    _list_pending_material_requests,
    _list_recent_withdrawals,
)
from assistant.agents.procurement_analyst import agent as _procurement_agent_mod
from assistant.agents.trend_analyst import agent as _trend_agent_mod
from assistant.application.workflows.registry import run_workflow
from assistant.application.workflows.types import WorkflowDeps
from shared.infrastructure.db import get_org_id
from shared.infrastructure.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")

_agent: Agent[AgentDeps, str] | None = None


def _get_agent() -> Agent[AgentDeps, str]:
    global _agent
    if _agent is not None:
        return _agent
    cfg = load_agent_config("unified")
    _agent = Agent(
        get_model("agent:unified"),
        deps_type=AgentDeps,
        system_prompt=SYSTEM_PROMPT,
        model_settings={
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_output_tokens,
        },
    )

    # ── Lookup tools ─────────────────────────────────────────────────────────────

    @_agent.tool
    async def search_skus(ctx: RunContext[AgentDeps], query: str, limit: int = 20) -> str:
        """Search SKUs by name, SKU code, or barcode."""
        return budget_tool_result(await _search_skus(query=query, limit=limit))

    @_agent.tool
    async def search_semantic(ctx: RunContext[AgentDeps], query: str, limit: int = 10) -> str:
        """Semantic/concept search for SKUs. Use when exact search fails or query is descriptive."""
        return budget_tool_result(await _search_semantic(query=query, limit=limit))

    @_agent.tool
    async def get_sku_details(ctx: RunContext[AgentDeps], sku: str) -> str:
        """Get full details for one SKU: price, cost, vendor, UOM, barcode, reorder point."""
        return budget_tool_result(await _get_sku_details(sku=sku))

    @_agent.tool
    async def get_inventory_stats(ctx: RunContext[AgentDeps]) -> str:
        """Catalogue summary: total_skus, total_cost_value, low_stock_count, out_of_stock_count."""
        raw = await _get_inventory_stats()
        result = ToolResult(
            text=budget_tool_result(raw),
            blocks=blocks_from_inventory_stats(raw),
        )
        if result.blocks:
            ctx.deps.blocks.extend(result.blocks)
        return result.text

    @_agent.tool
    async def list_low_stock(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """List SKUs at or below their reorder point."""
        raw = await _list_low_stock(limit=limit)
        result = ToolResult(
            text=budget_tool_result(raw),
            blocks=blocks_from_list_data(
                raw,
                "Low stock SKUs",
                ["sku", "name", "quantity", "sell_uom", "min_stock", "department"],
            ),
        )
        if result.blocks:
            ctx.deps.blocks.extend(result.blocks)
        return result.text

    @_agent.tool
    async def list_departments(ctx: RunContext[AgentDeps]) -> str:
        """List all departments with SKU counts."""
        return budget_tool_result(await _list_departments())

    @_agent.tool
    async def list_vendors(ctx: RunContext[AgentDeps]) -> str:
        """List all vendors."""
        return budget_tool_result(await _list_vendors())

    # ── Operations tools (quick answers) ─────────────────────────────────────────

    @_agent.tool
    async def list_recent_withdrawals(
        ctx: RunContext[AgentDeps], days: int = 7, limit: int = 20
    ) -> str:
        """Recent material withdrawals across all jobs."""
        return budget_tool_result(await _list_recent_withdrawals(days=days, limit=limit))

    @_agent.tool
    async def list_pending_material_requests(ctx: RunContext[AgentDeps], limit: int = 20) -> str:
        """Material requests from contractors awaiting approval."""
        return budget_tool_result(await _list_pending_material_requests(limit=limit))

    @_agent.tool
    async def get_contractor_history(ctx: RunContext[AgentDeps], name: str, limit: int = 20) -> str:
        """Withdrawal history for a contractor (by name)."""
        return budget_tool_result(await _get_contractor_history(name=name, limit=limit))

    @_agent.tool
    async def get_job_materials(ctx: RunContext[AgentDeps], job_id: str) -> str:
        """All materials pulled for a specific job ID."""
        return budget_tool_result(await _get_job_materials(job_id=job_id))

    # ── Quick finance lookups ────────────────────────────────────────────────────

    @_agent.tool
    async def get_payment_status_breakdown(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Withdrawal totals by payment status (paid/invoiced/unpaid)."""
        return budget_tool_result(await _get_payment_status_breakdown(days=days))

    @_agent.tool
    async def get_invoice_summary(ctx: RunContext[AgentDeps]) -> str:
        """Invoice counts and totals by status (draft/sent/paid)."""
        return budget_tool_result(await _get_invoice_summary())

    @_agent.tool
    async def get_pl_summary(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Quick P&L: revenue, COGS, gross profit and margin."""
        raw = await _get_pl_summary(days=days)
        result = ToolResult(
            text=budget_tool_result(raw),
            blocks=blocks_from_pl_summary(raw),
        )
        if result.blocks:
            ctx.deps.blocks.extend(result.blocks)
        return result.text

    # ── Workflow tools ───────────────────────────────────────────────────────────

    @_agent.tool
    async def run_weekly_sales_report(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Full sales/finance report: revenue, P&L, top SKUs, outstanding balances."""
        trace_id = ctx.deps.trace_id or None
        deps = WorkflowDeps(
            org_id=get_org_id(), user_id=ctx.deps.user_id, days=days, trace_id=trace_id
        )
        result = await run_workflow("weekly_sales_report", deps)
        return result.synthesized_markdown

    @_agent.tool
    async def run_inventory_overview(ctx: RunContext[AgentDeps]) -> str:
        """Full inventory overview: stats, department health, low stock, slow movers."""
        trace_id = ctx.deps.trace_id or None
        deps = WorkflowDeps(
            org_id=get_org_id(), user_id=ctx.deps.user_id, days=30, trace_id=trace_id
        )
        result = await run_workflow("inventory_overview", deps)
        return result.synthesized_markdown

    @_agent.tool
    async def run_procurement_overview(ctx: RunContext[AgentDeps]) -> str:
        """Full procurement overview: what to order now, urgency, vendor grouping, and PO pipeline."""
        trace_id = ctx.deps.trace_id or None
        deps = WorkflowDeps(
            org_id=get_org_id(), user_id=ctx.deps.user_id, days=30, trace_id=trace_id
        )
        result = await run_workflow("procurement_overview", deps)
        return result.synthesized_markdown

    @_agent.tool
    async def run_trend_overview(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Full trend overview: broad demand shifts, top SKUs, department movement, and activity patterns."""
        trace_id = ctx.deps.trace_id or None
        deps = WorkflowDeps(
            org_id=get_org_id(), user_id=ctx.deps.user_id, days=days, trace_id=trace_id
        )
        result = await run_workflow("trend_overview", deps)
        return result.synthesized_markdown

    @_agent.tool
    async def run_health_overview(ctx: RunContext[AgentDeps], days: int = 30) -> str:
        """Full health overview: urgent risks, cash/inventory drag, pending requests, and prioritized actions."""
        trace_id = ctx.deps.trace_id or None
        deps = WorkflowDeps(
            org_id=get_org_id(), user_id=ctx.deps.user_id, days=days, trace_id=trace_id
        )
        result = await run_workflow("health_overview", deps)
        return result.synthesized_markdown

    # ── Entity graph traversal ───────────────────────────────────────────────────

    @_agent.tool
    async def traverse_entity_graph(
        ctx: RunContext[AgentDeps],
        entity_type: str,
        entity_id: str,
    ) -> str:
        """Follow relationships from any entity (sku, vendor, job, invoice, po).
        Returns connected entities. entity_type: 'sku', 'vendor', 'job', 'invoice', 'po'."""
        from assistant.application.entity_graph import neighbors as _graph_neighbors

        result = await _graph_neighbors(entity_type, entity_id)
        if not result:
            return f"No graph data found for {entity_type}:{entity_id}"
        return result.format_for_agent()

    # ── Sub-agent delegation ─────────────────────────────────────────────────────

    delegation_timeout = 50  # seconds — must be under the outer stream timeout

    @_agent.tool
    async def analyze_procurement(ctx: RunContext[AgentDeps], question: str) -> str:
        """Delegate to procurement analyst for reorder optimization, vendor selection, lead times, and ordering decisions."""
        try:
            result = await asyncio.wait_for(
                _procurement_agent_mod.run(question, deps=ctx.deps, usage=ctx.usage),
                timeout=delegation_timeout,
            )
            return result.response
        except TimeoutError:
            return "Procurement analysis timed out. Try a more specific question."
        except Exception:
            logger.exception("analyze_procurement delegation failed")
            return "Procurement analysis hit an error. Please try again."

    @_agent.tool
    async def analyze_trends(ctx: RunContext[AgentDeps], question: str) -> str:
        """Delegate to trend analyst for demand patterns, anomaly detection, seasonality, and period comparison."""
        try:
            result = await asyncio.wait_for(
                _trend_agent_mod.run(question, deps=ctx.deps, usage=ctx.usage),
                timeout=delegation_timeout,
            )
            return result.response
        except TimeoutError:
            return "Trend analysis timed out. Try a more specific question."
        except Exception:
            logger.exception("analyze_trends delegation failed")
            return "Trend analysis hit an error. Please try again."

    @_agent.tool
    async def assess_business_health(ctx: RunContext[AgentDeps], question: str) -> str:
        """Delegate to health analyst for cross-domain triage: inventory risk, cash flow, carrying cost, vendor drift."""
        try:
            result = await asyncio.wait_for(
                _health_agent_mod.run(question, deps=ctx.deps, usage=ctx.usage),
                timeout=delegation_timeout,
            )
            return result.response
        except TimeoutError:
            return "Health analysis timed out. Try a more specific question."
        except Exception:
            logger.exception("assess_business_health delegation failed")
            return "Health analysis hit an error. Please try again."

    @_agent.tool
    async def run_ad_hoc_analysis(ctx: RunContext[AgentDeps], question: str) -> str:
        """Delegate to the SQL analyst for ad hoc data questions: custom queries, period comparisons, cross-table joins, anything the pre-built tools can't answer."""
        try:
            result = await asyncio.wait_for(
                _analyst_agent_mod.run(question, deps=ctx.deps, usage=ctx.usage),
                timeout=delegation_timeout,
            )
            return result.response
        except TimeoutError:
            return "Ad hoc analysis timed out. Try a more focused question."
        except Exception:
            logger.exception("run_ad_hoc_analysis delegation failed")
            return "Ad hoc analysis hit an error. Please try again."

    return _agent


# ── Entry point ───────────────────────────────────────────────────────────────


async def run(
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    session_id: str = "",
) -> dict:
    result = await run_specialist(
        _get_agent(),
        user_message,
        msg_history=build_message_history(history),
        deps=deps,
        agent_name="UnifiedAgent",
        agent_label="unified",
        session_id=session_id,
        history=history,
    )
    from assistant.application.workflows.registry import response_agent_label

    result["agent"] = response_agent_label(result.get("agent", "unified"), result.get("tool_calls"))
    return result
