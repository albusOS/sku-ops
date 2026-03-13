"""Schema runner — bootstraps the database on startup.

Architecture:
  Each bounded context owns its current table definitions in
  {context}/infrastructure/schema.py (TABLES, INDEXES).

  full_schema.py aggregates all context schemas in dependency order.

  On startup the runner executes every CREATE TABLE/INDEX IF NOT EXISTS
  from full_schema.py, then applies seed data. All statements are
  idempotent — safe to run on every startup against an existing database.

  For a full data reset (demo environments), set RESET_DB=true before
  starting. The startup lifespan handles that before calling run_schema().
"""

import logging

logger = logging.getLogger(__name__)


async def run_schema(backend) -> None:
    """Ensure the database schema is up to date.

    Executes CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS for
    every table and index in the full schema, then applies idempotent seed
    data rows. Safe to call on every startup.
    """
    conn = backend.connection()
    from shared.infrastructure.full_schema import ALL_INDEXES, ALL_TABLES
    from shared.infrastructure.schema import SEED as _shared_seed

    for stmt in ALL_TABLES:
        await conn.execute(stmt)
    await conn.commit()

    for stmt in ALL_INDEXES + _shared_seed:
        await conn.execute(stmt)
    await conn.commit()

    logger.debug("Schema bootstrap complete")


# Keep old name as alias so init_db() doesn't need changing.
run_migrations = run_schema
