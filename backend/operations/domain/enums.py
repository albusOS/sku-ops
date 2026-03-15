"""Operations domain enums — single source of truth for operations status values.

Every status comparison, DB literal, and API response in the operations context
must reference these enums. Raw string literals for statuses are forbidden.
"""

from enum import StrEnum


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    INVOICED = "invoiced"
    PAID = "paid"


class MaterialRequestStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
