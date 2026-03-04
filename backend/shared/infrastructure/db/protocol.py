"""Database protocol — interface contract for SQLite and PostgreSQL adapters."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class Cursor(Protocol):
    """Minimal cursor returned by Connection.execute()."""

    @property
    def rowcount(self) -> int: ...

    async def fetchone(self) -> dict | None: ...

    async def fetchall(self) -> list[dict]: ...


@runtime_checkable
class Connection(Protocol):
    """Async database connection (single conn or pool proxy)."""

    async def execute(self, sql: str, params: tuple | list = ()) -> Cursor: ...

    async def executemany(self, sql: str, params_list: list[tuple | list]) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class DatabaseBackend(Protocol):
    """Lifecycle manager for a database backend (SQLite or PostgreSQL)."""

    dialect: str  # "sqlite" or "postgresql"

    async def connect(self, url: str) -> None: ...

    def connection(self) -> Connection: ...

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Connection]: ...

    async def close(self) -> None: ...
