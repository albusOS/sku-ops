"""WebSocket endpoint for streaming AI chat responses.

Async job model: the WS handler submits chat requests as background jobs.
Generation runs independently of the WS connection — if the WS drops and
reconnects, the client sends ``chat.resume`` to reattach to the running job.

Protocol (client -> server):
    { "type": "chat", "message": "...", "session_id": "...", "agent_type": "auto" }
    { "type": "cancel" }                    - abort the current generation
    { "type": "chat.resume", "job_id": "..." } - reattach to a running job
    { "type": "pong" }                      - heartbeat response

Protocol (server -> client):
    { "type": "ping" }
    { "type": "chat.job_started", "job_id": "..." }
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

from assistant.agents.core.deps import AgentDeps
from assistant.agents.core.messages import (
    build_message_history,
    extract_text_history,
    extract_tool_calls,
    extract_tool_calls_detailed,
)
from assistant.agents.core.model_registry import calc_cost, get_fallback_model, get_model_name
from assistant.agents.core.tokens import compress_history_async
from assistant.agents.core.validators import classify_intent, validate_response
from assistant.agents.health_analyst.agent import _get_agent as _get_health_agent
from assistant.agents.procurement_analyst.agent import _get_agent as _get_procurement_agent
from assistant.agents.trend_analyst.agent import _get_agent as _get_trend_agent
from assistant.agents.unified.agent import _get_agent
from assistant.application import job_manager, session_store
from assistant.application.assistant import schedule_memory_extraction
from assistant.application.context_assembly import assemble_context
from assistant.application.job_manager import GENERATION_TIMEOUT
from assistant.application.workflows.registry import response_agent_label
from assistant.infrastructure.agent_run_repo import log_agent_run
from assistant.infrastructure.concurrency import (
    GenerationBusyError,
    acquire_generation_slot,
    release_generation_slot,
)
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

_STREAM_OVERLOAD_RETRIES = 2
_STREAM_OVERLOAD_BACKOFF = 5.0  # seconds — matches runner.py's _OVERLOAD_BASE_DELAY

# Background generation tasks — tracked for clean shutdown
_running_tasks: set[asyncio.Task] = set()


def _enrich_specialist_message(user_message: str, context_block: str) -> str:
    if not context_block:
        return user_message
    return f"<context>\n{context_block}\n</context>\n\n{user_message}"


def _classify_chat_error(exc: Exception) -> tuple[str, str]:
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


def _is_overload_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(k in s for k in ("529", "overload", "service unavailable", "capacity"))


router = APIRouter()


def _authenticate(token: str) -> dict | None:
    try:
        return decode_token(token)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def _send(ws: WebSocket, msg: dict) -> bool:
    try:
        await ws.send_text(json.dumps(msg))
        return True
    except (RuntimeError, OSError):
        return False


# ---------------------------------------------------------------------------
# Background generation — runs independently of the WebSocket connection
# ---------------------------------------------------------------------------


async def _run_generation(
    *,
    job_id: str,
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
    """Execute agent generation and publish events via job_manager.

    Runs as a standalone background task — not tied to any WS connection.
    All streaming events are published through the job manager so any
    connected (or reconnecting) client can receive them.
    """
    full_text = ""
    tool_calls_seen: list[dict] = []
    slot_acquired = False

    try:
        await acquire_generation_slot()
        slot_acquired = True
    except GenerationBusyError:
        await job_manager.fail_job(
            job_id,
            {
                "type": "chat.error",
                "error_type": "busy",
                "detail": "The AI assistant is handling several requests right now. "
                "Please try again in a moment.",
            },
        )
        return

    await job_manager.publish_event(job_id, {"type": "chat.status", "status": "thinking"})

    logger.info(
        "Generation started: job=%s user=%s session=%s agent=%s",
        job_id,
        user_id,
        session_id,
        agent_label,
    )

    try:
        model_override: str | None = None
        overload_attempts = 0
        stream_succeeded = False

        for _stream_attempt in range(_STREAM_OVERLOAD_RETRIES + 1):
            full_text = ""
            tool_calls_seen.clear()
            try:
                stream_kwargs: dict = {
                    "message_history": msg_history,
                    "deps": deps,
                }
                if model_override:
                    stream_kwargs["model"] = model_override

                async with asyncio.timeout(GENERATION_TIMEOUT):
                    async for event in agent.run_stream_events(
                        user_message,
                        **stream_kwargs,
                    ):
                        if cancel_event.is_set():
                            logger.info(
                                "Generation cancelled: job=%s session=%s", job_id, session_id
                            )
                            break

                        if isinstance(event, PartStartEvent):
                            if isinstance(event.part, ToolCallPart):
                                tool_name = event.part.tool_name
                                tool_calls_seen.append({"tool": tool_name})
                                await job_manager.publish_event(
                                    job_id, {"type": "chat.tool_start", "tool": tool_name}
                                )
                            elif isinstance(event.part, TextPart):
                                if event.part.content:
                                    full_text += event.part.content
                                    await job_manager.publish_event(
                                        job_id,
                                        {"type": "chat.delta", "content": event.part.content},
                                    )

                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                chunk = event.delta.content_delta
                                if chunk:
                                    full_text += chunk
                                    await job_manager.publish_event(
                                        job_id, {"type": "chat.delta", "content": chunk}
                                    )

                        elif isinstance(event, FinalResultEvent):
                            pass

                        elif isinstance(event, AgentRunResultEvent):
                            result = event.result
                            response_text = (
                                result.output
                                if isinstance(result.output, str)
                                else str(result.output)
                            )

                            if not full_text:
                                full_text = response_text

                            model_name = model_override or get_model_name(f"agent:{agent_label}")
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
                                "Generation done: job=%s session=%s agent=%s cost=%.4f tokens=%d+%d",
                                job_id,
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

                            ui_agent_label = response_agent_label(agent_label, tool_calls_final)
                            done_event = {
                                "type": "chat.done",
                                "response": full_text,
                                "agent": ui_agent_label,
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
                            }
                            await job_manager.complete_job(job_id, done_event)
                            stream_succeeded = True
                            return

                # Inner stream completed without raising — break out of retry loop
                break

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not _is_overload_error(exc):
                    raise

                overload_attempts += 1
                if overload_attempts >= _STREAM_OVERLOAD_RETRIES and not model_override:
                    primary = get_model_name(
                        f"agent:{agent_label}" if agent_label else "agent:unified"
                    )
                    fallback = get_fallback_model(primary)
                    if fallback:
                        logger.warning(
                            "Stream overloaded after %d attempts, falling back to %s: "
                            "job=%s session=%s",
                            overload_attempts,
                            fallback,
                            job_id,
                            session_id,
                        )
                        model_override = fallback
                        overload_attempts = 0
                        await job_manager.publish_event(
                            job_id,
                            {"type": "chat.status", "status": "retrying"},
                        )
                        await asyncio.sleep(_STREAM_OVERLOAD_BACKOFF)
                        continue
                    raise

                logger.warning(
                    "Stream overloaded (attempt %d/%d), backing off: job=%s session=%s",
                    overload_attempts,
                    _STREAM_OVERLOAD_RETRIES,
                    job_id,
                    session_id,
                )
                await job_manager.publish_event(
                    job_id,
                    {"type": "chat.status", "status": "retrying"},
                )
                await asyncio.sleep(_STREAM_OVERLOAD_BACKOFF * (2 ** (overload_attempts - 1)))

        if stream_succeeded:
            return

        # Stream ended without AgentRunResultEvent (cancel or partial)
        if cancel_event.is_set():
            response = full_text or "Generation cancelled."
            await _save_turn(session_id, history, original_message, response)
            cancel_done = {
                "type": "chat.done",
                "response": response,
                "agent": response_agent_label(agent_label, tool_calls_seen),
                "tool_calls": tool_calls_seen,
                "thinking": [],
                "session_id": session_id,
                "usage": {
                    "cost_usd": 0,
                    "session_cost_usd": await session_store.get_cost(session_id),
                },
                "cancelled": True,
            }
            await job_manager.complete_job(job_id, cancel_done)
        elif full_text:
            await _save_turn(session_id, history, original_message, full_text)
            partial_done = {
                "type": "chat.done",
                "response": full_text,
                "agent": response_agent_label(agent_label, tool_calls_seen),
                "tool_calls": tool_calls_seen,
                "thinking": [],
                "session_id": session_id,
                "usage": {
                    "cost_usd": 0,
                    "session_cost_usd": await session_store.get_cost(session_id),
                },
            }
            await job_manager.complete_job(job_id, partial_done)
        else:
            logger.warning(
                "Generation ended with no output: job=%s session=%s agent=%s",
                job_id,
                session_id,
                agent_label,
            )
            await job_manager.fail_job(
                job_id,
                {
                    "type": "chat.error",
                    "error_type": "empty_response",
                    "detail": "No response generated. Please try again.",
                },
            )

    except asyncio.CancelledError:
        logger.debug("Generation task cancelled: job=%s session=%s", job_id, session_id)
        chat_message(agent_label, "cancelled")
        if full_text:
            await _save_turn(session_id, history, original_message, full_text)
        await job_manager.cancel_job(job_id)
    except Exception as exc:
        error_type, detail = _classify_chat_error(exc)
        logger.exception(
            "Generation %s for job=%s user=%s session=%s agent=%s",
            error_type,
            job_id,
            user_id,
            session_id,
            agent_label,
        )
        chat_message(agent_label, error_type)
        try:
            await job_manager.fail_job(
                job_id, {"type": "chat.error", "error_type": error_type, "detail": detail}
            )
        except Exception:
            logger.exception("fail_job itself failed for job=%s", job_id)
    finally:
        if slot_acquired:
            release_generation_slot()


async def _save_turn(
    session_id: str, history: list[dict] | None, user_msg: str, assistant_msg: str
) -> None:
    new_history = list(history or [])
    new_history.append({"role": "user", "content": user_msg})
    new_history.append({"role": "assistant", "content": assistant_msg})
    await session_store.update(session_id, new_history, cost_usd=0)


# ---------------------------------------------------------------------------
# WebSocket endpoint — thin relay
# ---------------------------------------------------------------------------


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

    active_job_id: str | None = None
    cancel_event: asyncio.Event | None = None
    relay_task: asyncio.Task | None = None
    ws = websocket

    async def _relay_events(job_id: str) -> None:
        """Subscribe to a job's event stream and forward to the WS client."""
        try:
            async for event in job_manager.subscribe_job(job_id):
                if not await _send(ws, event):
                    return
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.warning("Relay task error for job %s", job_id, exc_info=True)
            await _send(
                ws,
                {
                    "type": "chat.error",
                    "error_type": "relay_error",
                    "detail": "Lost connection to generation stream. Try refreshing.",
                },
            )

    async def _heartbeat():
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if not await _send(ws, {"type": "ping"}):
                return

    async def _receiver():
        nonlocal active_job_id, cancel_event, relay_task
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
                    if active_job_id:
                        await job_manager.cancel_job(active_job_id)
                    if relay_task and not relay_task.done():
                        relay_task.cancel()
                        with contextlib.suppress(Exception):
                            await relay_task
                    active_job_id = None
                    cancel_event = None
                    relay_task = None
                    continue

                if msg_type == "chat.resume":
                    resume_job_id = msg.get("job_id", "")
                    if not resume_job_id:
                        continue
                    logger.info("Chat WS resume: user=%s job=%s", user_id, resume_job_id)

                    if relay_task and not relay_task.done():
                        relay_task.cancel()
                        with contextlib.suppress(Exception):
                            await relay_task
                        relay_task = None

                    status = await job_manager.get_job_status(resume_job_id)
                    if not status:
                        await _send(
                            ws,
                            {
                                "type": "chat.error",
                                "detail": "Job not found or expired.",
                            },
                        )
                        continue

                    if status["status"] in ("completed", "failed", "cancelled"):
                        events = await job_manager.get_job_events(resume_job_id)
                        for ev in events:
                            if not await _send(ws, ev):
                                return
                        active_job_id = None
                    else:
                        active_job_id = resume_job_id
                        buffered = await job_manager.get_job_events(resume_job_id)
                        for ev in buffered:
                            if not await _send(ws, ev):
                                return
                        relay_task = asyncio.create_task(_relay_events(resume_job_id))
                    continue

                if msg_type == "chat":
                    if active_job_id:
                        await _send(
                            ws,
                            {
                                "type": "chat.error",
                                "detail": "Already generating a response. Send 'cancel' first.",
                            },
                        )
                        continue

                    cancel_event = asyncio.Event()
                    result = await _submit_chat(ws, msg, user_id, user_name, cancel_event)
                    if result:
                        active_job_id = result
                        await _send(ws, {"type": "chat.job_started", "job_id": result})
                        relay_task = asyncio.create_task(_relay_events(result))
                    else:
                        cancel_event = None

        except WebSocketDisconnect:
            logger.debug("Chat WS disconnected: user=%s", user_id)
        except (RuntimeError, OSError, ValueError) as e:
            logger.warning("Chat WS receiver error for user=%s: %s", user_id, e)
        finally:
            if relay_task and not relay_task.done():
                relay_task.cancel()
                with contextlib.suppress(Exception):
                    await relay_task

    tasks = [
        asyncio.create_task(_heartbeat()),
        asyncio.create_task(_receiver()),
    ]
    try:
        _done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
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


# ---------------------------------------------------------------------------
# Chat submission — validates, prepares context, spawns background task
# ---------------------------------------------------------------------------


async def _submit_chat(
    ws: WebSocket,
    msg: dict,
    user_id: str,
    user_name: str,
    cancel_event: asyncio.Event,
) -> str | None:
    """Validate and submit a chat message. Returns job_id or None on validation failure."""
    user_message = (msg.get("message") or "").strip()
    session_id = msg.get("session_id") or str(uuid.uuid4())

    if not user_message:
        await _send(ws, {"type": "chat.error", "detail": "Empty message"})
        return None

    if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE:
        await _send(ws, {"type": "chat.error", "detail": "AI not configured."})
        return None

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
        return None

    job_id = await job_manager.create_job(session_id=session_id, user_id=user_id)

    task = asyncio.create_task(
        _prepare_and_generate(
            job_id=job_id,
            msg=msg,
            user_id=user_id,
            user_name=user_name,
            cancel_event=cancel_event,
            session_id=session_id,
            user_message=user_message,
        )
    )
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)

    return job_id


async def _prepare_and_generate(
    *,
    job_id: str,
    msg: dict,
    user_id: str,
    user_name: str,
    cancel_event: asyncio.Event,
    session_id: str,
    user_message: str,
) -> None:
    """Pre-process (context assembly, history compression) then run generation."""
    try:
        history = await session_store.get_or_create(session_id)

        requested_agent = (msg.get("agent_type") or "").strip().lower()
        specialist_agents = frozenset({"procurement", "trend", "health"})
        route = requested_agent if requested_agent in specialist_agents else "unified"
        is_first_turn = not history

        compress_task = asyncio.create_task(compress_history_async(history))
        if route in specialist_agents:
            context_task = asyncio.create_task(
                assemble_context(
                    query=user_message,
                    user_id=user_id,
                    include_graph=False,
                    include_memory=False,
                    max_entity_hits=0,
                )
            )
        else:
            context_task = asyncio.create_task(
                assemble_context(
                    query=user_message,
                    user_id=user_id,
                    include_memory=is_first_turn,
                )
            )

        compressed = await compress_task
        history = compressed if compressed is not None else history

        assembled = await context_task
        context_block = assembled.format_for_agent()

        clean_history = [h for h in (history or []) if h.get("role") != "system"]
        deps = AgentDeps(user_id=user_id, user_name=user_name, history=clean_history)
        msg_history = build_message_history(clean_history)

        logger.info("Agent mode: %s for message='%s...'", route, (user_message or "")[:50])

        _specialist_agent_map = {
            "procurement": _get_procurement_agent,
            "trend": _get_trend_agent,
            "health": _get_health_agent,
        }

        enriched = _enrich_specialist_message(user_message, context_block)

        agent = _specialist_agent_map[route]() if route in specialist_agents else _get_agent()

        await _run_generation(
            job_id=job_id,
            agent=agent,
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
    except Exception as exc:
        error_type, detail = _classify_chat_error(exc)
        logger.exception("Pre-processing failed for job %s", job_id)
        try:
            await job_manager.fail_job(
                job_id, {"type": "chat.error", "error_type": error_type, "detail": detail}
            )
        except Exception:
            logger.exception("fail_job itself failed for job=%s", job_id)


# ---------------------------------------------------------------------------
# Shutdown hook — cancel all running generation tasks
# ---------------------------------------------------------------------------


async def shutdown_generation_tasks() -> None:
    """Cancel all running generation tasks. Called from lifespan shutdown."""
    if not _running_tasks:
        return
    logger.info("Shutting down %d generation task(s)", len(_running_tasks))
    for task in list(_running_tasks):
        task.cancel()
    await asyncio.gather(*_running_tasks, return_exceptions=True)
    _running_tasks.clear()
