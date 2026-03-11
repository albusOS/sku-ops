"""Assistant application queries — safe for cross-context import.

API and other bounded contexts import from here, never from assistant.infrastructure directly.
Thin delegation layer that decouples consumers from infrastructure details.
"""

from assistant.infrastructure.agent_run_repo import (
    get_cost_breakdown,
    get_session_trace,
    get_stats,
    list_runs,
)

__all__ = [
    "get_cost_breakdown",
    "get_session_trace",
    "get_stats",
    "list_runs",
]
