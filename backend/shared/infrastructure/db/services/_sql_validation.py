"""Read-only SQL validation (shared by analyst sandbox and RawSQLService)."""

from __future__ import annotations

import re

_ALLOWED_PREFIXES = ("SELECT", "WITH")

FORBIDDEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bINSERT\b", re.IGNORECASE),
        "INSERT statements are not allowed",
    ),
    (
        re.compile(r"\bUPDATE\b", re.IGNORECASE),
        "UPDATE statements are not allowed",
    ),
    (
        re.compile(r"\bDELETE\b", re.IGNORECASE),
        "DELETE statements are not allowed",
    ),
    (re.compile(r"\bDROP\b", re.IGNORECASE), "DROP statements are not allowed"),
    (
        re.compile(r"\bALTER\b", re.IGNORECASE),
        "ALTER statements are not allowed",
    ),
    (
        re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
        "TRUNCATE statements are not allowed",
    ),
    (
        re.compile(r"\bGRANT\b", re.IGNORECASE),
        "GRANT statements are not allowed",
    ),
    (
        re.compile(r"\bREVOKE\b", re.IGNORECASE),
        "REVOKE statements are not allowed",
    ),
    (re.compile(r"\bCOPY\b", re.IGNORECASE), "COPY statements are not allowed"),
    (
        re.compile(r"\bCREATE\b(?!\s+TEMP)", re.IGNORECASE),
        "CREATE statements are not allowed",
    ),
    (re.compile(r"\bSET\b", re.IGNORECASE), "SET statements are not allowed"),
    (
        re.compile(r"\bVACUUM\b", re.IGNORECASE),
        "VACUUM statements are not allowed",
    ),
    (
        re.compile(r"\bEXPLAIN\b", re.IGNORECASE),
        "EXPLAIN statements are not allowed",
    ),
    (
        re.compile(r"\bLISTEN\b", re.IGNORECASE),
        "LISTEN statements are not allowed",
    ),
    (
        re.compile(r"\bNOTIFY\b", re.IGNORECASE),
        "NOTIFY statements are not allowed",
    ),
]


class SQLValidationError(Exception):
    """Raised when SQL fails read-only validation."""


def validate_sql(sql: str) -> None:
    """Validate that SQL is a safe read-only query."""
    stripped = sql.strip()
    if not stripped:
        raise SQLValidationError("Empty query")

    normalized = stripped.upper().lstrip()
    if not any(normalized.startswith(p) for p in _ALLOWED_PREFIXES):
        raise SQLValidationError(
            f"Only SELECT and WITH (CTE) queries are allowed. Got: {normalized[:30]}..."
        )

    if ";" in stripped:
        parts = [p.strip() for p in stripped.split(";") if p.strip()]
        if len(parts) > 1:
            raise SQLValidationError(
                "Multi-statement queries are not allowed. Send one query at a time."
            )

    for pattern, message in FORBIDDEN_PATTERNS:
        if pattern.search(stripped):
            raise SQLValidationError(message)


def ensure_limit(sql: str, max_rows: int) -> str:
    """Append LIMIT if not already present."""
    upper = sql.upper()
    if "LIMIT" not in upper:
        return f"{sql.rstrip().rstrip(';')}\nLIMIT {max_rows}"
    return sql
