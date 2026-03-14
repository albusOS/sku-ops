"""Migration 002 — Add auto_invoice column to org_settings.

Per-org toggle for auto-creating invoices on withdrawal. Default 0 (off)
so manual invoicing is the default.
"""

import logging

logger = logging.getLogger(__name__)


async def _column_exists(conn, table: str, column: str, dialect: str) -> bool:
    if dialect == "sqlite":
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return any(row[1] == column for row in rows)
    cursor = await conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = ? AND column_name = ?",
        (table, column),
    )
    return (await cursor.fetchone()) is not None


async def up(conn, dialect: str) -> None:
    if await _column_exists(conn, "org_settings", "auto_invoice", dialect):
        logger.info("Migration 002: org_settings.auto_invoice already exists — skipping")
        return

    if dialect == "sqlite":
        await conn.execute(
            "ALTER TABLE org_settings ADD COLUMN auto_invoice INTEGER NOT NULL DEFAULT 0"
        )
    else:
        await conn.execute(
            "ALTER TABLE org_settings ADD COLUMN auto_invoice INTEGER NOT NULL DEFAULT 0"
        )
    await conn.commit()
    logger.info("Migration 002: added org_settings.auto_invoice")
