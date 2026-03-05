"""Return models — reversing all or part of a material withdrawal."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from kernel.entity import AuditedEntity


class ReturnReason(str, Enum):
    WRONG_ITEM = "wrong_item"
    DEFECTIVE = "defective"
    OVERORDER = "overorder"
    JOB_CANCELLED = "job_cancelled"
    OTHER = "other"


class ReturnItem(BaseModel):
    """A line on a return — references the original withdrawal item."""
    model_config = ConfigDict(extra="ignore")

    product_id: str
    sku: str
    name: str
    quantity: float
    unit_price: float = 0.0
    cost: float = 0.0
    unit: str = "each"
    reason: ReturnReason = ReturnReason.OTHER
    notes: str = ""

    @property
    def refund_amount(self) -> float:
        return round(self.unit_price * self.quantity, 2)

    @property
    def cost_total(self) -> float:
        return round(self.cost * self.quantity, 2)


class ReturnCreate(BaseModel):
    """API payload to create a return."""
    withdrawal_id: str
    items: List[ReturnItem]
    reason: ReturnReason = ReturnReason.OTHER
    notes: Optional[str] = None


class MaterialReturn(AuditedEntity):
    """A return against a previous withdrawal."""
    withdrawal_id: str
    contractor_id: str
    contractor_name: str = ""
    billing_entity: str = ""
    job_id: str = ""
    items: List[ReturnItem]
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    cost_total: float = 0.0
    reason: ReturnReason = ReturnReason.OTHER
    notes: Optional[str] = None
    credit_note_id: Optional[str] = None
    processed_by_id: str = ""
    processed_by_name: str = ""

    def compute_totals(self, tax_rate: float = 0.10) -> None:
        self.subtotal = sum(i.refund_amount for i in self.items)
        self.cost_total = sum(i.cost_total for i in self.items)
        self.tax = round(self.subtotal * tax_rate, 2)
        self.total = round(self.subtotal + self.tax, 2)
