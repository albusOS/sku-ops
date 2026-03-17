"""WebSocket endpoint for streaming AI chat responses.

Clients send JSON messages over WebSocket, and receive streamed events
as the LLM generates text and calls tools. This replaces the blocking
POST /chat flow with real-time token streaming.

Protocol (client -> server):
    { "type": "chat", "message": "...", "session_id": "...", "agent_type": "auto" }
    { "type": "cancel" }      - abort the current generation
    { "type": "pong" }        - heartbeat response

Protocol (server -> client):
    { "type": "ping" }
    { "type": "chat.status",     "status": "thinking" }
    { "type": "chat.tool_start", "tool": "search_products" }
    { "type": "chat.delta",      "content": "partial text..." }
    { "type": "chat.done",       "response": "...", "agent": "...",
      "tool_calls": [...], "thinking": [...], "session_id": "...",
      "usage": {...} }
    { "type": "chat.error",      "detail": "..." }
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic_ai import AgentRunResultEvent
from pydantic_ai.messages import (
    FinalResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
)

from assistant.agents.analyst.agent import _get_agent as _get_analyst_agent
from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import (
    build_message_history,
    extract_text_history,
    extract_tool_calls,
    extract_tool_calls_detailed,
)
from assistant.agents.core.model_registry import calc_cost, get_model_name
from assistant.agents.core.tokens import compress_history_async
from assistant.agents.core.validators import classify_intent, validate_response
from assistant.agents.health_analyst.agent import _get_agent as _get_health_agent
from assistant.agents.procurement_analyst.agent import _get_agent as _get_procurement_agent
from assistant.agents.trend_analyst.agent import _get_agent as _get_trend_agent
from assistant.agents.unified.agent import _get_agent
from assistant.application import session_store
from assistant.application.assistant import schedule_memory_extraction
from assistant.application.context_assembly import assemble_context
from assistant.infrastructure.agent_run_repo import log_agent_run
from shared.api.auth_provider import resolve_claims
from shared.infrastructure.config import (
    ANTHROPIC_AVAILABLE,
    OPENROUTER_AVAILABLE,
    SESSION_COST_CAP,
    decode_token,
    is_deployed,
)
from shared.infrastructure.logging_config import org_id_var, user_id_var
from shared.infrastructure.metrics import (
    chat_message,
    chat_session_closed,
    chat_session_opened,
    llm_usage,
)

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 25
_ALLOWED_ROLES = frozenset({"admin"})


def _enrich_specialist_message(user_message: str, context_block: str) -> str:
    """Prepend assembled context to the user message for specialist agents."""
    if not context_block:
        return user_message
    return f"<context>\n{context_block}\n</context>\n\n{user_message}"


async def _get_query_embedding(query: str):
    """Compute a single embedding for reuse across context assembly, memory, and routing."""
    if not query or not query.strip():
        return None
    try:
        from assistant.infrastructure.embedding_store import embed_query

        return await embed_query(query)
    except Exception:
        return None


def _classify_chat_error(exc: Exception) -> tuple[str, str]:
    """Classify an exception into (error_type, user_facing_detail).

    Returns typed errors so the frontend can show actionable messages
    or auto-retry on transient failures.
    """
    s = str(exc).lower()
    t = type(exc).__name__.lower()

    if isinstance(exc, asyncio.TimeoutError) or "timeout" in t or "timeout" in s:
        return "timeout", "The AI took too long to respond. Please try again."

    if any(k in s for k in ("rate limit", "429", "too many requests", "ratelimit")):
        return "rate_limit", "AI rate limit reached. Please wait a moment and try again."

    if any(k in s for k in ("401", "403", "invalid api key", "authentication", "unauthorized")):
        return "auth_error", "AI service authentication failed. Please contact support."

    if any(k in s for k in ("overload", "503", "529", "service unavailable", "capacity")):
        return "overloaded", "The AI service is temporarily overloaded. Please try again shortly."

    if any(k in s for k in ("connection", "network", "refused", "unreachable")):
        return "network", "Could not reach the AI service. Please check your connection."

    return "error", "Something went wrong. Please try again."


router = APIRouter()


def _authenticate(token: str) -> dict | None:
    try:
        return decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def _send(ws: WebSocket, msg: dict) -> bool:
    """Send JSON to client. Returns False if connection is dead."""
    try:
        await ws.send_text(json.dumps(msg))
        return True
    except (RuntimeError, OSError):
        return False


@router.websocket("/ws/chat")
async def ws_chat_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    payload = _authenticate(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    try:
        claims = resolve_claims(payload)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid token: missing required claims")
        return
    if is_deployed and claims.organization_id is None:
        await websocket.close(code=4001, reason="Invalid token: missing organization_id claim")
        return
    org_id = claims.organization_id or ""
    user_id = claims.user_id
    user_name = claims.name
    role = claims.role

    org_id_var.set(org_id)
    user_id_var.set(user_id)

    if role not in _ALLOWED_ROLES:
        await websocket.close(code=4003, reason="Insufficient permissions")
        return

    await websocket.accept()
    chat_session_opened()
    logger.info("Chat WS connected: user=%s org=%s", user_id, org_id)

    cancel_event: asyncio.Event | None = None
    generation_task: asyncio.Task | None = None

    async def _heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if not await _send(ws, {"type": "ping"}):
                return

    async def _receiver():
        """Listen for client messages - chat requests and cancellations."""
        nonlocal cancel_event, generation_task
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue

                msg_type = msg.get("type")

                if msg_type == "pong":
                    continue

                if msg_type == "cancel":
                    logger.debug("Chat WS cancel from user=%s", user_id)
                    if cancel_event:
                        cancel_event.set()
                    if generation_task and not generation_task.done():
                        generation_task.cancel()
                    continue

                if msg_type == "chat":
                    if generation_task and not generation_task.done():
                        await _send(
                            ws,
                            {
                                "type": "chat.error",
                                "detail": "Already generating a response. Send 'cancel' first.",
                            },
                        )
                        continue

                    cancel_event = asyncio.Event()
                    generation_task = asyncio.create_task(
                        _handle_chat(
                            websocket,
                            msg,
                            user_id,
                            user_name,
                            cancel_event,
                        )
                    )

        except WebSocketDisconnect:
            logger.debug("Chat WS disconnected: user=%s", user_id)
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("Chat WS receiver error for user=%s: %s", user_id, e)
        finally:
            if generation_task and not generation_task.done():
                generation_task.cancel()
                try:
                    await generation_task
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.warning("Chat generation task raised on cancel", exc_info=True)

    ws = websocket
    tasks = [
        asyncio.create_task(_heartbeat()),
        asyncio.create_task(_receiver()),
    ]
    try:
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        # Await cancelled tasks so their finally-blocks run and no "task destroyed
        # while pending" warnings are emitted. Shield the gather so an external
        # CancelledError (e.g. from the test client or a server shutdown) doesn't
        # prevent cleanup from completing.
        if pending:
            await asyncio.shield(asyncio.gather(*pending, return_exceptions=True))
    except (RuntimeError, OSError, asyncio.CancelledError):
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await asyncio.shield(asyncio.gather(*tasks, return_exceptions=True))
    finally:
        chat_session_closed()
        logger.info("Chat WS closed: user=%s org=%s", user_id, org_id)


async def _handle_chat(
    ws: WebSocket,
    msg: dict,
    user_id: str,
    user_name: str,
    cancel_event: asyncio.Event,
) -> None:
    """Process a single chat message with streaming."""
    user_message = (msg.get("message") or "").strip()
    session_id = msg.get("session_id") or str(uuid.uuid4())

    if not user_message:
        await _send(ws, {"type": "chat.error", "detail": "Empty message"})
        return

    if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE:
        await _send(ws, {"type": "chat.error", "detail": "AI not configured."})
        return

    if SESSION_COST_CAP > 0 and await session_store.get_cost(session_id) >= SESSION_COST_CAP:
        await _send(
            ws,
            {
                "type": "chat.done",
                "response": f"This session has reached the ${SESSION_COST_CAP:.2f} AI spend limit. Start a new chat.",
                "tool_calls": [],
                "thinking": [],
                "agent": None,
                "session_id": session_id,
                "usage": {
                    "cost_usd": 0,
                    "capped": True,
                    "session_cost_usd": await session_store.get_cost(session_id),
                },
            },
        )
        return

    history = await session_store.get_or_create(session_id)

    # Compute a single embedding for the query — reused by context, memory, and routing
    query_embedding = await _get_query_embedding(user_message)

    is_first_turn = not history

    # Run independent pre-processing concurrently
    compress_task = asyncio.create_task(compress_history_async(history))
    context_task = asyncio.create_task(
        assemble_context(
            query=user_message,
            user_id=user_id,
            include_memory=is_first_turn,
            query_embedding=query_embedding,
        )
    )

    # Route is determined by the user's explicit mode selection from the frontend.
    # No embedding-based routing — the frontend sends the agent_type directly.
    requested_agent = (msg.get("agent_type") or "").strip().lower()
    specialist_agents = frozenset({"procurement", "trend", "health", "analyst"})
    route = requested_agent if requested_agent in specialist_agents else "unified"

    compressed = await compress_task
    # Treat an empty list from compression as a successful result (falsy check would
    # incorrectly fall back to the uncompressed history when compression returns []).
    history = compressed if compressed is not None else history

    assembled = await context_task

    context_block = assembled.format_for_agent()

    # Only store clean conversation turns (no system context messages) in history.
    # System context is delivered to every agent via message enrichment, not history.
    clean_history = [h for h in (history or []) if h.get("role") != "system"]
    deps = AgentDeps(user_id=user_id, user_name=user_name, history=clean_history)
    # All agents receive clean history — system context block is prepended to the
    # user message instead so it never appears as a ModelResponse in the message list.
    msg_history = build_message_history(clean_history)

    logger.info("Agent mode: %s for message='%s...'", route, (user_message or "")[:50])

    _specialist_agent_map = {
        "procurement": _get_procurement_agent,
        "trend": _get_trend_agent,
        "health": _get_health_agent,
        "analyst": _get_analyst_agent,
    }

    if route in specialist_agents:
        enriched = _enrich_specialist_message(user_message, context_block)
        await _stream_agent(
            ws=ws,
            agent=_specialist_agent_map[route](),
            user_message=enriched,
            original_message=user_message,
            msg_history=msg_history,
            deps=deps,
            cancel_event=cancel_event,
            agent_label=route,
            session_id=session_id,
            history=clean_history,
            user_id=user_id,
        )
        return

    await _send(ws, {"type": "chat.status", "status": "thinking"})

    # For the unified agent, prepend the context block to the user message so it
    # reaches the model without polluting the persistent history as a system turn.
    unified_message = _enrich_specialist_message(user_message, context_block)
    await _stream_agent(
        ws=ws,
        agent=_get_agent(),
        user_message=unified_message,
        original_message=user_message,
        msg_history=msg_history,
        deps=deps,
        cancel_event=cancel_event,
        agent_label="unified",
        session_id=session_id,
        history=clean_history,
        user_id=user_id,
    )


_STREAM_TIMEOUT_SECONDS = 90  # hard ceiling on LLM stream; prevents hung-provider WebSocket leaks


async def _stream_agent(
    *,
    ws: WebSocket,
    agent,
    user_message: str,
    original_message: str,
    msg_history,
    deps: AgentDeps,
    cancel_event: asyncio.Event,
    agent_label: str,
    session_id: str,
    history: list[dict] | None,
    user_id: str,
) -> None:
    """Stream any PydanticAI agent to the WebSocket client.

    Shared by both the unified agent and all specialist agents so every mode
    gets live token deltas, tool_start events, and cancel support.
    """
    await _send(ws, {"type": "chat.status", "status": "thinking"})

    full_text = ""
    tool_calls_seen: list[dict] = []

    logger.info(
        "Chat stream started: user=%s session=%s agent=%s", user_id, session_id, agent_label
    )

    try:
        async with asyncio.timeout(_STREAM_TIMEOUT_SECONDS):
            async for event in agent.run_stream_events(
                user_message,
                message_history=msg_history,
                deps=deps,
            ):
                if cancel_event.is_set():
                    logger.info("Chat stream cancelled: user=%s session=%s", user_id, session_id)
                    break

                if isinstance(event, PartStartEvent):
                    if isinstance(event.part, ToolCallPart):
                        tool_name = event.part.tool_name
                        tool_calls_seen.append({"tool": tool_name})
                        await _send(ws, {"type": "chat.tool_start", "tool": tool_name})
                    elif isinstance(event.part, TextPart):
                        if event.part.content:
                            full_text += event.part.content
                            await _send(ws, {"type": "chat.delta", "content": event.part.content})

                elif isinstance(event, PartDeltaEvent):
                    if isinstance(event.delta, TextPartDelta):
                        chunk = event.delta.content_delta
                        if chunk:
                            full_text += chunk
                            await _send(ws, {"type": "chat.delta", "content": chunk})

                elif isinstance(event, FinalResultEvent):
                    pass

                elif isinstance(event, AgentRunResultEvent):
                    result = event.result
                    response_text = (
                        result.output if isinstance(result.output, str) else str(result.output)
                    )

                    if not full_text:
                        full_text = response_text

                    model_name = get_model_name(f"agent:{agent_label}")
                    usage = result.usage()
                    cost = calc_cost(model_name, usage)

                    all_msgs = result.all_messages()
                    tool_calls_final = extract_tool_calls(all_msgs)
                    tool_calls_det = extract_tool_calls_detailed(all_msgs)
                    text_history = extract_text_history(all_msgs)

                    intent = await classify_intent(original_message)
                    validation = validate_response(
                        original_message,
                        response_text,
                        tool_calls_final,
                        tool_calls_det,
                        intent=intent,
                    )

                    turn_cost = cost
                    # Use PydanticAI-extracted history (clean user/assistant pairs only).
                    # Fall back to manually appending to clean_history — never to the
                    # raw history which may contain system context entries.
                    if text_history:
                        new_history = text_history
                    else:
                        new_history = list(history or [])
                        new_history.append({"role": "user", "content": original_message})
                        new_history.append({"role": "assistant", "content": full_text})

                    await session_store.update(session_id, new_history, cost_usd=turn_cost)

                    if len(new_history) % 8 == 0:
                        schedule_memory_extraction(
                            user_id=user_id,
                            session_id=session_id,
                            history=new_history,
                        )

                    chat_message(agent_label, "success")
                    llm_usage(
                        model=model_name,
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        cost_usd=cost,
                        agent=agent_label,
                    )

                    if not validation.passed:
                        logger.warning(
                            "Validation failures: session=%s agent=%s failures=%s scores=%s",
                            session_id,
                            agent_label,
                            validation.failures,
                            validation.scores,
                        )

                    logger.info(
                        "Chat stream done: user=%s session=%s agent=%s cost=%.4f tokens=%d+%d",
                        user_id,
                        session_id,
                        agent_label,
                        cost,
                        usage.input_tokens,
                        usage.output_tokens,
                    )

                    _snap_model = model_name
                    _snap_text = full_text
                    _snap_det = tool_calls_det
                    _snap_usage = usage
                    _snap_cost = cost
                    _snap_val = validation

                    async def _log_run(
                        _m=_snap_model,
                        _t=_snap_text,
                        _d=_snap_det,
                        _u=_snap_usage,
                        _c=_snap_cost,
                        _v=_snap_val,
                    ):
                        try:
                            await log_agent_run(
                                session_id=session_id,
                                user_id=user_id,
                                agent_name=agent_label,
                                model=_m,
                                mode="stream",
                                user_message=original_message,
                                response_text=_t,
                                tool_calls=_d,
                                input_tokens=_u.input_tokens,
                                output_tokens=_u.output_tokens,
                                cost_usd=_c,
                                duration_ms=0,
                                validation_passed=_v.passed,
                                validation_failures=_v.failures,
                                validation_scores=_v.scores,
                            )
                        except Exception as _e:
                            logger.warning("Failed to log streamed agent run: %s", _e)

                    asyncio.create_task(_log_run())  # noqa: RUF006

                    await _send(
                        ws,
                        {
                            "type": "chat.done",
                            "response": full_text,
                            "agent": agent_label,
                            "tool_calls": tool_calls_final,
                            "thinking": [],
                            "blocks": deps.blocks or [],
                            "session_id": session_id,
                            "usage": {
                                "cost_usd": cost,
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                                "model": model_name,
                                "session_cost_usd": await session_store.get_cost(session_id),
                            },
                            "validation": {
                                "passed": validation.passed,
                                "failures": validation.failures,
                                "scores": validation.scores,
                            },
                        },
                    )
                    return

        if cancel_event.is_set():
            response = full_text or "Generation cancelled."
            await _save_turn(session_id, history, original_message, response)
            await _send(
                ws,
                {
                    "type": "chat.done",
                    "response": response,
                    "agent": agent_label,
                    "tool_calls": tool_calls_seen,
                    "thinking": [],
                    "session_id": session_id,
                    "usage": {
                        "cost_usd": 0,
                        "session_cost_usd": await session_store.get_cost(session_id),
                    },
                    "cancelled": True,
                },
            )
        elif full_text:
            await _save_turn(session_id, history, original_message, full_text)
            await _send(
                ws,
                {
                    "type": "chat.done",
                    "response": full_text,
                    "agent": agent_label,
                    "tool_calls": tool_calls_seen,
                    "thinking": [],
                    "session_id": session_id,
                    "usage": {
                        "cost_usd": 0,
                        "session_cost_usd": await session_store.get_cost(session_id),
                    },
                },
            )

    except asyncio.CancelledError:
        logger.debug("Chat generation task cancelled: session=%s", session_id)
        chat_message(agent_label, "cancelled")
        if full_text:
            await _save_turn(session_id, history, original_message, full_text)
            await _send(
                ws,
                {
                    "type": "chat.done",
                    "response": full_text,
                    "agent": agent_label,
                    "tool_calls": tool_calls_seen,
                    "thinking": [],
                    "session_id": session_id,
                    "usage": {
                        "cost_usd": 0,
                        "session_cost_usd": await session_store.get_cost(session_id),
                    },
                    "cancelled": True,
                },
            )
    except Exception as exc:
        error_type, detail = _classify_chat_error(exc)
        logger.exception(
            "Chat stream %s for user=%s session=%s agent=%s",
            error_type,
            user_id,
            session_id,
            agent_label,
        )
        chat_message(agent_label, error_type)
        await _send(
            ws,
            {"type": "chat.error", "error_type": error_type, "detail": detail},
        )


async def _save_turn(
    session_id: str, history: list[dict] | None, user_msg: str, assistant_msg: str
) -> None:
    """Persist a user+assistant turn to the session store."""
    new_history = list(history or [])
    new_history.append({"role": "user", "content": user_msg})
    new_history.append({"role": "assistant", "content": assistant_msg})
    await session_store.update(session_id, new_history, cost_usd=0)
