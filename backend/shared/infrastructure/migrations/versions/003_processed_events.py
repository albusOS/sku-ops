"""Migration 003 — Create processed_events table for handler idempotency.

Tracks which (event_id, handler_name) pairs have been processed so handlers
decorated with @idempotent can skip duplicate deliveries.
"""

import logging

logger = logging.getLogger(__name__)


async def _table_exists(conn, table: str, dialect: str) -> bool:
    if dialect == "sqlite":
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return (await cursor.fetchone()) is not None
    cursor = await conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name = ?",
        (table,),
    )
    return (await cursor.fetchone()) is not None


async def up(conn, dialect: str) -> None:
    if await _table_exists(conn, "processed_events", dialect):
        logger.info("Migration 003: processed_events already exists — skipping")
        return

    await conn.execute(
        """CREATE TABLE processed_events (
            event_id TEXT NOT NULL,
            handler_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            PRIMARY KEY (event_id, handler_name)
        )"""
    )
    await conn.commit()
    logger.info("Migration 003: created processed_events table")
