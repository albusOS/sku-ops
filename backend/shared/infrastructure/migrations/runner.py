"""Schema runner — bootstraps the database from context schemas.

Architecture:
  Each bounded context owns its current table definitions in
  {context}/infrastructure/schema.py (TABLES, INDEXES).

  full_schema.py aggregates all context schemas in dependency order.

  On startup the runner checks whether the database has been initialized.
  If not, it creates every table and index from full_schema.py in one shot.

  There is no migration chain.  Schema changes are made directly in the
  context schema files and applied by re-creating the database.
"""
import logging

logger = logging.getLogger(__name__)


async def _table_exists(conn, table: str, *, dialect: str = "sqlite") -> bool:
    if dialect == "sqlite":
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
    else:
        cursor = await conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = ?", (table,)
        )
    return (await cursor.fetchone()) is not None


async def _bootstrap_full_schema(conn) -> None:
    """Create the full schema on a fresh database (any dialect)."""
    from full_schema import FULL_SCHEMA
    for stmt in FULL_SCHEMA:
        await conn.execute(stmt)
    await conn.commit()


async def run_migrations(backend) -> None:
    """Ensure the database schema is up to date.

    All schema statements use CREATE TABLE/INDEX IF NOT EXISTS, so running
    them on an existing database is safe — new tables and indexes are added
    without touching existing data.  This means new bounded contexts and new
    tables automatically appear on the next server restart with no manual
    migration step.
    """
    conn = backend.connection()
    from full_schema import FULL_SCHEMA

    is_fresh = not await _table_exists(conn, "users", dialect=backend.dialect)
    if is_fresh:
        logger.info("Fresh database — bootstrapping schema")
    else:
        logger.debug("Existing database — applying any missing tables/indexes")

    for stmt in FULL_SCHEMA:
        await conn.execute(stmt)
    await conn.commit()

    if is_fresh:
        logger.info("Schema bootstrapped")
