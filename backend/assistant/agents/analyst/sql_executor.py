"""Sandboxed SQL executor for the analyst agent.

Security stack:
1. Statement validation — only SELECT / WITH allowed (RawSQLService, read_only)
2. Forbidden pattern rejection — DDL, DML, COPY, multi-statement
3. Org isolation — :org_id required, org_id injected
4. statement_timeout — 10s cap prevents runaway queries
5. Row limit — 500 rows max per query
6. Audit logging — every query logged with org, user, duration
"""

from __future__ import annotations

import json
import logging
import re
import time

from shared.infrastructure.db import get_org_id, get_user_id
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.services._sql_validation import SQLValidationError
from shared.infrastructure.db.services.raw_sql import ExecutionResult

logger = logging.getLogger(__name__)

MAX_ROWS = 500
TIMEOUT_MS = 10_000


class AnalystQueryError(Exception):
    """Raised when a query violates sandbox constraints."""


def _validate_org_filter(sql: str) -> None:
    """Ensure the query references org scoping (:org_id or legacy ``$1``)."""
    if ":org_id" not in sql and re.search(r"\$1\b", sql) is None:
        raise AnalystQueryError(
            "Query must include organization_id = :org_id (or legacy $1) for org "
            "isolation. Add WHERE organization_id = :org_id to your query."
        )


async def execute_sandboxed(sql: str) -> ExecutionResult:
    """Execute a read-only SQL query with full security stack.

    The query MUST contain :org_id or $1 as the organization_id placeholder.
    The ambient org_id (from auth middleware) is injected automatically.
    """
    org_id = get_org_id()
    if not org_id:
        raise AnalystQueryError(
            "No organization context. Cannot execute analyst query."
        )

    _validate_org_filter(sql)
    sql_named = re.sub(r"\$1\b", ":org_id", sql)

    t0 = time.monotonic()
    db = get_database_manager()
    try:
        result = await db.sql.execute(
            sql_named,
            {"org_id": org_id},
            read_only=True,
            timeout_ms=TIMEOUT_MS,
            max_rows=MAX_ROWS,
        )
    except SQLValidationError as e:
        raise AnalystQueryError(str(e)) from e
    except Exception as e:
        duration_ms = int((time.monotonic() - t0) * 1000)
        _log_query(sql_named, org_id, duration_ms, error=str(e))
        err_msg = str(e)
        if "canceling statement due to statement timeout" in err_msg:
            raise AnalystQueryError(
                "Query timed out (10s limit). Try a more targeted query "
                "with tighter filters or fewer joins."
            ) from e
        raise AnalystQueryError(f"Query execution error: {err_msg}") from e

    _log_query(
        sql_named, org_id, result.duration_ms, row_count=len(result.rows)
    )
    return ExecutionResult(
        columns=result.columns,
        rows=result.rows[:MAX_ROWS],
        row_count=result.row_count,
        truncated=result.truncated,
        duration_ms=result.duration_ms,
    )


def format_result(result: ExecutionResult) -> str:
    """Format an ExecutionResult as a JSON string for the LLM."""
    serializable_rows = []
    for row in result.rows:
        clean = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                clean[k] = v.isoformat()
            elif isinstance(v, (int, float, str, bool, type(None))):
                clean[k] = v
            else:
                clean[k] = str(v)
        serializable_rows.append(clean)

    payload = {
        "columns": result.columns,
        "rows": serializable_rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
        "duration_ms": result.duration_ms,
    }
    return json.dumps(payload, default=str)


def _log_query(
    sql: str,
    org_id: str,
    duration_ms: int,
    *,
    row_count: int = 0,
    error: str = "",
) -> None:
    extra = {
        "org_id": org_id,
        "user_id": get_user_id(),
        "duration_ms": duration_ms,
        "row_count": row_count,
        "action": "analyst_sql",
    }
    if error:
        extra["error"] = error[:500]
        logger.warning("analyst_query_failed sql=%s", sql[:200], extra=extra)
    else:
        logger.info("analyst_query sql=%s", sql[:200], extra=extra)
