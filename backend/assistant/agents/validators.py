"""Structured response validators — deterministic quality checks (no LLM calls).

Replaces the Haiku-based reflect_on_response with fast, testable assertions
that check tool coverage, data grounding, format compliance, and token efficiency.
"""
import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    should_rerun: bool = False
    rerun_hint: str = ""


# ── Words that signal a data question (expect tool calls) ────────────────────
_DATA_SIGNALS = frozenset((
    "how many", "how much", "show me", "list", "what", "which",
    "search", "find", "lookup", "look up", "do we have",
    "stock", "inventory", "revenue", "balance", "outstanding",
    "forecast", "trend", "top", "low stock", "reorder",
    "withdrawal", "request", "contractor", "job", "department",
    "invoice", "payment", "p&l", "profit", "margin", "vendor",
))

_TRIVIAL_SIGNALS = frozenset((
    "hi", "hello", "hey", "thanks", "thank you", "help", "ok", "okay",
    "sure", "yes", "no", "bye", "goodbye",
))

_NUMBER_RE = re.compile(r"\b\d[\d,]*\.?\d*\b")


def _is_data_question(msg: str) -> bool:
    m = msg.lower().strip()
    if len(m) < 10:
        return False
    if any(w in m for w in _TRIVIAL_SIGNALS):
        return False
    return any(w in m for w in _DATA_SIGNALS)


def _extract_numbers(text: str) -> set[str]:
    """Extract numeric strings from text for grounding checks."""
    return set(_NUMBER_RE.findall(text))


def _numbers_from_tool_results(tool_calls_detailed: list[dict]) -> set[str]:
    """Extract numbers that appear in tool return data."""
    nums: set[str] = set()
    for tc in tool_calls_detailed:
        preview = tc.get("result_preview", "")
        if preview:
            nums |= _extract_numbers(preview)
    return nums


def validate_response(
    user_message: str,
    response_text: str,
    tool_calls: list[dict],
    tool_calls_detailed: list[dict],
) -> ValidationResult:
    """Run all deterministic validators. Returns a ValidationResult."""
    failures: list[str] = []
    scores: dict[str, float] = {}

    # ── Skip validation for trivial interactions ──────────────────────────
    m = user_message.lower().strip()
    if len(m) < 10 or any(w in m for w in _TRIVIAL_SIGNALS):
        return ValidationResult(passed=True, scores={"trivial": 1.0})

    if not response_text or len(response_text) < 10:
        return ValidationResult(passed=True, scores={"empty_response": 0.0})

    # ── 1. Tool coverage: data question should have tool calls ────────────
    is_data_q = _is_data_question(user_message)
    if is_data_q and not tool_calls:
        failures.append("no_tools_called")
        scores["tool_coverage"] = 0.0
    else:
        scores["tool_coverage"] = 1.0

    # ── 2. Data grounding: numbers in response should come from tools ─────
    if tool_calls_detailed:
        resp_nums = _extract_numbers(response_text)
        tool_nums = _numbers_from_tool_results(tool_calls_detailed)
        if resp_nums and tool_nums:
            grounded = resp_nums & tool_nums
            grounding_ratio = len(grounded) / len(resp_nums) if resp_nums else 1.0
            scores["data_grounding"] = round(grounding_ratio, 2)
            # Only flag if more than half the numbers are ungrounded
            if grounding_ratio < 0.5 and len(resp_nums) > 2:
                ungrounded = resp_nums - tool_nums
                failures.append(f"ungrounded_numbers:{len(ungrounded)}")
        else:
            scores["data_grounding"] = 1.0
    else:
        scores["data_grounding"] = 1.0

    # ── 3. Format compliance: tables for list data ────────────────────────
    has_table = "|" in response_text and "---" in response_text
    list_keywords = ("top", "list", "all", "show me", "ranking", "forecast")
    expects_table = any(k in m for k in list_keywords) and is_data_q
    if expects_table and not has_table and len(response_text) > 200:
        scores["format_compliance"] = 0.5
    else:
        scores["format_compliance"] = 1.0

    # ── 4. Token efficiency (basic) ───────────────────────────────────────
    resp_len = len(response_text)
    if resp_len > 5000 and len(m) < 50:
        scores["token_efficiency"] = 0.5
    elif resp_len > 3000 and len(m) < 30:
        scores["token_efficiency"] = 0.6
    else:
        scores["token_efficiency"] = 1.0

    # ── 5. UOM compliance: no bare "units" in inventory context ───────────
    inv_words = ("stock", "inventory", "product", "reorder", "department", "sku")
    if any(w in m for w in inv_words):
        bare_units = bool(re.search(r"\b\d+\s+units?\b", response_text, re.IGNORECASE))
        if bare_units:
            scores["uom_compliance"] = 0.3
        else:
            scores["uom_compliance"] = 1.0

    # ── Decide whether to re-run ──────────────────────────────────────────
    should_rerun = False
    rerun_hint = ""

    if "no_tools_called" in failures:
        should_rerun = True
        rerun_hint = (
            "Your initial response did not use any tools. This question requires "
            "data from the database. Please use the appropriate tool(s) to fetch "
            "real data before answering."
        )
    elif any(f.startswith("ungrounded_numbers") for f in failures):
        should_rerun = True
        rerun_hint = (
            "Some numbers in your response could not be verified against tool results. "
            "Please only use data returned by your tools — do not estimate or fabricate numbers."
        )

    passed = len(failures) == 0
    return ValidationResult(
        passed=passed,
        failures=failures,
        scores=scores,
        should_rerun=should_rerun,
        rerun_hint=rerun_hint,
    )
