"""Model registry — maps task types to models.

Thin wrapper over the LLM infrastructure package.  Maintains the same public
API (get_model, get_model_name, calc_cost) so existing agent code is unchanged.

The _DEFAULTS dict provides task-to-model mappings that will eventually be
replaced by per-agent YAML configs (Phase 1).  Env-var overrides still work:
    MODEL_REGISTRY_AGENT_INVENTORY=anthropic/claude-opus-4-6
"""
from __future__ import annotations

import logging
import os

from shared.infrastructure.config import AGENT_PRIMARY_MODEL

logger = logging.getLogger(__name__)

# ── Per-task model assignments ────────────────────────────────────────────────
# These will be replaced by agent YAML configs in Phase 1.  For now they serve
# as the mapping layer between task keys and model identifiers.

_DEFAULTS: dict[str, str] = {
    "agent:inventory":  "anthropic/claude-sonnet-4-6",
    "agent:ops":        "anthropic/claude-sonnet-4-6",
    "agent:finance":    "anthropic/claude-sonnet-4-6",
    "agent:insights":   "anthropic/claude-sonnet-4-6",
    "agent:general":    "anthropic/claude-sonnet-4-6",
    "agent:coordinator": "anthropic/claude-sonnet-4-6",

    "infra:router_fallback": "meta-llama/llama-3.3-70b-instruct",
    "infra:merge_fallback":  "meta-llama/llama-3.3-70b-instruct",
    "infra:synthesis":       "meta-llama/llama-3.3-70b-instruct",

    "eval:judge": "anthropic/claude-sonnet-4-6",
}


def _resolve(task: str) -> str:
    """Return the model identifier for *task*, checking env overrides first."""
    env_key = "MODEL_REGISTRY_" + task.replace(":", "_").replace(".", "_").upper()
    override = os.environ.get(env_key, "").strip()
    if override:
        return override
    return _DEFAULTS.get(task, _DEFAULTS["agent:general"])


def get_model_name(task: str) -> str:
    """Return the raw model identifier string for a task."""
    return _resolve(task)


def get_model(task: str):
    """Return a PydanticAI-compatible model for *task*.

    Delegates to the LLM infrastructure provider.  Falls back to the legacy
    direct-construction path if init_llm() has not been called (e.g. during
    imports before startup).
    """
    model_name = _resolve(task)
    try:
        from assistant.infrastructure.llm import get_model as llm_get_model
        return llm_get_model(model_name)
    except RuntimeError:
        logger.debug("LLM provider not yet initialized, using AGENT_PRIMARY_MODEL fallback")
        return AGENT_PRIMARY_MODEL


def calc_cost(task_or_model: str, usage) -> float:
    """Estimate cost in USD from a PydanticAI Usage object.

    Delegates to the LLM cost engine.  Accepts either a task key
    ("agent:inventory") or a raw model name ("anthropic/claude-sonnet-4-6").
    """
    model = _resolve(task_or_model) if ":" in task_or_model else task_or_model
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    try:
        from assistant.infrastructure.llm.cost import calc_cost as cost_calc
        return cost_calc(model, inp, out)
    except Exception:
        return 0.0
