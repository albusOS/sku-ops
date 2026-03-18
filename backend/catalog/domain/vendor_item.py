"""VendorItem domain model.

A VendorItem links a vendor to a specific SKU, recording the vendor's
own part number, purchase UOM, cost, lead time, and preferred status.
One SKU may have many VendorItems (multi-sourcing).
"""

from pydantic import field_validator

from shared.kernel.entity import AuditedEntity


class VendorItem(AuditedEntity):
    vendor_id: str
    vendor_name: str = ""
    sku_id: str
    vendor_sku: str | None = None
    purchase_uom: str = "each"
    purchase_pack_qty: int = 1
    cost: float = 0.0
    lead_time_days: int | None = None
    moq: float | None = None
    is_preferred: bool = False
    notes: str | None = None

    @field_validator("purchase_uom")
    @classmethod
    def normalise_uom(cls, v: str) -> str:
        v = (v or "each").lower().strip()
        if not v:
            return "each"
        return v

    @field_validator("purchase_pack_qty")
    @classmethod
    def valid_pack_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("purchase_pack_qty must be at least 1")
        return v
