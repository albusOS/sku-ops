"""Schema bootstrap — creates all tables and indexes on a fresh database.

Each bounded context owns its current table definitions in
{context}/infrastructure/schema.py (TABLES, INDEXES).

full_schema.py aggregates all context schemas in dependency order.

On startup the runner:
  1. Runs every CREATE TABLE IF NOT EXISTS from full_schema.py (idempotent).
  2. Runs every CREATE INDEX IF NOT EXISTS.
  3. Applies shared reference data (SEED statements).

This is intentionally simple — no migration version tracking.

For local development after a schema change:
  ./bin/dev db:reset    (tears down the volume and re-creates a clean DB)

For production additive changes (new tables, new columns with defaults):
  Deploy normally. run_schema() is idempotent and will apply new
  CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS statements.

For production destructive changes (column drops, renames, type changes):
  These require explicit SQL run against the live database BEFORE deploying
  the new code. There is no migration runner for these — write and review
  the SQL manually, apply it, then deploy.
"""

import logging

from shared.infrastructure.full_schema import ALL_INDEXES, ALL_TABLES
from shared.infrastructure.schema import SEED as _shared_seed

logger = logging.getLogger(__name__)


async def run_schema(backend) -> None:
    """Bootstrap the database schema.

    Safe to call on an already-initialised database — all statements use
    CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
    """
    conn = backend.connection()

    for stmt in ALL_TABLES:
        await conn.execute(stmt)
    await conn.commit()

    for stmt in ALL_INDEXES + _shared_seed:
        await conn.execute(stmt)
    await conn.commit()

    logger.debug("Schema bootstrap complete")
