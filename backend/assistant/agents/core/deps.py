"""Shared dependency type injected into all agent tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from assistant.agents.core.contracts import AgentConfig


@dataclass
class AgentDeps:
    user_id: str
    user_name: str
    config: AgentConfig | None = None
    trace_id: str = field(default="")
    blocks: list[dict[str, Any]] = field(default_factory=list)
    query_results: dict[str, Any] = field(default_factory=dict)
