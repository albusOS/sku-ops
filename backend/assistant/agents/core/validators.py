"""Structured response validators — deterministic structural checks + LLM intent classifier.

Architecture:
    classify_intent()   — async, cheap LLM call to classify the user's intent.
                          Returns IntentClassification. Falls back to a permissive
                          default if the LLM is unavailable so validation never blocks.
    validate_response() — sync, deterministic checks on tool coverage, data grounding,
                          format compliance, and token efficiency. Accepts an optional
                          IntentClassification to drive intent-dependent checks instead
                          of brittle keyword heuristics.

The intent classifier is the source of truth for:
    - Does this message need tool calls?
    - What domain(s) does it touch?
    - Does the user expect tabular output?

Deterministic checks remain for things the LLM cannot self-verify:
    - Did the agent actually invoke tools (structural count)?
    - Are the numbers in the response grounded in tool output (data integrity)?
    - Is the response an appropriate length?
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)

# ── Number extraction ──────────────────────────────────────────────────────────
# Handles: 1,234.56  |  42  |  .5  |  3.14
_NUMBER_RE = re.compile(r"\b\d[\d,]*\.?\d*\b|\B\.\d+\b")

# ── Intent cache (avoids duplicate LLM calls for same message in same process) ─
_intent_cache: dict[str, IntentClassification] = {}
_CACHE_MAX = 512


# ── Data classes ───────────────────────────────────────────────────────────────


@dataclass
class IntentClassification:
    """Result of the LLM intent classifier."""

    needs_tools: bool
    """True when the question requires live data lookup (tool calls expected)."""
    domains: list[str]
    """Relevant tool domains: inventory, ops, finance, finance_analytics, purchasing."""
    expects_table: bool
    """True when the user would expect tabular output."""
    is_conversational: bool
    """True for greetings, acks, clarifications — skip structural validation."""
    source: str = "llm"
    """'llm' | 'fallback' — indicates whether the classifier ran."""


@dataclass
class ValidationResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)


# ── Classifier ────────────────────────────────────────────────────────────────

_CLASSIFIER_SYSTEM = """\
You are an intent classifier for a supply chain operations assistant.
Classify the user message and respond with ONLY a JSON object — no markdown, no prose.

Schema:
{
  "needs_tools": <bool>,       // true if answering requires fetching live data
  "domains": <string[]>,       // subset of: ["inventory","ops","finance","finance_analytics","purchasing"]
  "expects_table": <bool>,     // true if user expects a list/table in response
  "is_conversational": <bool>  // true for greetings, acks, clarifications, capability questions
}

Domain guide:
  inventory        — products, stock levels, SKUs, departments, reorder
  ops              — withdrawals, contractors, jobs, material requests
  finance          — invoices, payments, revenue, P&L, balances
  finance_analytics — trends, margins, AR aging, profitability, spend analysis
  purchasing       — vendors, purchase orders, vendor performance, procurement

Examples:
  "hi there" → {"needs_tools":false,"domains":[],"expects_table":false,"is_conversational":true}
  "what are our top selling products this month?" → {"needs_tools":true,"domains":["inventory"],"expects_table":true,"is_conversational":false}
  "show me product margins" → {"needs_tools":true,"domains":["finance_analytics"],"expects_table":true,"is_conversational":false}
  "are any POs outstanding?" → {"needs_tools":true,"domains":["purchasing","finance"],"expects_table":false,"is_conversational":false}
  "what's the AR aging?" → {"needs_tools":true,"domains":["finance_analytics"],"expects_table":true,"is_conversational":false}
"""

_FALLBACK_INTENT = IntentClassification(
    needs_tools=True,
    domains=[],
    expects_table=False,
    is_conversational=False,
    source="fallback",
)


async def classify_intent(user_message: str) -> IntentClassification:
    """Classify user intent via a cheap LLM call.

    Returns IntentClassification. Falls back to a permissive default
    (needs_tools=True, no domain assertions) if the LLM is unavailable,
    so validation never blocks the main agent response.
    """
    cache_key = hashlib.md5(user_message.encode(), usedforsecurity=False).hexdigest()
    if cache_key in _intent_cache:
        return _intent_cache[cache_key]

    try:
        from assistant.agents.core.model_registry import get_model_name
        from assistant.infrastructure.llm import get_provider

        provider = get_provider()
        if not provider.available or provider.provider_name == "stub":
            return _FALLBACK_INTENT

        model_id = get_model_name("infra:classifier")
        raw = await asyncio.to_thread(
            provider.generate_text,
            user_message,
            _CLASSIFIER_SYSTEM,
            model_id,
        )
        if not raw:
            return _FALLBACK_INTENT

        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.removeprefix("```json").removeprefix("```")
            stripped = stripped.removesuffix("```").strip()

        data = json.loads(stripped)
        result = IntentClassification(
            needs_tools=bool(data.get("needs_tools", True)),
            domains=list(data.get("domains") or []),
            expects_table=bool(data.get("expects_table", False)),
            is_conversational=bool(data.get("is_conversational", False)),
            source="llm",
        )

        if len(_intent_cache) >= _CACHE_MAX:
            _intent_cache.clear()
        _intent_cache[cache_key] = result
        return result

    except Exception as e:
        logger.debug("Intent classifier failed (%s), using fallback", e)
        return _FALLBACK_INTENT


# ── Domain tool cross-reference (structural check only) ───────────────────────

_domain_tool_cache: dict[str, dict[str, set[str]]] = {}


@lru_cache(maxsize=1)
def _get_domain_tool_sets() -> dict[str, set[str]]:
    """Derive domain-to-tool-name mapping from the tool registry."""
    from assistant.agents.tools.registry import all_tools

    mapping: dict[str, set[str]] = {}
    for entry in all_tools().values():
        mapping.setdefault(entry.domain, set()).add(entry.name)
    # Aliased memberships: a tool in finance_analytics satisfies a finance-domain intent,
    # and a purchasing tool satisfies an inventory/vendor-domain intent.
    mapping.setdefault("finance", set()).update(mapping.get("finance_analytics", set()))
    mapping.setdefault("inventory", set()).update(mapping.get("purchasing", set()))
    mapping.setdefault("inventory_analytics", set()).update(mapping.get("inventory", set()))
    return mapping


# ── Number helpers ─────────────────────────────────────────────────────────────


def _extract_numbers(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(text))


def _numbers_from_tool_results(tool_calls_detailed: list[dict]) -> set[str]:
    nums: set[str] = set()
    for tc in tool_calls_detailed:
        preview = tc.get("result_preview", "")
        if preview:
            nums |= _extract_numbers(preview)
    return nums


# ── Main validator ─────────────────────────────────────────────────────────────


def validate_response(
    user_message: str,
    response_text: str,
    tool_calls: list[dict],
    tool_calls_detailed: list[dict],
    intent: IntentClassification | None = None,
) -> ValidationResult:
    """Run deterministic structural validators.

    *intent* is the result of classify_intent(). If None (e.g. classifier was
    not awaited), the intent-dependent checks are skipped rather than falling
    back to keyword heuristics — this keeps validation honest.
    """
    failures: list[str] = []
    scores: dict[str, float] = {}

    m = user_message.lower().strip()

    # ── Skip everything for very short or conversational messages ─────────
    if len(m) < 5:
        return ValidationResult(passed=True, scores={"trivial": 1.0})
    if intent is not None and intent.is_conversational:
        return ValidationResult(passed=True, scores={"conversational": 1.0})

    if not response_text or len(response_text) < 10:
        return ValidationResult(passed=True, scores={"empty_response": 0.0})

    # ── 1. Tool coverage ──────────────────────────────────────────────────
    # Only flag if the classifier confirmed this is a data question.
    if intent is not None and intent.needs_tools and not tool_calls:
        failures.append("no_tools_called")
        scores["tool_coverage"] = 0.0
    else:
        scores["tool_coverage"] = 1.0

    # ── 2. Data grounding ─────────────────────────────────────────────────
    if tool_calls_detailed:
        resp_nums = _extract_numbers(response_text)
        tool_nums = _numbers_from_tool_results(tool_calls_detailed)
        if resp_nums and tool_nums:
            grounded = resp_nums & tool_nums
            grounding_ratio = len(grounded) / len(resp_nums)
            scores["data_grounding"] = round(grounding_ratio, 2)
            if grounding_ratio < 0.5 and len(resp_nums) > 2:
                ungrounded = resp_nums - tool_nums
                failures.append(f"ungrounded_numbers:{len(ungrounded)}")
        else:
            scores["data_grounding"] = 1.0
    else:
        scores["data_grounding"] = 1.0

    # ── 3. Format compliance ──────────────────────────────────────────────
    if intent is not None and intent.expects_table and tool_calls:
        has_table = "|" in response_text and "---" in response_text
        if not has_table and len(response_text) > 200:
            scores["format_compliance"] = 0.5
        else:
            scores["format_compliance"] = 1.0

    # ── 4. Token efficiency ───────────────────────────────────────────────
    resp_len = len(response_text)
    if resp_len > 5000 and len(m) < 50:
        scores["token_efficiency"] = 0.5
    elif resp_len > 3000 and len(m) < 30:
        scores["token_efficiency"] = 0.6
    else:
        scores["token_efficiency"] = 1.0

    # ── 5. Domain mismatch ────────────────────────────────────────────────
    # Only check if the classifier provided explicit domains AND tools were called.
    if intent is not None and intent.domains and tool_calls:
        tool_names = {tc.get("tool", "") for tc in tool_calls}
        domain_tool_sets = _get_domain_tool_sets()
        tool_domains: set[str] = set()
        for t in tool_names:
            for domain_name, tool_set in domain_tool_sets.items():
                if t in tool_set:
                    tool_domains.add(domain_name)
        question_domains = set(intent.domains)
        if tool_domains and not (question_domains & tool_domains):
            failures.append("domain_mismatch")
            scores["domain_match"] = 0.0
        else:
            scores["domain_match"] = 1.0

    passed = len(failures) == 0
    return ValidationResult(passed=passed, failures=failures, scores=scores)
