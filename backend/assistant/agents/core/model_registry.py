"""Model registry — maps task types to models.

Resolution order (first non-empty wins):
  1. Environment variable: MODEL_REGISTRY_<TASK_KEY>
  2. Per-agent config.yaml `model` field
  3. Global defaults from models.yaml (AGENT_PRIMARY_MODEL / INFRA_SYNTHESIS_MODEL)

Env-var overrides still work:
    MODEL_REGISTRY_AGENT_INVENTORY=anthropic:claude-opus-4-6
"""

from __future__ import annotations

import logging
import os

from assistant.infrastructure.llm.cost import calc_cost as _cost_calc
from shared.infrastructure.config import (
    AGENT_PRIMARY_MODEL,
    INFRA_CLASSIFIER_MODEL,
    INFRA_SYNTHESIS_MODEL,
)

logger = logging.getLogger(__name__)

_TASK_TO_AGENT_ID: dict[str, str] = {
    "agent:unified": "unified",
    "agent:analyst": "analyst",
    "agent:trend": "trend_analyst",
    "agent:health": "health_analyst",
    "agent:procurement": "procurement_analyst",
    "agent:product_analyst": "product_analyst",
}

_DEFAULTS: dict[str, str] = {
    "agent:unified": AGENT_PRIMARY_MODEL,
    "agent:analyst": AGENT_PRIMARY_MODEL,
    "agent:trend": AGENT_PRIMARY_MODEL,
    "agent:health": AGENT_PRIMARY_MODEL,
    "agent:procurement": AGENT_PRIMARY_MODEL,
    "agent:product_analyst": AGENT_PRIMARY_MODEL,
    # Reserved task keys for agents not yet implemented.
    # They resolve to AGENT_PRIMARY_MODEL via the fallback in _resolve(),
    # so they are safe to call but produce no config.yaml override benefit.
    # Add a config.yaml + _TASK_TO_AGENT_ID entry when the agent is built.
    "agent:inventory": AGENT_PRIMARY_MODEL,
    "agent:ops": AGENT_PRIMARY_MODEL,
    "agent:finance": AGENT_PRIMARY_MODEL,
    "infra:synthesis": INFRA_SYNTHESIS_MODEL,
    "infra:classifier": INFRA_CLASSIFIER_MODEL,
}


def _resolve(task: str) -> str:
    """Return the model identifier for *task*.

    Checks env override -> per-agent config.yaml -> global default.
    """
    env_key = "MODEL_REGISTRY_" + task.replace(":", "_").replace(".", "_").upper()
    override = os.environ.get(env_key, "").strip()
    if override:
        return override

    agent_id = _TASK_TO_AGENT_ID.get(task)
    if agent_id:
        from assistant.agents.core.config import load_agent_config

        cfg = load_agent_config(agent_id)
        if cfg.model:
            return cfg.model

    return _DEFAULTS.get(task, AGENT_PRIMARY_MODEL)


def get_model_name(task: str) -> str:
    """Return a PydanticAI-compatible model identifier string for a task."""
    return _resolve(task)


def get_model(task: str) -> str:
    """Return a PydanticAI-compatible model string for *task*.

    In test mode, the llm package prefixes with 'test:' automatically.
    At runtime, PydanticAI resolves 'anthropic:*', 'openrouter:*', etc. natively.
    """
    from assistant.infrastructure.llm import get_model as _llm_get_model

    return _llm_get_model(get_model_name(task))


def get_fallback_model(model_id: str) -> str | None:
    """Return an OpenRouter fallback for an Anthropic model, or None.

    When Anthropic's API is overloaded, we can route through OpenRouter
    to reach the same model via a different path. Only applies when
    OpenRouter is configured and the original model is an Anthropic one.
    """
    from shared.infrastructure.config import OPENROUTER_AVAILABLE

    if not OPENROUTER_AVAILABLE:
        return None
    if not model_id.startswith("anthropic:"):
        return None
    bare = model_id.removeprefix("anthropic:")
    fallback = f"openrouter:anthropic/{bare}"
    logger.info("Falling back from %s to %s", model_id, fallback)
    return fallback


def calc_cost(task_or_model: str, usage) -> float:
    """Estimate cost in USD from a PydanticAI Usage object."""
    model = _resolve(task_or_model) if ":" in task_or_model else task_or_model
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    try:
        return _cost_calc(model, inp, out)
    except (RuntimeError, ValueError, TypeError, KeyError, AttributeError):
        return 0.0
