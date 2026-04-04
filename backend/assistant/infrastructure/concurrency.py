"""Concurrency limiter for outbound LLM API calls.

Prevents the process from hammering the provider when it's already under load.
Callers that exceed the limit get a fast, user-friendly rejection instead of
queueing up and making the overload worse.

The semaphore is per-process — in multi-worker mode each worker gets its own
limit, which is the correct behavior (each has its own event loop).
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

MAX_CONCURRENT_GENERATIONS = int(os.environ.get("MAX_CONCURRENT_GENERATIONS", "4"))
_QUEUE_TIMEOUT = float(os.environ.get("GENERATION_QUEUE_TIMEOUT", "10"))

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)
    return _semaphore


class GenerationBusyError(Exception):
    """Raised when concurrency limit is reached and the queue times out."""


async def acquire_generation_slot() -> None:
    """Acquire a generation slot, waiting up to _QUEUE_TIMEOUT seconds.

    Raises GenerationBusyError if a slot cannot be obtained in time.
    """
    sem = _get_semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=_QUEUE_TIMEOUT)
    except TimeoutError:
        logger.warning(
            "Generation concurrency limit reached (%d active), rejecting request",
            MAX_CONCURRENT_GENERATIONS,
        )
        raise GenerationBusyError(
            "The AI assistant is handling several requests right now. Please try again in a moment."
        ) from None


def release_generation_slot() -> None:
    """Release a previously acquired generation slot."""
    sem = _get_semaphore()
    sem.release()


def active_generation_count() -> int:
    """Return number of in-flight generations (for health/metrics)."""
    sem = _get_semaphore()
    return MAX_CONCURRENT_GENERATIONS - sem._value  # noqa: SLF001
