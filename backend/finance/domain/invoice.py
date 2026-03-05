"""Invoice models."""
from typing import ClassVar, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from kernel.entity import AuditedEntity
from kernel.types import LineItem


class InvoiceLineItem(BaseModel):
    """A line on an accounting document.

    Uses accounting-standard field names (unit_price, amount) rather than
    the operational names on LineItem (unit_price, subtotal). The underlying
    data is the same — unit_price * quantity = amount.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid4()))
    invoice_id: str = ""
    description: str = ""
    quantity: float = 1.0
    unit_price: float = 0.0
    amount: float = 0.0
    cost: float = 0.0
    product_id: Optional[str] = None
    job_id: Optional[str] = None

    @property
    def margin(self) -> float:
        return self.amount - (self.cost * self.quantity)

    @property
    def margin_pct(self) -> Optional[float]:
        if self.amount <= 0:
            return None
        return round(self.margin / self.amount * 100, 2)

    @classmethod
    def from_line_item(
        cls,
        item: LineItem,
        invoice_id: str = "",
        job_id: Optional[str] = None,
    ) -> "InvoiceLineItem":
        """Convert a universal LineItem to an InvoiceLineItem."""
        return cls(
            invoice_id=invoice_id,
            description=item.name,
            quantity=float(item.quantity),
            unit_price=item.unit_price,
            amount=item.subtotal,
            cost=item.cost,
            product_id=item.product_id,
            job_id=job_id,
        )


class InvoiceCreate(BaseModel):
    """Payload for creating invoice from withdrawal IDs."""
    withdrawal_ids: List[str]


class InvoiceSyncXeroBulk(BaseModel):
    """Payload for bulk sync to Xero."""
    invoice_ids: List[str]


class InvoiceUpdate(BaseModel):
    """Payload for updating invoice."""
    billing_entity: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tax: Optional[float] = None
    line_items: Optional[List[InvoiceLineItem]] = None


class Invoice(AuditedEntity):
    invoice_number: str = ""
    billing_entity: str = ""
    contact_name: str = ""
    contact_email: str = ""
    status: str = "draft"
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    notes: Optional[str] = None
    xero_invoice_id: Optional[str] = None

    ALLOWED_TRANSITIONS: ClassVar[dict[str, set[str]]] = {
        "draft": {"sent", "paid"},
        "sent": {"paid"},
        "paid": set(),
    }

    def can_transition_to(self, target: str) -> bool:
        return target in self.ALLOWED_TRANSITIONS.get(self.status, set())


class InvoiceWithDetails(Invoice):
    """Invoice with line items and linked withdrawals."""
    line_items: List[InvoiceLineItem] = []
    withdrawal_ids: List[str] = []
