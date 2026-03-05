"""Financial ledger — immutable record of every monetary event.

Mirrors the stock_transactions pattern but for dollars instead of units.
Every withdrawal, return, PO receipt, stock adjustment, and payment writes
entries here at event time. Reports read from this table — they never
recompute from operational data.
"""
from enum import Enum
from typing import Optional

from kernel.entity import Entity


class Account(str, Enum):
    REVENUE = "revenue"
    COGS = "cogs"
    TAX_COLLECTED = "tax_collected"
    INVENTORY = "inventory"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ACCOUNTS_PAYABLE = "accounts_payable"
    SHRINKAGE = "shrinkage"


class ReferenceType(str, Enum):
    WITHDRAWAL = "withdrawal"
    RETURN = "return"
    PO_RECEIPT = "po_receipt"
    ADJUSTMENT = "adjustment"
    PAYMENT = "payment"
    CREDIT_NOTE = "credit_note"


class FinancialEntry(Entity):
    """One line in the financial ledger — always created, never mutated."""
    account: Account
    amount: float
    department: Optional[str] = None
    job_id: Optional[str] = None
    billing_entity: Optional[str] = None
    contractor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    product_id: Optional[str] = None
    reference_type: ReferenceType
    reference_id: str
