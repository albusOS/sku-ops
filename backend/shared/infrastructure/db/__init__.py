"""Database package — drop-in replacement for the old database.py module.

Public API (unchanged from the original):
    init_db()        — call once at startup
    get_connection() — returns a Connection (protocol)
    transaction()    — async context manager yielding a Connection
    close_db()       — call once at shutdown

The backend (SQLite vs PostgreSQL) is selected automatically from DATABASE_URL.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from shared.infrastructure.config import DATABASE_URL

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from shared.infrastructure.db.protocol import Connection, DatabaseBackend

_state: dict[str, DatabaseBackend | None] = {"backend": None}


def _make_backend(url: str) -> DatabaseBackend:
    if url.startswith(("postgresql://", "postgres://")):
        from shared.infrastructure.db.postgres import PostgresBackend

        return PostgresBackend()
    from shared.infrastructure.db.sqlite import SqliteBackend

    return SqliteBackend()


async def init_db() -> None:
    """Open connection / pool and run pending migrations."""
    _state["backend"] = _make_backend(DATABASE_URL)
    await _state["backend"].connect(DATABASE_URL)

    from shared.infrastructure.migrations.runner import run_migrations

    await run_migrations(_state["backend"])


def get_connection() -> Connection:
    """Return the database connection (pool proxy for PG, wrapper for SQLite)."""
    if _state["backend"] is None:
        raise RuntimeError("Database not initialized. Call init_db() at startup.")
    return _state["backend"].connection()


@asynccontextmanager
async def transaction() -> AsyncIterator[Connection]:
    """Async context manager — commits on success, rolls back on exception."""
    if _state["backend"] is None:
        raise RuntimeError("Database not initialized. Call init_db() at startup.")
    async with _state["backend"].transaction() as conn:
        yield conn


async def close_db() -> None:
    """Close connection / pool on shutdown."""
    if _state["backend"]:
        await _state["backend"].close()
        _state["backend"] = None
