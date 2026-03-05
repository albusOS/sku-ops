"""Document domain models for receipt/invoice parsing."""
from typing import List, Optional

from pydantic import BaseModel


class DocumentLineItem(BaseModel):
    """Line item from a parsed document — local to the documents context."""
    name: str
    original_sku: Optional[str] = None
    quantity: float = 1
    ordered_qty: Optional[float] = None
    delivered_qty: Optional[float] = None
    price: float = 0.0
    cost: Optional[float] = None
    base_unit: str = "each"
    sell_uom: str = "each"
    pack_qty: int = 1
    suggested_department: Optional[str] = None
    product_id: Optional[str] = None
    selected: bool = True
    ai_parsed: bool = False


class DocumentImportRequest(BaseModel):
    """Request to import a parsed document into a purchase order."""
    vendor_name: str
    create_vendor_if_missing: bool = True
    department_id: Optional[str] = None
    products: List[DocumentLineItem]
