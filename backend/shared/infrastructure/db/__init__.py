"""Central DB API - async session access and transaction scope."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from shared.infrastructure.db.services.raw_sql import ExecutionResult
from shared.infrastructure.db.uow import _tx_session
from shared.infrastructure.logging_config import org_id_var, user_id_var

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

_state: dict[str, object | None] = {"manager": None}


def _manager():
    from shared.infrastructure.db.base import get_database_manager

    manager = _state["manager"]
    if manager is None:
        manager = get_database_manager()
        _state["manager"] = manager
    return manager


async def init_db() -> None:
    """Open connection pool using the externally managed Supabase schema."""
    from shared.infrastructure.db.base import get_database_manager

    manager = get_database_manager()
    _state["manager"] = manager
    await manager.connect()


def get_org_id() -> str:
    """Return the ambient org_id for the current request or job context."""
    return org_id_var.get("")


def get_user_id() -> str:
    """Return the ambient user_id for the current request or job context."""
    return user_id_var.get("")


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    tx_session = _tx_session.get()
    if tx_session is not None:
        yield tx_session
        return
    async with _manager().db_service.get_session() as session:
        yield session


@asynccontextmanager
async def transaction() -> AsyncIterator[None]:
    """Open a unit of work (commits on success, rolls back on error).

    Nested calls reuse the ambient session without opening a new transaction.
    Use ``get_session()`` or ``get_database_manager().sql`` inside the block.
    """
    if _tx_session.get() is not None:
        yield
        return
    async with _manager().transaction():
        yield


async def close_db() -> None:
    """Close connection pool on shutdown."""
    manager = _state["manager"]
    if manager is not None:
        await manager.close()
        _state["manager"] = None


async def sql_execute(
    sql: str,
    params: dict[str, Any] | Sequence[Any] | None = None,
    *,
    read_only: bool = False,
    timeout_ms: int = 10_000,
    max_rows: int = 500,
) -> ExecutionResult:
    """Run a single raw SQL statement via :named or ``$1``-style parameters."""
    return await _manager().sql.execute(
        sql,
        params,
        read_only=read_only,
        timeout_ms=timeout_ms,
        max_rows=max_rows,
    )


async def sql_execute_many(
    sql: str,
    params_list: list[dict[str, Any]] | list[Sequence[Any]],
    *,
    read_only: bool = False,
) -> int:
    """Execute the same statement for many parameter rows; returns rows affected."""
    return await _manager().sql.execute_many(
        sql, params_list, read_only=read_only
    )


__all__ = [
    "ExecutionResult",
    "_tx_session",
    "close_db",
    "get_org_id",
    "get_session",
    "get_user_id",
    "init_db",
    "sql_execute",
    "sql_execute_many",
    "transaction",
]
