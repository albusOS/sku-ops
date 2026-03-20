"""Lazy per-context database service handles."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.infrastructure.db.base import BaseDatabaseService


class DomainDatabaseService:
    def __init__(self, db_service: BaseDatabaseService) -> None:
        self.db_service = db_service

    @asynccontextmanager
    async def session(self):
        async with self.db_service.get_session() as session:
            yield session

    def connection(self):
        return self.db_service.connection()


class SharedDatabaseService(DomainDatabaseService):
    pass


class CatalogDatabaseService(DomainDatabaseService):
    pass


class InventoryDatabaseService(DomainDatabaseService):
    pass


class OperationsDatabaseService(DomainDatabaseService):
    pass


class FinanceDatabaseService(DomainDatabaseService):
    pass


class PurchasingDatabaseService(DomainDatabaseService):
    pass


class DocumentsDatabaseService(DomainDatabaseService):
    pass


class JobsDatabaseService(DomainDatabaseService):
    pass


class AssistantDatabaseService(DomainDatabaseService):
    pass
