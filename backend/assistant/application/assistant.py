"""Chat assistant entrypoint.

Routing is determined by the user's explicit mode selection in the frontend.
Specialist agents (procurement, trend, health, analyst) are invoked directly
when the user picks that mode; otherwise the unified agent handles the request.

Context assembly pipeline enriches each request with entity graph data,
semantic memory, and session state before agent dispatch.
"""

import asyncio
import logging

import assistant.agents.analyst.agent as _analyst_agent_mod
import assistant.agents.health_analyst.agent as _health_agent_mod
import assistant.agents.procurement_analyst.agent as _procurement_agent_mod
import assistant.agents.trend_analyst.agent as _trend_agent_mod
import assistant.agents.unified.agent as _unified_agent
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.tokens import compress_history_async
from assistant.agents.memory.extract import extract_and_save
from assistant.agents.memory.store import recall
from assistant.application.context_assembly import assemble_context
from assistant.application.session_state import SessionState
from shared.infrastructure.config import (
    ANTHROPIC_AVAILABLE,
    LLM_SETUP_URL,
    OPENROUTER_AVAILABLE,
)

logger = logging.getLogger(__name__)


async def _get_query_embedding(query: str):
    """Compute a single embedding vector for the user query.

    Returns None if embedding service is unavailable — callers fall back
    to computing their own or skipping semantic features.
    """
    if not query or not query.strip():
        return None
    try:
        from assistant.infrastructure.embedding_store import embed_query

        return await embed_query(query)
    except Exception as e:
        logger.debug("Query embedding failed (non-critical): %s", e)
        return None


LLM_NOT_CONFIGURED_MSG = (
    "Chat assistant requires an API key. Set OPENROUTER_API_KEY (preferred) or "
    f"ANTHROPIC_API_KEY in backend/.env.  Get a key at {LLM_SETUP_URL}"
)


async def chat(
    user_message: str,
    history: list[dict] | None,
    ctx: dict | None = None,
    agent_type: str = "auto",
    session_id: str = "",
    session_state: SessionState | None = None,
) -> dict:
    """Route message to specialist or unified agent based on explicit mode selection."""
    if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE:
        return {"response": LLM_NOT_CONFIGURED_MSG, "tool_calls": [], "history": [], "agent": None}

    ctx = ctx or {}
    user_id = ctx.get("user_id", "")
    deps = AgentDeps(
        user_id=user_id,
        user_name=ctx.get("user_name", ""),
    )

    query_embedding = await _get_query_embedding(user_message)

    # Run independent pre-processing concurrently
    compress_task = asyncio.create_task(compress_history_async(history))
    context_task = asyncio.create_task(
        assemble_context(
            query=user_message,
            user_id=user_id,
            session_state=session_state,
            query_embedding=query_embedding,
        )
    )

    history = await compress_task or history
    assembled = await context_task

    # Capture clean conversation turns before injecting the context system message.
    # Specialists receive this as message_history so follow-up questions work.
    deps.history = [h for h in (history or []) if h.get("role") != "system"]

    context_block = assembled.format_for_agent()
    if context_block:
        history = [{"role": "system", "content": context_block}] + (history or [])

    # Route is determined by the user's explicit mode selection from the frontend.
    specialist_agents = frozenset({"procurement", "trend", "health", "analyst"})
    route = agent_type if agent_type in specialist_agents else "unified"

    logger.info("Agent mode: %s for message='%s...'", route, (user_message or "")[:50])

    if route in specialist_agents:
        enriched = _enrich_specialist_message(user_message, context_block)
        agent_mod = {
            "procurement": _procurement_agent_mod,
            "trend": _trend_agent_mod,
            "health": _health_agent_mod,
            "analyst": _analyst_agent_mod,
        }[route]
        try:
            spec_result = await agent_mod.run(enriched, deps=deps)
        except Exception:
            logger.exception("Specialist agent %s failed", route)
            return {
                "response": "I ran into an issue. Please try again in a moment.",
                "tool_calls": [],
                "history": history or [],
                "agent": route,
                "routed_to": [route],
            }
        return _specialist_result(user_message, spec_result, route, history or [])

    result = await _unified_agent.run(
        user_message, history=history, deps=deps, session_id=session_id
    )
    result["routed_to"] = ["unified"]
    return result


def _enrich_specialist_message(user_message: str, context_block: str) -> str:
    """Prepend assembled context to the user message for specialist agents."""
    if not context_block:
        return user_message
    return f"<context>\n{context_block}\n</context>\n\n{user_message}"


def _specialist_result(
    user_message: str, spec_result, agent_label: str, history: list[dict]
) -> dict:
    """Format specialist run output to match unified agent result shape."""
    new_history = list(history)
    new_history.append({"role": "user", "content": user_message})
    new_history.append({"role": "assistant", "content": spec_result.response})
    return {
        "response": spec_result.response,
        "tool_calls": [],
        "history": new_history,
        "agent": agent_label,
        "routed_to": [agent_label],
        "usage": {
            "cost_usd": spec_result.usage.cost_usd,
            "input_tokens": spec_result.usage.input_tokens,
            "output_tokens": spec_result.usage.output_tokens,
            "model": spec_result.usage.model,
        },
    }


# ── Memory facade (keeps agent imports out of the API layer) ──────────────────


async def recall_memory(user_id: str, query: str | None = None) -> str:
    """Return formatted memory context for session injection.

    When *query* is provided, uses semantic recall (hybrid scoring).
    Returns empty string if no artifacts exist.
    """
    return await recall(user_id=user_id, query=query)


def schedule_memory_extraction(
    user_id: str,
    session_id: str,
    history: list[dict],
) -> None:
    """Fire-and-forget background task to extract memory artifacts from conversation."""
    asyncio.create_task(
        extract_and_save(
            user_id=user_id,
            session_id=session_id,
            history=history,
        )
    )
