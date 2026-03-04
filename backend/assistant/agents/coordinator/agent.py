"""CoordinatorAgent: delegates to specialists for complex cross-domain queries.

Instead of duplicating tools from every specialist (like general.py does),
the coordinator has delegation tools that call specialist agents directly.
Only invoked for COMPLEX queries that need cross-domain coordination.
"""
import importlib
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

logger = logging.getLogger(__name__)

_config = load_agent_config("coordinator")

SYSTEM_PROMPT = """You are the **coordinator** for SKU-Ops, a hardware store management system.
Your job is to answer complex, cross-domain questions by delegating to specialist agents.

DELEGATION TOOLS:
- ask_inventory(question): ask the inventory specialist — products, stock, reorders, departments, vendors
- ask_ops(question): ask the operations specialist — withdrawals, contractors, jobs, material requests
- ask_finance(question): ask the finance specialist — revenue, invoices, payments, P&L, outstanding balances
- ask_insights(question): ask the insights specialist — trends, top products, forecasting, velocity

HOW TO COORDINATE:
1. Break the user's question into sub-questions, one per domain
2. Call the relevant delegation tools — call independent ones in parallel
3. Synthesize the results into a unified, coherent answer
4. Highlight cross-domain connections (e.g. "low stock items are also your top sellers")

EXAMPLES:
- "How's the business doing?" → ask_inventory("inventory health overview") + ask_finance("revenue and P&L summary this week") + ask_insights("stockout forecast")
- "What needs attention?" → ask_inventory("critical low stock and reorder priorities") + ask_ops("pending material requests") + ask_finance("outstanding balances")

FORMAT — respond in GitHub-flavored markdown:
- Use ## section headers for each domain area
- Use markdown tables for structured data
- Lead with a 1-2 sentence executive summary
- Highlight action items or risks with **bold**

RULES:
- Always delegate — never make up data
- Synthesize, don't just concatenate — find patterns and connections across domains
- If a delegation fails, note the gap and answer with what you have
- Be concise but comprehensive"""

_agent = Agent(
    get_model("agent:coordinator"),
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


async def _delegate(agent_id: str, question: str, deps: AgentDeps) -> str:
    """Call a specialist agent and return its response text."""
    module_path = f"assistant.agents.{agent_id}"
    try:
        agent_module = importlib.import_module(module_path)
        result = await agent_module.run(
            question, history=None, deps=deps, mode="fast", session_id="",
        )
        return result.get("response", "No response from specialist.")
    except Exception as e:
        logger.warning(f"Coordinator delegation to {agent_id} failed: {e}")
        return f"[{agent_id} agent unavailable: {e}]"


@_agent.tool
async def ask_inventory(ctx: RunContext[AgentDeps], question: str) -> str:
    """Delegate a question to the inventory specialist (products, stock, reorders, departments, vendors)."""
    return await _delegate("inventory", question, ctx.deps)


@_agent.tool
async def ask_ops(ctx: RunContext[AgentDeps], question: str) -> str:
    """Delegate a question to the operations specialist (withdrawals, contractors, jobs, material requests)."""
    return await _delegate("ops", question, ctx.deps)


@_agent.tool
async def ask_finance(ctx: RunContext[AgentDeps], question: str) -> str:
    """Delegate a question to the finance specialist (revenue, invoices, payments, P&L, balances)."""
    return await _delegate("finance", question, ctx.deps)


@_agent.tool
async def ask_insights(ctx: RunContext[AgentDeps], question: str) -> str:
    """Delegate a question to the insights specialist (trends, top products, forecasting, velocity)."""
    return await _delegate("insights", question, ctx.deps)


async def run(user_message: str, history: list[dict] | None, deps: AgentDeps, mode: str = "fast", session_id: str = "") -> dict:
    model_settings = build_model_settings(_config, mode)

    return await run_agent_with_reflection(
        _agent, user_message,
        msg_history=build_message_history(history), deps=deps,
        model_settings=model_settings,
        agent_name="CoordinatorAgent", agent_label="coordinator",
        session_id=session_id, mode=mode, history=history,
        config=_config,
    )
