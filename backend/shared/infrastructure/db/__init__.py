"""Central DB API - raw SQL compatibility plus async session access."""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.logging_config import org_id_var, user_id_var

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.infrastructure.db.protocol import Connection

_state: dict[str, object | None] = {"manager": None}

_tx_conn: ContextVar[Connection | None] = ContextVar("_tx_conn", default=None)
_tx_session: ContextVar[AsyncSession | None] = ContextVar(
    "_tx_session", default=None
)


def _manager():
    manager = _state["manager"]
    if manager is None:
        manager = get_database_manager()
        _state["manager"] = manager
    return manager


async def init_db() -> None:
    """Open connection pool using the externally managed Supabase schema."""
    manager = get_database_manager()
    _state["manager"] = manager
    await manager.connect()


def get_org_id() -> str:
    """Return the ambient org_id for the current request or job context."""
    return org_id_var.get("")


def get_user_id() -> str:
    """Return the ambient user_id for the current request or job context."""
    return user_id_var.get("")


def get_connection() -> Connection:
    """Return the ambient transactional connection if inside a transaction(),
    otherwise fall back to the pool proxy."""
    tx = _tx_conn.get()
    if tx is not None:
        return tx
    return _manager().db_service.connection()


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    tx_session = _tx_session.get()
    if tx_session is not None:
        yield tx_session
        return
    async with _manager().db_service.get_session() as session:
        yield session


@asynccontextmanager
async def transaction() -> AsyncIterator[Connection]:
    """Async context manager — commits on success, rolls back on exception.

    Stores the transactional connection in a contextvar so that
    get_connection() returns it for the duration of the block.
    Nested calls reuse the existing ambient connection.
    """
    existing = _tx_conn.get()
    if existing is not None:
        yield existing
        return
    async with _manager().transaction() as tx:
        conn_token = _tx_conn.set(tx.connection)
        session_token = _tx_session.set(tx.session)
        try:
            yield tx.connection
        finally:
            _tx_conn.reset(conn_token)
            _tx_session.reset(session_token)


async def close_db() -> None:
    """Close connection pool on shutdown."""
    manager = _state["manager"]
    if manager is not None:
        await manager.close()
        _state["manager"] = None
