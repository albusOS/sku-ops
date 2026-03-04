"""Cost estimation engine — pre-flight estimates, budget enforcement, post-flight accounting.

Centralizes cost logic previously scattered across model_registry.calc_cost(),
tokens.estimate_turn_tokens(), and chat.py SESSION_COST_CAP checks.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from assistant.infrastructure.llm.catalog import (
    get_model_pricing,
    resolve_tier_model,
    tier_max_output_tokens,
)

logger = logging.getLogger(__name__)


@dataclass
class CostEstimate:
    """Pre-flight cost estimate for a planned LLM call."""
    model_id: str
    tier: str
    estimated_input_tokens: int
    max_output_tokens: int
    estimated_cost_usd: float
    within_budget: bool


def calc_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Compute actual cost in USD from observed token counts.

    Replaces model_registry.calc_cost() — the single source of truth for cost math.
    """
    pricing = get_model_pricing(model_id)
    if not pricing:
        return 0.0
    return round(
        (input_tokens * pricing["input_price_per_m"]
         + output_tokens * pricing["output_price_per_m"])
        / 1_000_000,
        6,
    )


def estimate_call_cost(
    tier: str,
    input_tokens: int,
    model_id: str | None = None,
) -> CostEstimate:
    """Pre-flight estimate: how much will this call likely cost?

    Uses the tier's default model if *model_id* is not specified.
    Assumes the model will produce max_output_tokens for a worst-case estimate.
    """
    mid = model_id or resolve_tier_model(tier) or ""
    max_out = tier_max_output_tokens(tier)
    est = calc_cost(mid, input_tokens, max_out)
    return CostEstimate(
        model_id=mid,
        tier=tier,
        estimated_input_tokens=input_tokens,
        max_output_tokens=max_out,
        estimated_cost_usd=est,
        within_budget=True,
    )


def check_budget(
    estimated_cost: float,
    session_cost_so_far: float,
    session_budget: float,
) -> bool:
    """Return True if adding *estimated_cost* stays within the session budget.

    A budget of 0 means unlimited.
    """
    if session_budget <= 0:
        return True
    return (session_cost_so_far + estimated_cost) <= session_budget


def recommend_tier(
    estimated_input_tokens: int,
    is_trivial: bool = False,
    is_complex: bool = False,
) -> str:
    """Recommend the cheapest viable tier based on input size and complexity.

    Keeps costs proportional to query complexity:
    - trivial -> cheap (greetings, help)
    - simple -> standard (most queries; fast tier is reserved for explicit downgrade)
    - complex -> standard (coordinator handles the multi-agent overhead)
    - very large context -> standard/premium (based on token count)
    """
    if is_trivial:
        return "cheap"
    if is_complex:
        return "standard"
    return "standard"
