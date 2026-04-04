"""Token counting, budget management, and context compression.

Uses cl100k_base encoding as an approximation for both Anthropic and
OpenRouter models.  Not exact, but close enough for budget decisions.
"""

import json
import logging

import tiktoken

from assistant.agents.core.model_registry import get_model_name
from assistant.application.llm import generate_text
from shared.infrastructure.config import ANTHROPIC_AVAILABLE, OPENROUTER_AVAILABLE, is_test

logger = logging.getLogger(__name__)

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return approximate token count for a string."""
    if not text:
        return 0
    return len(_enc.encode(text))


# ── Tool result budgeting ─────────────────────────────────────────────────────
# Fields to drop first when trimming (low information density).
# sell_uom is NOT here — the system prompt requires UOM in every answer.
_LOW_VALUE_FIELDS = frozenset(
    (
        "_note",
        "method",
        "original_sku",
        "barcode",
    )
)

# JSON keys that typically contain list items
_LIST_KEYS = (
    "skus",
    "forecast",
    "suggestions",
    "slow_movers",
    "withdrawals",
    "balances",
    "pending_requests",
    "departments",
    "vendors",
    "items",
)


def budget_tool_result(raw_json: str, max_tokens: int = 2000) -> str:
    """Truncate a tool's JSON output if it exceeds *max_tokens*.

    Strategy (applied in order until under budget):
    1. Drop low-value fields from each item in lists
    2. Trim the list to fewer items (keep first N)
    3. Hard character-level truncation as last resort
    """
    tokens = count_tokens(raw_json)
    if tokens <= max_tokens:
        return raw_json

    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return raw_json[: max_tokens * 4]  # ~4 chars per token fallback

    # Phase 1: drop low-value fields from list items
    for key in _LIST_KEYS:
        items = data.get(key)
        if isinstance(items, list):
            data[key] = [
                {k: v for k, v in item.items() if k not in _LOW_VALUE_FIELDS}
                if isinstance(item, dict)
                else item
                for item in items
            ]

    trimmed = json.dumps(data, separators=(",", ":"))
    if count_tokens(trimmed) <= max_tokens:
        return trimmed

    # Phase 2: reduce list length
    for key in _LIST_KEYS:
        items = data.get(key)
        if isinstance(items, list) and len(items) > 3:
            original_count = len(items)
            while (
                len(items) > 3
                and count_tokens(json.dumps(data, separators=(",", ":"))) > max_tokens
            ):
                items.pop()
            data[key] = items
            data[f"_{key}_truncated"] = f"{len(items)}/{original_count} shown"

    trimmed = json.dumps(data, separators=(",", ":"))
    if count_tokens(trimmed) <= max_tokens:
        return trimmed

    # Phase 3: result still too large — return a structured truncation notice so the
    # model receives valid JSON rather than a broken fragment.
    return json.dumps(
        {
            "_truncated": True,
            "_note": f"Result exceeded {max_tokens} token budget after trimming. Ask for a more specific query.",
        }
    )


def estimate_turn_tokens(
    system_prompt: str,
    history: list[dict] | None,
    user_message: str,
) -> dict[str, int]:
    """Pre-flight estimate of input tokens for an agent turn."""
    sys_tokens = count_tokens(system_prompt)
    msg_tokens = count_tokens(user_message)
    hist_tokens = 0
    if history:
        hist_tokens = sum(count_tokens(h.get("content", "")) for h in history)
    overhead = 50  # framing tokens (role markers, separators)
    return {
        "system": sys_tokens,
        "history": hist_tokens,
        "user_message": msg_tokens,
        "overhead": overhead,
        "total_estimate": sys_tokens + hist_tokens + msg_tokens + overhead,
    }


# ── History compression ───────────────────────────────────────────────────────


# Synchronous fallback — drop oldest turns, keep most recent.
def _compress_truncate(
    history: list[dict],
    max_tokens: int = 8000,
) -> list[dict]:
    """Trim conversation history by dropping oldest user/assistant pairs first.

    Drops turns as pairs to avoid orphaning an assistant message without a
    preceding user message (which some LLM APIs reject).
    """
    if len(history) <= 4:
        return history

    total = sum(count_tokens(h.get("content", "")) for h in history)
    if total <= max_tokens:
        return history

    # Partition into a leading system block (if any) and conversation turns.
    # System entries are always kept — they carry critical context.
    system_prefix = [h for h in history if h.get("role") == "system"]
    conv = [h for h in history if h.get("role") != "system"]

    # Always keep the last 2 turns (1 user + 1 assistant)
    kept = list(conv[-2:])
    budget_remaining = (
        max_tokens
        - sum(count_tokens(h.get("content", "")) for h in system_prefix)
        - sum(count_tokens(h.get("content", "")) for h in kept)
    )

    # Add older pairs from most-recent backward until budget exhausted.
    # Step by 2 to always consume a user+assistant pair together.
    older = conv[:-2]
    i = len(older) - 1
    while i >= 1:
        # Pair = older[i-1] (user) + older[i] (assistant) when i is odd-indexed
        pair = older[i - 1 : i + 1]
        pair_tokens = sum(count_tokens(h.get("content", "")) for h in pair)
        if budget_remaining - pair_tokens < 0:
            break
        kept = pair + kept
        budget_remaining -= pair_tokens
        i -= 2

    return system_prefix + kept


def compress_history(
    history: list[dict] | None,
    max_tokens: int = 8000,
) -> list[dict] | None:
    """Synchronous compression — truncation only. Use for non-async callers."""
    if not history:
        return history
    return _compress_truncate(history, max_tokens)


_LLM_SUMMARIZE_THRESHOLD = 16  # messages (~8 turns) before paying for an LLM call


async def compress_history_async(
    history: list[dict] | None,
    max_tokens: int = 8000,
) -> list[dict] | None:
    """Async compression with progressive summarization.

    Uses cheap truncation for short/medium histories.  Only invokes the
    LLM summarizer when the conversation is long enough (>= 16 messages)
    to justify the latency.

    Strategy:
        Tier 0 — Short history or under budget → return as-is
        Tier 1 — Medium history (< 16 msgs) → truncation only (zero LLM cost)
        Tier 2 — Long history (>= 16 msgs) → summarize older turns via LLM
        Tier 3 — If summary + recent still too large, truncate recent
    """
    if not history:
        return history
    if len(history) <= 6:
        return history

    total = sum(count_tokens(h.get("content", "")) for h in history)
    if total <= max_tokens:
        return history

    # For short-to-medium conversations, truncation is fast and good enough.
    if len(history) < _LLM_SUMMARIZE_THRESHOLD:
        return _compress_truncate(history, max_tokens)

    # Split into recent (keep) and older (summarize)
    recent = history[-6:]  # last 3 turns
    older = history[:-6]

    if not older:
        return _compress_truncate(history, max_tokens)

    summary = await _summarize_turns(older)
    if summary:
        summary_turn = {"role": "user", "content": f"[Prior conversation summary]: {summary}"}
        summary_ack = {"role": "assistant", "content": "Understood. Continuing from that context."}
        result = [summary_turn, summary_ack, *recent]
        result_tokens = sum(count_tokens(h.get("content", "")) for h in result)
        if result_tokens <= max_tokens:
            return result
        return _compress_truncate(result, max_tokens)

    return _compress_truncate(history, max_tokens)


async def _summarize_turns(turns: list[dict], max_summary_tokens: int = 300) -> str | None:
    """Summarize conversation turns using a cheap model.

    Returns None if LLM is unavailable. Never raises.
    """
    try:
        if not ANTHROPIC_AVAILABLE and not OPENROUTER_AVAILABLE and not is_test:
            return None

        model_id = get_model_name("infra:synthesis")

        lines = []
        for t in turns:
            role = (t.get("role") or "user").upper()
            content = (t.get("content") or "").strip()[:400]
            if content:
                lines.append(f"{role}: {content}")
        if not lines:
            return None

        text = "\n".join(lines)
        result = await generate_text(
            text,
            "Summarize this conversation concisely. Preserve: entity names, "
            "numbers, decisions made, questions still open, and any user "
            "preferences expressed. Max 3-4 sentences.",
            model_id,
        )
        return result.strip() if result else None

    except Exception as e:
        logger.debug("Turn summarization failed (non-critical): %s", e)
        return None
