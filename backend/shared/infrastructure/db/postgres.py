"""PostgreSQL backend using SQLAlchemy async engine and session factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from shared.infrastructure.config import config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class PostgresBackend:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call connect() at startup.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call connect() at startup.")
        return self._session_factory

    async def connect(self, url: str) -> None:
        pool_size = max(config.PG_POOL_MIN, 1)
        max_overflow = max(config.PG_POOL_MAX - pool_size, 0)

        connect_args: dict[str, Any] = {"command_timeout": config.PG_COMMAND_TIMEOUT}
        if config.DB_SSL_MODE:
            connect_args["ssl"] = config.DB_SSL_MODE

        engine_kwargs: dict[str, Any] = {
            "pool_pre_ping": True,
            "connect_args": connect_args,
        }
        if config.is_test:
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = pool_size
            engine_kwargs["max_overflow"] = max_overflow
            engine_kwargs["pool_timeout"] = config.PG_ACQUIRE_TIMEOUT

        self._engine = create_async_engine(url, **engine_kwargs)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
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
    async def transaction_bundle(self) -> AsyncIterator[AsyncSession]:
        async with self.engine.connect() as conn, conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.exec_driver_sql("SELECT 1")
        except Exception:
            logger.exception("Database health check failed")
            return False
        else:
            return True

    def get_pool_status(self) -> dict[str, str]:
        return {"status": self.engine.sync_engine.pool.status()}

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
