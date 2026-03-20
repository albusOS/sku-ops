"""Database protocol — interface contract for the PostgreSQL adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from contextlib import AbstractAsyncContextManager


import re

# Matches Postgres text-format timestamps with a two-digit tz offset (e.g. +00, -05)
# that stdlib fromisoformat (pre-3.11) and Pydantic reject.
_TRUNCATED_TZ_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)([+-]\d{2})$")


def _coerce_value(v, decimal_type, datetime_type):
    if isinstance(v, decimal_type):
        return float(v)
    if isinstance(v, str):
        m = _TRUNCATED_TZ_RE.match(v)
        if m:
            return datetime_type.fromisoformat(m.group(1) + m.group(2) + ":00")
    return v


class DictRow(dict):
    """Dict that also supports integer-index access (row[0], row[1]).

    NUMERIC columns come back from asyncpg as ``Decimal``.  All domain models
    use ``float`` for monetary/quantity fields, so we coerce at the DB boundary.

    TIMESTAMPTZ columns may arrive as strings when routed through connection
    poolers (e.g. Supavisor).  Postgres text format uses a shortened timezone
    offset (``+00``) that Pydantic rejects, so we parse those into proper
    ``datetime`` objects here.
    """

    def __init__(self, mapping):
        from datetime import datetime
        from decimal import Decimal

        coerced = {k: _coerce_value(v, Decimal, datetime) for k, v in mapping.items()}
        super().__init__(coerced)
        self._keys = list(coerced.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)


def to_dict_row(mapping) -> DictRow:
    """Convert any mapping (dict, asyncpg.Record) to DictRow."""
    return DictRow(dict(mapping))


@runtime_checkable
class Cursor(Protocol):
    """Minimal cursor returned by Connection.execute()."""

    @property
    def rowcount(self) -> int: ...

    async def fetchone(self) -> DictRow | None: ...

    async def fetchall(self) -> list[DictRow]: ...


@runtime_checkable
class Connection(Protocol):
    """Async database connection (pool proxy or transaction proxy)."""

    async def execute(self, sql: str, params: tuple | list = ()) -> Cursor: ...

    async def executemany(self, sql: str, params_list: Sequence[tuple | list]) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class DatabaseBackend(Protocol):
    """Lifecycle manager for the PostgreSQL backend."""

    dialect: str

    async def connect(self, url: str) -> None: ...

    def connection(self) -> Connection: ...

    def transaction(self) -> AbstractAsyncContextManager[Connection]: ...

    async def close(self) -> None: ...
