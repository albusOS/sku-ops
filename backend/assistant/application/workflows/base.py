"""Workflow base primitives — parallel fetch and direct formatting.

Shared by fixed DAG workflows. No workflow-specific logic.

Workflows return structured data formatted by a deterministic fallback
function.  The calling agent (which is already an LLM) interprets and
presents the data to the user — adding a second LLM "synthesis" call
in the workflow was doubling latency for marginal quality gain.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from assistant.agents.tools.registry import init_tools, run_tool

if TYPE_CHECKING:
    from collections.abc import Callable

    from assistant.application.workflows.types import FetchSpec

logger = logging.getLogger(__name__)


def _is_json(s: str) -> bool:
    s = (s or "").strip()
    return s.startswith(("{", "["))


async def run_parallel_fetch(specs: list[FetchSpec]) -> dict:
    """Fetch multiple tools in parallel and return aggregated dict keyed by result_key.

    Calls init_tools(), runs each spec via run_tool(), parses JSON responses,
    and assembles into a dict. Non-JSON responses become {}.
    """
    init_tools()
    tasks = [run_tool(s.tool_name, s.args) for s in specs]
    results = await asyncio.gather(*tasks)
    out: dict = {}
    for spec, raw in zip(specs, results, strict=False):
        if _is_json(raw):
            try:
                out[spec.result_key] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                out[spec.result_key] = {}
        else:
            out[spec.result_key] = {}
    return out


def format_workflow_result(
    data: dict,
    format_fn: Callable[[dict], str],
) -> str:
    """Format workflow data using a deterministic formatter.

    No LLM call — the calling agent already has the context to interpret
    the data and will present it to the user.
    """
    return format_fn(data)
