"""Chat job lifecycle — Redis-backed with in-process fallback.

Decouples agent generation from WebSocket connection lifetime. A "job"
represents a single chat generation: submitted by the WS handler, executed
by a standalone background task, and streamed to any connected client via
Redis pub/sub (or in-process asyncio queues when Redis is unavailable).

Job state is ephemeral — TTL'd in Redis after completion. This is not
a durable task queue; it exists to survive WS reconnects during generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from shared.helpers.uuid import new_uuid7_str

logger = logging.getLogger(__name__)

_JOB_TTL = 600  # 10 minutes after completion
_CHANNEL_PREFIX = "sku_ops:chat:job:"
_KEY_PREFIX = "sku_ops:chat:job:"
GENERATION_TIMEOUT = 180  # standalone generation ceiling


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChatJob:
    job_id: str
    session_id: str
    user_id: str
    status: JobStatus = JobStatus.RUNNING
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)


def _use_redis() -> bool:
    from shared.infrastructure.redis import is_redis_available

    return is_redis_available()


def _redis():
    from shared.infrastructure.redis import get_redis

    return get_redis()


# ---------------------------------------------------------------------------
# In-process fallback (dev/test without Redis)
# ---------------------------------------------------------------------------

_local_jobs: dict[str, ChatJob] = {}
_local_channels: dict[str, list[asyncio.Queue]] = {}
_local_event_logs: dict[str, list[dict]] = {}


def _local_publish(job_id: str, event: dict) -> None:
    """Publish to in-process subscriber queues and append to event log."""
    _local_event_logs.setdefault(job_id, []).append(event)
    for q in _local_channels.get(job_id, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Dropping event for slow local subscriber on job %s", job_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_job(session_id: str, user_id: str) -> str:
    """Create a new chat job. Returns the job_id."""
    job_id = new_uuid7_str()
    job = ChatJob(job_id=job_id, session_id=session_id, user_id=user_id)

    if _use_redis():
        await _redis_create_job(job)
    else:
        _local_jobs[job_id] = job
        _local_event_logs[job_id] = []

    return job_id


async def _redis_create_job(job: ChatJob) -> None:
    r = _redis()
    key = f"{_KEY_PREFIX}{job.job_id}"
    await r.hset(
        key,
        mapping={
            "session_id": job.session_id,
            "user_id": job.user_id,
            "status": job.status.value,
            "text": "",
            "tool_calls": "[]",
            "blocks": "[]",
            "error": "",
            "events": "[]",
        },
    )
    await r.expire(key, _JOB_TTL)


async def publish_event(job_id: str, event: dict) -> None:
    """Publish a streaming event for a job (delta, tool_start, block, etc.)."""
    if _use_redis():
        r = _redis()
        channel = f"{_CHANNEL_PREFIX}{job_id}"
        await r.publish(channel, json.dumps(event))
        key = f"{_KEY_PREFIX}{job_id}"
        await _redis_append_event(key, event)
    else:
        _local_publish(job_id, event)


async def _redis_append_event(key: str, event: dict) -> None:
    """Append event to the job's event log for replay on resume."""
    r = _redis()
    raw = await r.hget(key, "events")
    events = json.loads(raw) if raw else []
    events.append(event)
    if len(events) > 500:
        events = events[-500:]
    await r.hset(key, "events", json.dumps(events))


async def complete_job(job_id: str, final_event: dict) -> None:
    """Mark a job as completed with the final chat.done payload."""
    if _use_redis():
        r = _redis()
        key = f"{_KEY_PREFIX}{job_id}"
        channel = f"{_CHANNEL_PREFIX}{job_id}"
        await r.hset(
            key,
            mapping={
                "status": JobStatus.COMPLETED.value,
                "text": final_event.get("response", ""),
            },
        )
        await _redis_append_event(key, final_event)
        await r.publish(channel, json.dumps(final_event))
        await r.expire(key, _JOB_TTL)
    else:
        job = _local_jobs.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.text = final_event.get("response", "")
        _local_publish(job_id, final_event)


async def fail_job(job_id: str, error_event: dict) -> None:
    """Mark a job as failed with an error event."""
    if _use_redis():
        r = _redis()
        key = f"{_KEY_PREFIX}{job_id}"
        channel = f"{_CHANNEL_PREFIX}{job_id}"
        await r.hset(
            key,
            mapping={
                "status": JobStatus.FAILED.value,
                "error": error_event.get("detail", "Unknown error"),
            },
        )
        await _redis_append_event(key, error_event)
        await r.publish(channel, json.dumps(error_event))
        await r.expire(key, _JOB_TTL)
    else:
        job = _local_jobs.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.error = error_event.get("detail", "Unknown error")
        _local_publish(job_id, error_event)


async def cancel_job(job_id: str) -> None:
    """Mark a job as cancelled."""
    cancel_event = {
        "type": "chat.done",
        "cancelled": True,
        "response": "Generation cancelled.",
    }
    if _use_redis():
        r = _redis()
        key = f"{_KEY_PREFIX}{job_id}"
        channel = f"{_CHANNEL_PREFIX}{job_id}"
        await r.hset(key, "status", JobStatus.CANCELLED.value)
        await _redis_append_event(key, cancel_event)
        await r.publish(channel, json.dumps(cancel_event))
        await r.expire(key, _JOB_TTL)
    else:
        job = _local_jobs.get(job_id)
        if job:
            job.status = JobStatus.CANCELLED
        _local_publish(job_id, cancel_event)


async def get_job_status(job_id: str) -> dict | None:
    """Get current job state. Returns None if job doesn't exist."""
    if _use_redis():
        r = _redis()
        key = f"{_KEY_PREFIX}{job_id}"
        data = await r.hgetall(key)
        if not data:
            return None
        return {
            "job_id": job_id,
            "status": data.get("status", "unknown"),
            "session_id": data.get("session_id", ""),
            "text": data.get("text", ""),
            "error": data.get("error", ""),
        }
    job = _local_jobs.get(job_id)
    if not job:
        return None
    return {
        "job_id": job_id,
        "status": job.status.value,
        "session_id": job.session_id,
        "text": job.text,
        "error": job.error or "",
    }


async def get_job_events(job_id: str) -> list[dict]:
    """Get all buffered events for replay on resume."""
    if _use_redis():
        r = _redis()
        key = f"{_KEY_PREFIX}{job_id}"
        raw = await r.hget(key, "events")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    return list(_local_event_logs.get(job_id, []))


async def subscribe_job(job_id: str) -> AsyncIterator[dict]:
    """Subscribe to live events for a job.

    Yields events as they arrive. Terminates when a terminal event
    (chat.done or chat.error) is received.
    """
    if _use_redis():
        async for event in _redis_subscribe(job_id):
            yield event
    else:
        async for event in _local_subscribe(job_id):
            yield event


async def _redis_subscribe(job_id: str) -> AsyncIterator[dict]:
    r = _redis()
    channel = f"{_CHANNEL_PREFIX}{job_id}"
    pubsub = r.pubsub()
    try:
        await pubsub.subscribe(channel)
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg is None:
                status = await get_job_status(job_id)
                if status and status["status"] in (
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                ):
                    return
                continue
            if msg["type"] != "message":
                continue
            try:
                event = json.loads(msg["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            yield event
            if event.get("type") in ("chat.done", "chat.error"):
                return
    except asyncio.CancelledError:
        pass
    finally:
        try:
            with asyncio.timeout(2):
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
        except Exception:
            logger.debug("Pubsub cleanup failed for channel %s", channel, exc_info=True)


async def _local_subscribe(job_id: str) -> AsyncIterator[dict]:
    q: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)
    _local_channels.setdefault(job_id, []).append(q)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=2.0)
            except TimeoutError:
                job = _local_jobs.get(job_id)
                if job and job.status != JobStatus.RUNNING:
                    return
                continue
            yield event
            if event.get("type") in ("chat.done", "chat.error"):
                return
    except asyncio.CancelledError:
        pass
    finally:
        subs = _local_channels.get(job_id, [])
        if q in subs:
            subs.remove(q)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_local() -> None:
    """Remove expired local jobs. Called periodically in dev/test."""
    now = time.monotonic()
    expired = [jid for jid, job in _local_jobs.items() if now - job.created_at > _JOB_TTL]
    for jid in expired:
        _local_jobs.pop(jid, None)
        _local_event_logs.pop(jid, None)
        _local_channels.pop(jid, None)
