"""Agent contracts — typed models for the multi-agent system.

Defines the interfaces that agents, the orchestrator, and the router all share.
Pure data models with no side effects; safe to import anywhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


# ── Enums ─────────────────────────────────────────────────────────────────────

class Complexity(str, Enum):
    """Query complexity tier — drives cost-proportional execution."""
    TRIVIAL = "trivial"
    STRUCTURED = "structured"
    SIMPLE = "simple"
    COMPLEX = "complex"


class Tier(str, Enum):
    """Model quality/cost tier — agents reference a tier, not a specific model."""
    CHEAP = "cheap"
    FAST = "fast"
    STANDARD = "standard"
    PREMIUM = "premium"


# ── Agent configuration ───────────────────────────────────────────────────────

@dataclass
class RetryConfig:
    max_retries: int = 3
    timeout_seconds: int = 45
    backoff_base: float = 1.0


@dataclass
class AgentConfig:
    """Declarative agent definition — loaded from YAML, one per agent."""
    id: str
    description: str = ""
    domains: list[str] = field(default_factory=list)
    can_delegate_to: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    tier: str = "standard"
    thinking_budget: int = 0
    max_output_tokens: int = 4000
    temperature: float = 0.0
    retry: RetryConfig = field(default_factory=RetryConfig)
    system_prompt_file: str = ""
    canonical_queries: list[str] = field(default_factory=list)


# ── Agent result types ────────────────────────────────────────────────────────

@dataclass
class UsageInfo:
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    tier: str = ""


@dataclass
class HandoffRequest:
    """An agent's request to delegate to another specialist."""
    source_agent: str
    target_agent: str
    reason: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    partial_result: str = ""


@dataclass
class AgentResult:
    """Typed output from any agent run — replaces raw dict returns."""
    agent: str
    response: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_calls_detailed: list[dict] = field(default_factory=list)
    thinking: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    usage: UsageInfo = field(default_factory=UsageInfo)
    confidence: float = 1.0
    needs_handoff: HandoffRequest | None = None
    validation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to the dict shape expected by the API layer / frontend."""
        result: dict[str, Any] = {
            "response": self.response,
            "tool_calls": self.tool_calls,
            "thinking": self.thinking,
            "history": self.history,
            "agent": self.agent,
            "usage": {
                "cost_usd": self.usage.cost_usd,
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "model": self.usage.model,
            },
        }
        if self.validation is not None:
            result["validation"] = self.validation
        return result


# ── Routing and orchestration state ────────────────────────────────────────────

@dataclass
class RouteDecision:
    """Enriched routing decision with strategy and complexity awareness."""
    primary: str
    supporting: list[str] = field(default_factory=list)
    strategy: str = "single"       # single | parallel | coordinate | dag
    complexity: Complexity = Complexity.SIMPLE
    confidence: float = 1.0
    method: str = "heuristic"
    dag_template: str | None = None
    estimated_cost: float = 0.0


@dataclass
class TurnState:
    """Full state for one orchestration turn — flows through the dispatch loop."""
    trace_id: str
    query: str
    session_id: str
    complexity: Complexity
    route: RouteDecision | None = None
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    handoff_chain: list[str] = field(default_factory=list)
    total_cost: float = 0.0
    iteration: int = 0
    max_iterations: int = 3


# ── Config loading ────────────────────────────────────────────────────────────
# Each agent has its own package directory with a config.yaml:
#   agents/{agent_id}/config.yaml

_AGENTS_DIR = Path(__file__).parent


def _apply_env_overrides(agent_id: str, data: dict) -> dict:
    """Check for env-var overrides: AGENT_CONFIG_<ID>_<FIELD>=value."""
    prefix = f"AGENT_CONFIG_{agent_id.upper()}_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            field_name = key[len(prefix):].lower()
            if field_name == "tier":
                data["tier"] = value.strip()
            elif field_name == "thinking_budget":
                data["thinking_budget"] = int(value.strip())
            elif field_name == "max_output_tokens":
                data["max_output_tokens"] = int(value.strip())
            elif field_name == "temperature":
                data["temperature"] = float(value.strip())
    return data


def load_agent_config(agent_id: str) -> AgentConfig:
    """Load an agent's config from its package config.yaml with env-var overrides."""
    return _load_cached(agent_id)


@lru_cache(maxsize=32)
def _load_cached(agent_id: str) -> AgentConfig:
    yaml_path = _AGENTS_DIR / agent_id / "config.yaml"
    if not yaml_path.exists():
        return AgentConfig(id=agent_id)

    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}

    data = _apply_env_overrides(agent_id, data)

    retry_data = data.pop("retry", {})
    retry = RetryConfig(
        max_retries=retry_data.get("max_retries", 3),
        timeout_seconds=retry_data.get("timeout_seconds", 45),
        backoff_base=retry_data.get("backoff_base", 1.0),
    )

    return AgentConfig(
        id=data.get("id", agent_id),
        description=data.get("description", ""),
        domains=data.get("domains", []),
        can_delegate_to=data.get("can_delegate_to", []),
        tools=data.get("tools", []),
        tier=data.get("tier", "standard"),
        thinking_budget=data.get("thinking_budget", 0),
        max_output_tokens=data.get("max_output_tokens", 4000),
        temperature=data.get("temperature", 0.0),
        retry=retry,
        system_prompt_file=data.get("system_prompt_file", ""),
        canonical_queries=data.get("canonical_queries", []),
    )


def get_all_configs() -> dict[str, AgentConfig]:
    """Load all agent configs by scanning for agent package directories with config.yaml."""
    configs: dict[str, AgentConfig] = {}
    for child in _AGENTS_DIR.iterdir():
        if child.is_dir() and (child / "config.yaml").exists():
            agent_id = child.name
            configs[agent_id] = load_agent_config(agent_id)
    return configs
