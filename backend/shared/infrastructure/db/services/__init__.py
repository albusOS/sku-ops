"""Lazy-loaded per-context database services (see DatabaseManager._service_paths)."""

from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services.assistant import AssistantDatabaseService
from shared.infrastructure.db.services.catalog import CatalogDatabaseService
from shared.infrastructure.db.services.documents import DocumentsDatabaseService
from shared.infrastructure.db.services.finance import FinanceDatabaseService
from shared.infrastructure.db.services.inventory import InventoryDatabaseService
from shared.infrastructure.db.services.jobs import JobsDatabaseService
from shared.infrastructure.db.services.operations import (
    OperationsDatabaseService,
)
from shared.infrastructure.db.services.purchasing import (
    PurchasingDatabaseService,
)
from shared.infrastructure.db.services.shared import SharedDatabaseService

__all__ = [
    "AssistantDatabaseService",
    "CatalogDatabaseService",
    "DocumentsDatabaseService",
    "DomainDatabaseService",
    "FinanceDatabaseService",
    "InventoryDatabaseService",
    "JobsDatabaseService",
    "OperationsDatabaseService",
    "PurchasingDatabaseService",
    "SharedDatabaseService",
]
