"""Database connection management - SQLite with aiosqlite."""
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from shared.infrastructure.config import DATABASE_URL
from shared.infrastructure.migrations.runner import run_migrations

_db_path = DATABASE_URL.replace("sqlite:///", "").lstrip("/") if "://" in DATABASE_URL else DATABASE_URL

_conn: aiosqlite.Connection | None = None


def _get_db_path() -> str:
    if _db_path == ":memory:":
        return ":memory:"
    path = Path(_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path.resolve())


async def init_db() -> None:
    """Open connection, enable WAL + FK, run pending migrations."""
    global _conn
    _conn = await aiosqlite.connect(_get_db_path())
    _conn.row_factory = aiosqlite.Row
    await _conn.execute("PRAGMA journal_mode=WAL")
    await _conn.execute("PRAGMA foreign_keys=ON")
    await run_migrations(_conn)


def get_connection() -> aiosqlite.Connection:
    """Return the shared database connection. Must call init_db() first."""
    if _conn is None:
        raise RuntimeError("Database not initialized. Call init_db() at startup.")
    return _conn


@asynccontextmanager
async def transaction():
    """Async context manager for database transactions.

    Commits on success, rolls back on exception.
    Yields the connection so repos can reuse it without issuing their own commit.
    """
    conn = get_connection()
    await conn.execute("BEGIN")
    try:
        yield conn
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise


async def close_db() -> None:
    """Close the database connection on shutdown."""
    global _conn
    if _conn:
        await _conn.close()
        _conn = None
