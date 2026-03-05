"""Document domain models for receipt/invoice parsing."""
from typing import List, Optional

from pydantic import BaseModel

from purchasing.domain.purchase_order import POItemCreate


class DocumentImportRequest(BaseModel):
    """Request to import a parsed document into a purchase order."""
    vendor_name: str
    create_vendor_if_missing: bool = True
    department_id: Optional[str] = None
    products: List[POItemCreate]
