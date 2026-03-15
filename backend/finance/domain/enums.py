"""Finance domain enums — single source of truth for all finance status values.

Every status comparison, DB literal, and API response in the finance context
must reference these enums. Raw string literals for statuses are forbidden.
"""

from enum import StrEnum


class InvoiceStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    PAID = "paid"
    DELETED = "deleted"


class CreditNoteStatus(StrEnum):
    DRAFT = "draft"
    APPLIED = "applied"
    VOID = "void"


class XeroSyncStatus(StrEnum):
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    FAILED = "failed"
    MISMATCH = "mismatch"
    COGS_STALE = "cogs_stale"


class FiscalPeriodStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
