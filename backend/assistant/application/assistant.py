"""Chat assistant entrypoint. Routes to specialist agents via intelligent classification.

Routing modes:
- "auto" (default): Haiku classifier picks the best agent(s), supports multi-agent fan-out
- Explicit agent_type ("inventory", "ops", etc.): bypasses router, dispatches directly
"""
import asyncio
import importlib
import logging

from shared.infrastructure.config import ANTHROPIC_AVAILABLE, LLM_SETUP_URL
from assistant.agents.deps import AgentDeps

logger = logging.getLogger(__name__)

LLM_NOT_CONFIGURED_MSG = (
    "Chat assistant requires an Anthropic API key. Add ANTHROPIC_API_KEY to backend/.env. "
    f"Get a key at {LLM_SETUP_URL}"
)

_AGENT_MODULES = {
    "inventory": "assistant.agents.inventory",
    "ops":       "assistant.agents.ops",
    "finance":   "assistant.agents.finance",
    "insights":  "assistant.agents.insights",
    "general":   "assistant.agents.general",
    "dashboard": "assistant.agents.general",
}


async def chat(
    user_message: str,
    history: list[dict] | None,
    ctx: dict | None = None,
    mode: str = "fast",
    agent_type: str = "auto",
    session_id: str = "",
) -> dict:
    """
    Dispatch user message to the appropriate specialist agent(s).

    When agent_type="auto", the router classifies the message and may dispatch
    to multiple agents in parallel for cross-domain questions.
    """
    if not ANTHROPIC_AVAILABLE:
        return {"response": LLM_NOT_CONFIGURED_MSG, "tool_calls": [], "history": [], "agent": None}

    ctx = ctx or {}
    deps = AgentDeps(
        org_id=ctx.get("org_id", "default"),
        user_id=ctx.get("user_id", ""),
        user_name=ctx.get("user_name", ""),
    )

    if agent_type == "auto":
        return await _routed_dispatch(user_message, history, deps, mode, session_id)

    # Explicit agent_type — direct dispatch (backwards compatible)
    module_path = _AGENT_MODULES.get(agent_type, _AGENT_MODULES["general"])
    agent_module = importlib.import_module(module_path)
    return await agent_module.run(user_message, history=history, deps=deps, mode=mode, session_id=session_id)


async def _routed_dispatch(
    user_message: str,
    history: list[dict] | None,
    deps: AgentDeps,
    mode: str,
    session_id: str,
) -> dict:
    """Classify the message, dispatch to one or more agents, merge if needed."""
    from assistant.agents.router import classify, merge_responses

    agents = await classify(user_message, history)
    logger.info(f"Router classified → {agents}")

    if len(agents) == 1:
        module_path = _AGENT_MODULES.get(agents[0], _AGENT_MODULES["general"])
        agent_module = importlib.import_module(module_path)
        result = await agent_module.run(user_message, history=history, deps=deps, mode=mode, session_id=session_id)
        result["routed_to"] = agents
        return result

    # Multi-agent fan-out: run agents in parallel
    async def _run_one(agent_name: str) -> dict:
        module_path = _AGENT_MODULES.get(agent_name, _AGENT_MODULES["general"])
        agent_module = importlib.import_module(module_path)
        try:
            return await agent_module.run(user_message, history=history, deps=deps, mode=mode, session_id=session_id)
        except Exception as e:
            logger.error(f"Fan-out agent {agent_name} failed: {e}")
            return {
                "response": f"The {agent_name} agent encountered an issue.",
                "tool_calls": [], "history": history or [], "thinking": [],
                "agent": agent_name,
                "usage": {"cost_usd": 0, "input_tokens": 0, "output_tokens": 0},
            }

    results = await asyncio.gather(*[_run_one(a) for a in agents])
    return await merge_responses(user_message, list(results))
