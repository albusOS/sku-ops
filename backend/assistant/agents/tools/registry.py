"""Canonical tool registry — single source of truth for all agent tool functions.

Every tool that agents, DAG, and workflows can invoke is registered here once.
Consumers resolve tools by canonical name.
"""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

ToolFn = Callable[..., Awaitable[str]]


@dataclass(frozen=True)
class ToolEntry:
    name: str
    domain: str
    fn: ToolFn
    use_cases: list[str] = field(default_factory=list)


_TOOLS: dict[str, ToolEntry] = {}


def register(
    name: str,
    domain: str,
    fn: ToolFn,
    *,
    use_cases: list[str] | None = None,
    **_kwargs: object,
) -> None:
    """Register a tool. Called at import time by each agent package."""
    entry = ToolEntry(name=name, domain=domain, fn=fn, use_cases=use_cases or [])
    _TOOLS[name] = entry


def get(name: str) -> ToolEntry | None:
    """Look up a tool by its canonical name (e.g. 'search_skus')."""
    return _TOOLS.get(name)


def all_tools() -> dict[str, ToolEntry]:
    """Return the full registry (read-only snapshot)."""
    return dict(_TOOLS)


def names_for_domain(domain: str) -> set[str]:
    """Return canonical names of all tools in a domain."""
    return {e.name for e in _TOOLS.values() if e.domain == domain}


async def run_tool(name: str, args: dict) -> str:
    """Execute a tool by canonical name. Used by DAG executor and assistant.

    Introspects function signature to pass kwargs for typed functions,
    or falls back to passing the dict directly for legacy functions.
    """
    entry = _TOOLS.get(name)
    if not entry:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        sig = inspect.signature(entry.fn)
        params = list(sig.parameters.keys())
        if not params:
            result = await entry.fn()
        elif len(params) == 1 and params[0] == "args":
            result = await entry.fn(args)
        else:
            kwargs = {k: v for k, v in args.items() if k in sig.parameters}
            result = await entry.fn(**kwargs)
        return result if isinstance(result, str) else str(result)
    except Exception as e:
        logger.warning("Tool %s failed: %s", name, e)
        return json.dumps({"error": str(e)})


def init_tools() -> None:
    """Import agent tool modules so they self-register. Call once at startup."""
    if _TOOLS:
        return
    import assistant.agents.finance.analytics_tools
    import assistant.agents.finance.tools
    import assistant.agents.inventory.tools
    import assistant.agents.ops.tools
    import assistant.agents.purchasing.tools  # noqa: F401
