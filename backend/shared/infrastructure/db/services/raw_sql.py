"""Parameterized raw SQL via SQLAlchemy ``text()`` and ambient ``AsyncSession``."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text

from shared.infrastructure.db.base import BaseDatabaseService
from shared.infrastructure.db.services._sql_validation import (
    SQLValidationError,
    ensure_limit,
    validate_sql,
)

_ISO_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")
_STATEMENT_TIMEOUT_MAX_MS = 600_000
_UUID_HEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _statement_timeout_clause(timeout_ms: int) -> str:
    """Inline timeout for SET LOCAL (asyncpg cannot bind SET parameters reliably)."""
    if timeout_ms < 1 or timeout_ms > _STATEMENT_TIMEOUT_MAX_MS:
        msg = f"timeout_ms must be 1..{_STATEMENT_TIMEOUT_MAX_MS}, got {timeout_ms}"
        raise ValueError(msg)
    return f"SET LOCAL statement_timeout = '{int(timeout_ms)}ms'"


def positional_placeholders_to_named(
    sql: str, params: Sequence[Any]
) -> tuple[str, dict[str, Any]]:
    """Map Postgres-style ``$1`` .. ``$n`` to SQLAlchemy named binds (``:_p1`` ...)."""
    n = len(params)
    out_sql = sql
    for i in range(n, 0, -1):
        out_sql = out_sql.replace(f"${i}", f":_p{i}")
    mapping = {f"_p{i}": params[i - 1] for i in range(1, n + 1)}
    return out_sql, mapping


def coerce_bind_value(value: Any) -> Any:
    """Coerce ISO date strings and UUID strings for asyncpg type binding."""
    if isinstance(value, str) and _UUID_HEX.match(value):
        try:
            return UUID(value)
        except ValueError:
            return value
    if not isinstance(value, str) or len(value) < 10:
        return value
    if not _ISO_DATE_PREFIX.match(value):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value


def coerce_bind_mapping(params: Mapping[str, Any]) -> dict[str, Any]:
    return {k: coerce_bind_value(v) for k, v in params.items()}


def normalize_param_tuple(params: tuple | list) -> tuple[Any, ...]:
    return tuple(coerce_bind_value(p) for p in params)


def normalize_params(params: tuple | list) -> tuple[Any, ...] | None:
    if not params:
        return None
    return normalize_param_tuple(params)


def normalize_sql_value(value: Any) -> Any:
    """Normalize driver values to API-friendly scalars (Decimal, UUID, nested)."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: normalize_sql_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_sql_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(normalize_sql_value(v) for v in value)
    return value


class RowDict(dict):
    """Dict with int index access (``row[0]``, ``row[1]``) for legacy repo code."""

    def __init__(self, mapping: Mapping[str, Any]) -> None:
        coerced = normalize_sql_value(dict(mapping))
        super().__init__(coerced)
        self._keys: list[str] = list(coerced.keys())

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)


def normalize_row_mapping(row: Mapping[str, Any]) -> RowDict:
    return RowDict(row)


@dataclass(frozen=True)
class ExecutionResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    duration_ms: int = 0

    @property
    def rowcount(self) -> int:
        """Alias for ``row_count`` (matches legacy asyncpg cursor attribute)."""
        return self.row_count


class RawSQLService:
    """Runs raw SQL on the ambient session (or a standalone autocommit session)."""

    def __init__(self, db_service: BaseDatabaseService) -> None:
        self._db_service = db_service

    def _prepare_params(
        self, sql: str, params: dict[str, Any] | Sequence[Any] | None
    ) -> tuple[str, dict[str, Any]]:
        if params is None:
            return sql, {}
        if isinstance(params, Mapping):
            return sql, coerce_bind_mapping(dict(params))
        return positional_placeholders_to_named(sql, list(params))

    async def execute(
        self,
        sql: str,
        params: dict[str, Any] | Sequence[Any] | None = None,
        *,
        read_only: bool = True,
        timeout_ms: int = 10_000,
        max_rows: int = 500,
    ) -> ExecutionResult:
        from shared.infrastructure.db import get_session, uow

        work_sql = sql
        if read_only:
            validate_sql(work_sql)
            work_sql = ensure_limit(work_sql, max_rows)

        sql_exec, bind = self._prepare_params(work_sql, params)
        t0 = time.monotonic()
        async with get_session() as session:
            if read_only:
                await session.execute(
                    text(_statement_timeout_clause(timeout_ms))
                )
            result = await session.execute(text(sql_exec), bind)
            if result.returns_rows:
                raw_rows = result.mappings().all()
                rows = [normalize_row_mapping(r) for r in raw_rows]
                columns = list(rows[0].keys()) if rows else []
                db_row_count = len(rows)
            else:
                rows = []
                columns = []
                db_row_count = int(result.rowcount or 0)

            if read_only:
                truncated = db_row_count >= max_rows
            else:
                truncated = False

            ambient = uow._tx_session.get()
            if ambient is not None and ambient is session:
                if not read_only:
                    await session.flush()
            elif not read_only:
                await session.commit()

        duration_ms = int((time.monotonic() - t0) * 1000)
        return ExecutionResult(
            columns=columns,
            rows=rows,
            row_count=db_row_count,
            truncated=truncated,
            duration_ms=duration_ms,
        )

    async def execute_many(
        self,
        sql: str,
        params_list: list[dict[str, Any]] | list[Sequence[Any]],
        *,
        read_only: bool = False,
    ) -> int:
        from shared.infrastructure.db import get_session, uow

        if read_only:
            validate_sql(sql)
        total = 0
        async with get_session() as session:
            for raw in params_list:
                sql_exec, bind = self._prepare_params(sql, raw)
                res = await session.execute(text(sql_exec), bind)
                total += int(res.rowcount or 0)
            ambient = uow._tx_session.get()
            if ambient is not None and ambient is session:
                await session.flush()
            else:
                await session.commit()
        return total


__all__ = [
    "ExecutionResult",
    "RawSQLService",
    "RowDict",
    "SQLValidationError",
    "coerce_bind_mapping",
    "coerce_bind_value",
    "normalize_param_tuple",
    "normalize_params",
    "normalize_row_mapping",
    "normalize_sql_value",
    "positional_placeholders_to_named",
]
