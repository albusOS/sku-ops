"""PostgreSQL backend using SQLAlchemy async engine plus raw-SQL compatibility."""

from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from shared.infrastructure.db.protocol import Connection, DictRow

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

# asyncpg rejects str for TIMESTAMPTZ binds when using exec_driver_sql; API/query
# layers often pass ISO-8601 strings from HTTP query params.
_ISO_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _coerce_bind_for_asyncpg(value: Any) -> Any:
    """Coerce ISO date/datetime strings to datetime for asyncpg type binding."""
    if not isinstance(value, str) or len(value) < 10:
        return value
    if not _ISO_DATE_PREFIX.match(value):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value


def _normalize_param_tuple(params: tuple | list) -> tuple:
    return tuple(_coerce_bind_for_asyncpg(p) for p in params)


def _normalize_params(params: tuple | list) -> tuple | None:
    if not params:
        return None
    return _normalize_param_tuple(params)


def _coerce_result_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {key: _coerce_result_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_result_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_coerce_result_value(item) for item in value)
    return value


class PgCursor:
    __slots__ = ("_rowcount", "_rows")

    def __init__(self, rows: list[dict[str, Any]], rowcount: int) -> None:
        self._rows = rows
        self._rowcount = rowcount

    @property
    def rowcount(self) -> int:
        return self._rowcount

    async def fetchone(self) -> DictRow | None:
        if not self._rows:
            return None
        return DictRow(self._rows[0])

    async def fetchall(self) -> list[DictRow]:
        return [DictRow(row) for row in self._rows]


async def _execute_sql(
    conn: AsyncConnection, sql: str, params: tuple | list = ()
) -> PgCursor:
    result = await conn.exec_driver_sql(sql, _normalize_params(params))
    rows = (
        [_coerce_result_value(dict(row)) for row in result.mappings().all()]
        if result.returns_rows
        else []
    )
    rowcount = result.rowcount if result.rowcount != -1 else len(rows)
    return PgCursor(rows, rowcount)


class PgPoolProxy:
    """Returned by ``get_connection()`` — acquires per execute, auto-commits."""

    __slots__ = ("_engine",)

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def execute(self, sql: str, params: tuple | list = ()) -> PgCursor:
        async with self._engine.begin() as conn:
            return await _execute_sql(conn, sql, params)

    async def executemany(
        self, sql: str, params_list: Sequence[tuple | list]
    ) -> None:
        compiled = [_normalize_param_tuple(params) for params in params_list]
        async with self._engine.begin() as conn:
            await conn.exec_driver_sql(sql, compiled)

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class PgTransactionProxy:
    """Single-connection raw SQL proxy used inside transaction context."""

    __slots__ = ("_conn",)

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def execute(self, sql: str, params: tuple | list = ()) -> PgCursor:
        return await _execute_sql(self._conn, sql, params)

    async def executemany(
        self, sql: str, params_list: Sequence[tuple | list]
    ) -> None:
        compiled = [_normalize_param_tuple(params) for params in params_list]
        await self._conn.exec_driver_sql(sql, compiled)

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass


class PostgresBackend:
    dialect = "postgresql"

    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "Database not initialized. Call connect() at startup."
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError(
                "Database not initialized. Call connect() at startup."
            )
        return self._session_factory

    async def connect(self, url: str) -> None:

        from shared.infrastructure.config import (
            PG_ACQUIRE_TIMEOUT,
            PG_COMMAND_TIMEOUT,
            PG_POOL_MAX,
            PG_POOL_MIN,
            is_deployed,
            is_test,
        )

        if ":6543" in url:
            msg = (
                "DATABASE_URL uses port 6543 (Supabase pgbouncer). "
                "Use the direct Postgres connection on port 5432 instead."
            )
            if is_deployed:
                raise RuntimeError(msg)
            logger.warning(msg)

        pool_size = max(PG_POOL_MIN, 1)
        max_overflow = max(PG_POOL_MAX - pool_size, 0)
        async_url = url
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        elif async_url.startswith("postgres://"):
            async_url = async_url.replace(
                "postgres://", "postgresql+asyncpg://", 1
            )

        engine_kwargs: dict[str, Any] = {
            "pool_pre_ping": True,
            "connect_args": {"command_timeout": PG_COMMAND_TIMEOUT},
        }
        if is_test:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = pool_size
            engine_kwargs["max_overflow"] = max_overflow
            engine_kwargs["pool_timeout"] = PG_ACQUIRE_TIMEOUT

        self._engine = create_async_engine(async_url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False
        )
        self._register_pool_events()

    def _register_pool_events(self) -> None:
        if self._engine is None:
            return
        pool = self._engine.sync_engine.pool

        event.listen(pool, "checkout", self._on_checkout)
        event.listen(pool, "checkin", self._on_checkin)
        event.listen(pool, "invalidate", self._on_invalidate)

    @staticmethod
    def _on_checkout(*_args: object) -> None:
        logger.debug("DB pool checkout")

    @staticmethod
    def _on_checkin(*_args: object) -> None:
        logger.debug("DB pool checkin")

    @staticmethod
    def _on_invalidate(*_args: object) -> None:
        logger.warning("DB connection invalidated")

    def connection(self) -> Connection:
        return PgPoolProxy(self.engine)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Connection]:
        async with self.engine.connect() as conn:
            async with conn.begin():
                yield PgTransactionProxy(conn)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        session = self.session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def transaction_bundle(
        self,
    ) -> AsyncIterator[tuple[Connection, AsyncSession]]:
        async with self.engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn, expire_on_commit=False)
                try:
                    yield PgTransactionProxy(conn), session
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

    async def health_check(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.exec_driver_sql("SELECT 1")
            return True
        except Exception:
            logger.exception("Database health check failed")
            return False

    def get_pool_status(self) -> dict[str, str]:
        return {"status": self.engine.sync_engine.pool.status()}

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
