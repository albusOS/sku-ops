"""Model catalog — loads catalog.yaml and exposes tier/pricing lookups.

The catalog is loaded once and cached.  All pricing and tier resolution
flows through here so the rest of the codebase never hard-codes model names
or prices.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).parent / "catalog.yaml"


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    with open(_CATALOG_PATH) as f:
        return yaml.safe_load(f) or {}


def get_tiers() -> dict[str, dict]:
    """Return all tier definitions."""
    return _load_catalog().get("tiers", {})


def get_tier(tier_name: str) -> dict | None:
    """Return a single tier definition, or None."""
    return get_tiers().get(tier_name)


def get_models() -> dict[str, dict]:
    """Return all model definitions."""
    return _load_catalog().get("models", {})


def get_model_info(model_id: str) -> dict | None:
    """Return full model info for *model_id*, or None if unknown."""
    models = get_models()
    info = models.get(model_id)
    if info:
        return info
    bare = _strip_prefix(model_id)
    if bare != model_id:
        return models.get(bare)
    for key, val in models.items():
        if bare in key or key in bare:
            return val
    return None


def get_model_pricing(model_id: str) -> dict[str, float] | None:
    """Return {"input_price_per_m": ..., "output_price_per_m": ...} or None."""
    info = get_model_info(model_id)
    if not info:
        return None
    inp = info.get("input_price_per_m")
    out = info.get("output_price_per_m")
    if inp is None or out is None:
        return None
    return {"input_price_per_m": float(inp), "output_price_per_m": float(out)}


def resolve_tier_model(tier_name: str) -> str | None:
    """Return the default model_id for a tier.

    Checks env override: LLM_TIER_<NAME>_MODEL=<model_id>
    """
    env_key = f"LLM_TIER_{tier_name.upper()}_MODEL"
    override = os.environ.get(env_key, "").strip()
    if override:
        return override
    tier = get_tier(tier_name)
    if not tier:
        return None
    return tier.get("default_model")


def tier_max_output_tokens(tier_name: str) -> int:
    """Return the max_output_tokens for a tier, or 4000 as fallback."""
    tier = get_tier(tier_name)
    if not tier:
        return 4000
    return tier.get("max_output_tokens", 4000)


def _strip_prefix(model_id: str) -> str:
    """'anthropic:claude-sonnet-4-6' or 'anthropic/claude-...' -> normalized."""
    if model_id.startswith(("anthropic:", "openai:")):
        return model_id.split(":", 1)[1]
    return model_id
