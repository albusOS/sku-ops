"""Material withdrawal (POS) models."""
from typing import List, Optional

from pydantic import BaseModel

from kernel.entity import Entity
from kernel.types import LineItem


class WithdrawalItem(LineItem):
    """A line item on a material withdrawal — extends the universal LineItem."""
    pass


class MaterialWithdrawalCreate(BaseModel):
    items: List[WithdrawalItem]
    job_id: str
    service_address: str
    notes: Optional[str] = None


class MaterialWithdrawal(Entity):
    items: List[WithdrawalItem]
    job_id: str
    service_address: str
    notes: Optional[str] = None
    subtotal: float
    tax: float
    total: float
    cost_total: float
    contractor_id: str
    contractor_name: str = ""
    contractor_company: str = ""
    billing_entity: str = ""
    payment_status: str = "unpaid"
    invoice_id: Optional[str] = None
    paid_at: Optional[str] = None
    processed_by_id: str
    processed_by_name: str = ""

    def compute_totals(self, tax_rate: float = 0.10) -> None:
        """Calculate subtotal, tax, total, and cost_total from line items."""
        self.subtotal = sum(i.subtotal for i in self.items)
        self.cost_total = sum(i.cost_total for i in self.items)
        self.tax = round(self.subtotal * tax_rate, 2)
        self.total = round(self.subtotal + self.tax, 2)
