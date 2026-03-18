"""Full schema — aggregated from bounded context schema modules.

Single source of truth for the database schema.  Used by the migration runner
to bootstrap a *fresh* PostgreSQL database in one shot.
Each context owns its own table definitions; this module collects them
in dependency order (shared infra first, then catalog, inventory, etc.).
"""

from assistant.infrastructure.schema import (
    INDEXES as _assistant_indexes,
)
from assistant.infrastructure.schema import (
    MIGRATIONS as _assistant_migrations,
)
from assistant.infrastructure.schema import (
    TABLES as _assistant_tables,
)
from catalog.infrastructure.schema import (
    INDEXES as _catalog_indexes,
)
from catalog.infrastructure.schema import (
    MIGRATIONS as _catalog_migrations,
)
from catalog.infrastructure.schema import (
    TABLES as _catalog_tables,
)
from documents.infrastructure.schema import (
    INDEXES as _documents_indexes,
)
from documents.infrastructure.schema import (
    TABLES as _documents_tables,
)
from finance.infrastructure.schema import (
    INDEXES as _finance_indexes,
)
from finance.infrastructure.schema import (
    MIGRATIONS as _finance_migrations,
)
from finance.infrastructure.schema import (
    TABLES as _finance_tables,
)
from inventory.infrastructure.schema import (
    INDEXES as _inventory_indexes,
)
from inventory.infrastructure.schema import (
    MIGRATIONS as _inventory_migrations,
)
from inventory.infrastructure.schema import (
    TABLES as _inventory_tables,
)
from jobs.infrastructure.schema import (
    INDEXES as _jobs_indexes,
)
from jobs.infrastructure.schema import (
    TABLES as _jobs_tables,
)
from operations.infrastructure.schema import (
    INDEXES as _operations_indexes,
)
from operations.infrastructure.schema import (
    MIGRATIONS as _operations_migrations,
)
from operations.infrastructure.schema import (
    TABLES as _operations_tables,
)
from purchasing.infrastructure.schema import (
    INDEXES as _purchasing_indexes,
)
from purchasing.infrastructure.schema import (
    MIGRATIONS as _purchasing_migrations,
)
from purchasing.infrastructure.schema import (
    TABLES as _purchasing_tables,
)
from shared.infrastructure.schema import (
    EXTENSIONS as _shared_extensions,
)
from shared.infrastructure.schema import (
    INDEXES as _shared_indexes,
)
from shared.infrastructure.schema import (
    SEED as _shared_seed,
)
from shared.infrastructure.schema import (
    TABLES as _shared_tables,
)
from shared.infrastructure.schema import (
    VIEWS as _shared_views,
)

_ALL_TABLES: list[str] = (
    _shared_tables
    + _catalog_tables
    + _inventory_tables
    + _operations_tables
    + _finance_tables
    + _purchasing_tables
    + _documents_tables
    + _jobs_tables
    + _assistant_tables
)

_ALL_INDEXES: list[str] = (
    _shared_indexes
    + _catalog_indexes
    + _inventory_indexes
    + _operations_indexes
    + _finance_indexes
    + _purchasing_indexes
    + _documents_indexes
    + _jobs_indexes
    + _assistant_indexes
)

FULL_SCHEMA: list[str] = (
    _shared_extensions + _ALL_TABLES + _ALL_INDEXES + _shared_views + _shared_seed
)

# Exported separately so the migration runner can interleave migrations between
# table creation and index creation (needed when migrations rename columns that
# existing indexes reference).
ALL_EXTENSIONS: list[str] = _shared_extensions
ALL_TABLES: list[str] = _ALL_TABLES
ALL_INDEXES: list[str] = _ALL_INDEXES
ALL_VIEWS: list[str] = _shared_views

# Additive ALTER TABLE migrations — applied after tables and indexes.
# Each entry is idempotent (uses IF NOT EXISTS) or gracefully skipped on failure.
ALL_MIGRATIONS: list[str] = (
    _catalog_migrations
    + _inventory_migrations
    + _operations_migrations
    + _finance_migrations
    + _purchasing_migrations
    + _assistant_migrations
)

# Per-context table DDL — used by the analyst agent's schema introspection.
# Exported here (composition root) so the assistant context doesn't need
# cross-context infrastructure imports.
TABLES_BY_CONTEXT: dict[str, list[str]] = {
    "shared": _shared_tables,
    "catalog": _catalog_tables,
    "inventory": _inventory_tables,
    "operations": _operations_tables,
    "finance": _finance_tables,
    "purchasing": _purchasing_tables,
    "documents": _documents_tables,
    "jobs": _jobs_tables,
    "assistant": _assistant_tables,
}
