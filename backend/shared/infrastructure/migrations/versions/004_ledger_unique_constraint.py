"""Migration 004 — Ledger deduplication guard (no-op).

Originally intended to add a UNIQUE index on financial_ledger. However,
a single withdrawal/return produces multiple ledger rows with the same
(reference_type, reference_id, account) — one per line item. DB-level
uniqueness would reject legitimate multi-item entries.

Deduplication is handled at two other levels:
  - ``entries_exist()`` app-level guard in ledger_service
  - ``@idempotent`` decorator on event handlers

This migration is kept as a no-op to preserve migration numbering.
"""

import logging

logger = logging.getLogger(__name__)


async def up(conn, dialect: str) -> None:  # noqa: ARG001
    logger.info("Migration 004: no-op (ledger dedup handled at app level)")
