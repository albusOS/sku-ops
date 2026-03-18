"""Tool descriptors for unified agent — auto-generated from the tool registry.

Each tool's docstring becomes its description. Use cases come from the
registry's use_cases metadata. No manual maintenance required.
"""

from __future__ import annotations

from dataclasses import dataclass

from assistant.agents.tools.registry import all_tools, init_tools


@dataclass
class ToolDescriptor:
    """Structured descriptor for embedding and retrieval."""

    name: str
    description: str
    use_cases: list[str]


def get_unified_tool_descriptors() -> dict[str, ToolDescriptor]:
    """Return descriptors for all registered tools, derived from registry metadata."""
    init_tools()
    descriptors: dict[str, ToolDescriptor] = {}
    for name, entry in all_tools().items():
        doc = (entry.fn.__doc__ or "").strip().split("\n")[0]
        descriptors[name] = ToolDescriptor(
            name=name,
            description=doc,
            use_cases=entry.use_cases,
        )
    return descriptors
