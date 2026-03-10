"""Agent config loading — resolves YAML + env-var overrides to AgentConfig objects."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

from assistant.agents.core.contracts import AgentConfig, RetryConfig

_AGENTS_DIR = Path(__file__).parent.parent


def _apply_env_overrides(agent_id: str, data: dict) -> dict:
    """Check for env-var overrides: AGENT_CONFIG_<ID>_<FIELD>=value."""
    prefix = f"AGENT_CONFIG_{agent_id.upper()}_"
    for key, value in os.environ.items():
        if key.startswith(prefix):
            field_name = key[len(prefix) :].lower()
            if field_name == "max_output_tokens":
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
        tools=data.get("tools", []),
        max_output_tokens=data.get("max_output_tokens", 4000),
        temperature=data.get("temperature", 0.0),
        retry=retry,
    )


def get_all_configs() -> dict[str, AgentConfig]:
    """Load all agent configs by scanning for agent package directories with config.yaml."""
    configs: dict[str, AgentConfig] = {}
    for child in _AGENTS_DIR.iterdir():
        if child.is_dir() and (child / "config.yaml").exists():
            agent_id = child.name
            configs[agent_id] = load_agent_config(agent_id)
    return configs
