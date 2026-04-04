"""Central database services for SQLModel plus raw-SQL compatibility."""

from __future__ import annotations

import asyncio
import importlib
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Self

from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError

from shared.infrastructure.config import DATABASE_URL
from shared.infrastructure.db import uow
from shared.infrastructure.db.postgres import PostgresBackend
from shared.infrastructure.db.supabase import get_async_supabase, get_supabase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

    from shared.infrastructure.db.services.assistant import (
        AssistantDatabaseService,
    )
    from shared.infrastructure.db.services.catalog import CatalogDatabaseService
    from shared.infrastructure.db.services.documents import (
        DocumentsDatabaseService,
    )
    from shared.infrastructure.db.services.finance import FinanceDatabaseService
    from shared.infrastructure.db.services.inventory import (
        InventoryDatabaseService,
    )
    from shared.infrastructure.db.services.jobs import JobsDatabaseService
    from shared.infrastructure.db.services.operations import (
        OperationsDatabaseService,
    )
    from shared.infrastructure.db.services.purchasing import (
        PurchasingDatabaseService,
    )
    from shared.infrastructure.db.services.raw_sql import RawSQLService
    from shared.infrastructure.db.services.shared import SharedDatabaseService

logger = logging.getLogger(__name__)


class BaseDatabaseService:
    """Per-URL singleton owning engine, sessions, health, and Supabase handles."""

    _instances: ClassVar[dict[str, BaseDatabaseService]] = {}

    def __new__(cls, url: str) -> Self:
        if url not in cls._instances:
            cls._instances[url] = super().__new__(cls)
        return cls._instances[url]

    def __init__(self, url: str) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._url = url
        self._backend = PostgresBackend()
        self._connected = False

    @property
    def engine(self):
        return self._backend.engine

    @property
    def async_session_factory(self):
        return self._backend.session_factory

    @property
    def supabase(self):
        return get_supabase(False)

    @property
    def supabase_admin(self):
        return get_supabase(True)

    @property
    def is_healthy(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        if not self._connected:
            await self._backend.connect(self._url)
            self._connected = True

    @asynccontextmanager
    async def transaction_bundle(self) -> AsyncIterator[AsyncSession]:
        async with self._backend.transaction_bundle() as session:
            yield session

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        retries = 3
        delay_seconds = 0.2
        for attempt in range(1, retries + 1):
            try:
                async with self._backend.session() as session:
                    yield session
                    return
            except SQLAlchemyTimeoutError:
                if attempt == retries:
                    raise RuntimeError("Database session unavailable after retry exhaustion") from None
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2

    async def health_check(self) -> dict[str, Any]:
        return {
            "healthy": await self._backend.health_check(),
            "pool": self._backend.get_pool_status(),
            "url": self._url,
        }

    def get_pool_status(self) -> dict[str, str]:
        return self._backend.get_pool_status()

    async def close(self) -> None:
        await self._backend.close()
        self._connected = False


class RealtimeServiceProxy:
    """Lazy async Supabase proxy for realtime-oriented flows."""

    async def get_client(self):
        client = await get_async_supabase(False)
        if client is None:
            raise RuntimeError("Async Supabase client is not configured for this environment.")
        return client


class TransactionContext:
    """Opens one DB transaction and ORM session; sets ``_tx_session`` contextvar."""

    def __init__(self, db_service: BaseDatabaseService) -> None:
        self._db_service = db_service
        self._cm = None
        self._nested = False
        self._sess_token = None
        self.session = None

    async def __aenter__(self) -> Self:
        if uow._tx_session.get() is not None:
            self._nested = True
            self.session = uow._tx_session.get()
            return self
        self._nested = False
        self._cm = self._db_service.transaction_bundle()
        self.session = await self._cm.__aenter__()
        self._sess_token = uow._tx_session.set(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._nested:
            return None
        try:
            if self._cm is not None:
                return await self._cm.__aexit__(exc_type, exc, tb)
        finally:
            if self._sess_token is not None:
                uow._tx_session.reset(self._sess_token)
                self._sess_token = None
        return None


class TransactionScope:
    """Atomic multi-step API: ``async with db.transaction() as tx: await tx.finance.*``.

    ``tx.<name>`` delegates to the same lazy services as ``DatabaseManager``; ORM and
    raw SQL use ambient session via ``get_session()`` / ``db.sql``.
    """

    # Keep TYPE_CHECKING attributes in sync with DatabaseManager.
    if TYPE_CHECKING:
        shared: SharedDatabaseService
        catalog: CatalogDatabaseService
        inventory: InventoryDatabaseService
        operations: OperationsDatabaseService
        finance: FinanceDatabaseService
        purchasing: PurchasingDatabaseService
        documents: DocumentsDatabaseService
        jobs: JobsDatabaseService
        assistant: AssistantDatabaseService
        sql: RawSQLService
        realtime: RealtimeServiceProxy
        session: AsyncSession | None

    def __init__(self, manager: DatabaseManager) -> None:
        self._manager = manager
        self._ctx = TransactionContext(manager.db_service)

    @property
    def session(self) -> AsyncSession | None:
        return self._ctx.session

    async def __aenter__(self) -> Self:
        await self._ctx.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._ctx.__aexit__(exc_type, exc, tb)

    def __getattr__(self, name: str) -> object:
        return getattr(self._manager, name)


class DatabaseManager:
    """Application-facing facade for lazy domain database services."""

    if TYPE_CHECKING:
        shared: SharedDatabaseService
        catalog: CatalogDatabaseService
        inventory: InventoryDatabaseService
        operations: OperationsDatabaseService
        finance: FinanceDatabaseService
        purchasing: PurchasingDatabaseService
        documents: DocumentsDatabaseService
        jobs: JobsDatabaseService
        assistant: AssistantDatabaseService
        sql: RawSQLService
        realtime: RealtimeServiceProxy

    def __init__(self, db_service: BaseDatabaseService | None = None) -> None:
        self.db_service = db_service or BaseDatabaseService(DATABASE_URL)
        self._services: dict[str, object] = {}
        self._service_health: dict[str, str] = {}
        self._load_stats: dict[str, int] = {}
        self._service_paths = {
            "shared": "shared.infrastructure.db.services.shared.SharedDatabaseService",
            "catalog": "shared.infrastructure.db.services.catalog.CatalogDatabaseService",
            "inventory": "shared.infrastructure.db.services.inventory.InventoryDatabaseService",
            "operations": "shared.infrastructure.db.services.operations.OperationsDatabaseService",
            "finance": "shared.infrastructure.db.services.finance.FinanceDatabaseService",
            "purchasing": "shared.infrastructure.db.services.purchasing.PurchasingDatabaseService",
            "documents": "shared.infrastructure.db.services.documents.DocumentsDatabaseService",
            "jobs": "shared.infrastructure.db.services.jobs.JobsDatabaseService",
            "assistant": "shared.infrastructure.db.services.assistant.AssistantDatabaseService",
            "sql": "shared.infrastructure.db.services.raw_sql.RawSQLService",
            "realtime": "shared.infrastructure.db.base.RealtimeServiceProxy",
        }

    async def connect(self) -> None:
        await self.db_service.connect()

    def __getattr__(self, name: str):
        if name not in self._service_paths:
            raise AttributeError(name)
        if name in self._services:
            self._load_stats[name] = self._load_stats.get(name, 0) + 1
            return self._services[name]

        service = self._build_service(name)
        self._services[name] = service
        self._service_health[name] = "ready"
        self._load_stats[name] = self._load_stats.get(name, 0) + 1
        return service

    def _build_service(self, name: str):
        module_path, class_name = self._service_paths[name].rsplit(".", 1)
        module = importlib.import_module(module_path)
        service_class = getattr(module, class_name)
        if name == "realtime":
            return service_class()
        return service_class(self.db_service)

    def transaction(self) -> TransactionScope:
        return TransactionScope(self)

    async def warmup(self) -> None:
        await self.connect()
        for name in ("shared", "catalog", "inventory", "operations", "finance"):
            _ = getattr(self, name)

    async def health_check(self) -> dict[str, Any]:
        return {
            "database": await self.db_service.health_check(),
            "services": self._service_health,
        }

    def get_performance_stats(self) -> dict[str, int]:
        return dict(self._load_stats)

    def get_loaded_services(self) -> list[str]:
        return sorted(self._services.keys())

    async def close(self) -> None:
        self._services.clear()
        await self.db_service.close()


_default_manager: DatabaseManager | None = None


def get_database_manager(
    db_service: BaseDatabaseService | None = None,
) -> DatabaseManager:
    global _default_manager
    if db_service is not None:
        _default_manager = DatabaseManager(db_service)
        return _default_manager
    if _default_manager is None:
        _default_manager = DatabaseManager()
    return _default_manager
