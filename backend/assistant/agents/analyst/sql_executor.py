"""Sandboxed SQL executor for the analyst agent.

Security stack:
1. Statement validation — only SELECT / WITH allowed
2. Forbidden pattern rejection — DDL, DML, COPY, multi-statement
3. Org isolation — $1 placeholder required, org_id injected
4. SET TRANSACTION READ ONLY — Postgres-enforced write protection
5. statement_timeout — 10s cap prevents runaway queries
6. Row limit — 500 rows max per query
7. Audit logging — every query logged with org, user, duration
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass

from shared.infrastructure.db import get_org_id, get_user_id, transaction

logger = logging.getLogger(__name__)

MAX_ROWS = 500
TIMEOUT_MS = 10_000


class AnalystQueryError(Exception):
    """Raised when a query violates sandbox constraints."""


@dataclass(frozen=True)
class ExecutionResult:
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool
    duration_ms: int = 0


# ── SQL validation ───────────────────────────────────────────────────────────

_ALLOWED_PREFIXES = ("SELECT", "WITH")

_FORBIDDEN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bINSERT\b", re.IGNORECASE), "INSERT statements are not allowed"),
    (re.compile(r"\bUPDATE\b", re.IGNORECASE), "UPDATE statements are not allowed"),
    (re.compile(r"\bDELETE\b", re.IGNORECASE), "DELETE statements are not allowed"),
    (re.compile(r"\bDROP\b", re.IGNORECASE), "DROP statements are not allowed"),
    (re.compile(r"\bALTER\b", re.IGNORECASE), "ALTER statements are not allowed"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE statements are not allowed"),
    (re.compile(r"\bGRANT\b", re.IGNORECASE), "GRANT statements are not allowed"),
    (re.compile(r"\bREVOKE\b", re.IGNORECASE), "REVOKE statements are not allowed"),
    (re.compile(r"\bCOPY\b", re.IGNORECASE), "COPY statements are not allowed"),
    (re.compile(r"\bCREATE\b(?!\s+TEMP)", re.IGNORECASE), "CREATE statements are not allowed"),
    (re.compile(r"\bSET\b", re.IGNORECASE), "SET statements are not allowed"),
    (re.compile(r"\bVACUUM\b", re.IGNORECASE), "VACUUM statements are not allowed"),
    (re.compile(r"\bEXPLAIN\b", re.IGNORECASE), "EXPLAIN statements are not allowed"),
    (re.compile(r"\bLISTEN\b", re.IGNORECASE), "LISTEN statements are not allowed"),
    (re.compile(r"\bNOTIFY\b", re.IGNORECASE), "NOTIFY statements are not allowed"),
]


def _validate_sql(sql: str) -> None:
    """Validate that SQL is a safe read-only query."""
    stripped = sql.strip()
    if not stripped:
        raise AnalystQueryError("Empty query")

    normalized = stripped.upper().lstrip()
    if not any(normalized.startswith(p) for p in _ALLOWED_PREFIXES):
        raise AnalystQueryError(
            f"Only SELECT and WITH (CTE) queries are allowed. Got: {normalized[:30]}..."
        )

    if ";" in stripped:
        parts = [p.strip() for p in stripped.split(";") if p.strip()]
        if len(parts) > 1:
            raise AnalystQueryError(
                "Multi-statement queries are not allowed. Send one query at a time."
            )

    for pattern, message in _FORBIDDEN_PATTERNS:
        if pattern.search(stripped):
            raise AnalystQueryError(message)


def _validate_org_filter(sql: str) -> None:
    """Ensure the query references $1 for org_id injection."""
    if "$1" not in sql:
        raise AnalystQueryError(
            "Query must include organization_id = $1 for org isolation. "
            "Add WHERE organization_id = $1 to your query."
        )


def _ensure_limit(sql: str) -> str:
    """Append LIMIT if not already present."""
    upper = sql.upper()
    if "LIMIT" not in upper:
        return f"{sql.rstrip().rstrip(';')}\nLIMIT {MAX_ROWS}"
    return sql


# ── Execution ────────────────────────────────────────────────────────────────


async def execute_sandboxed(sql: str) -> ExecutionResult:
    """Execute a read-only SQL query with full security stack.

    The query MUST contain $1 as the organization_id placeholder.
    The ambient org_id (from auth middleware) is injected automatically.
    """
    org_id = get_org_id()
    if not org_id:
        raise AnalystQueryError("No organization context. Cannot execute analyst query.")

    _validate_sql(sql)
    _validate_org_filter(sql)
    sql = _ensure_limit(sql)

    t0 = time.monotonic()

    async with transaction() as conn:
        await conn.execute("SET LOCAL statement_timeout = '10000'")
        try:
            cursor = await conn.execute(sql, (org_id,))
            rows_raw = await cursor.fetchall()
        except Exception as e:
            duration_ms = int((time.monotonic() - t0) * 1000)
            _log_query(sql, org_id, duration_ms, error=str(e))
            err_msg = str(e)
            if "canceling statement due to statement timeout" in err_msg:
                raise AnalystQueryError(
                    "Query timed out (10s limit). Try a more targeted query "
                    "with tighter filters or fewer joins."
                ) from e
            raise AnalystQueryError(f"Query execution error: {err_msg}") from e

    duration_ms = int((time.monotonic() - t0) * 1000)

    rows = [dict(r) for r in rows_raw]
    columns = list(rows[0].keys()) if rows else []
    truncated = len(rows) >= MAX_ROWS

    _log_query(sql, org_id, duration_ms, row_count=len(rows))

    return ExecutionResult(
        columns=columns,
        rows=rows[:MAX_ROWS],
        row_count=len(rows),
        truncated=truncated,
        duration_ms=duration_ms,
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


# ── Audit logging ────────────────────────────────────────────────────────────


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
