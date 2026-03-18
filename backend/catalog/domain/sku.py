"""SKU (stock-keeping unit) domain models."""

from pydantic import BaseModel, Field, field_validator

from shared.kernel.entity import AuditedEntity

VariantAttrs = dict[str, str]


def _normalise_unit(v: str) -> str:
    """Normalise to non-empty lowercase. Does not validate against DB."""
    v = (v or "each").lower().strip()
    if not v:
        return "each"
    return v


class SkuCreate(BaseModel):
    name: str
    description: str | None = ""
    price: float
    cost: float = 0.0
    quantity: float = 0
    min_stock: int = 5
    category_id: str
    product_family_id: str | None = None
    barcode: str | None = None
    vendor_barcode: str | None = None
    base_unit: str = "each"
    sell_uom: str = "each"
    pack_qty: int = 1
    purchase_uom: str = "each"
    purchase_pack_qty: int = 1
    variant_label: str = ""
    spec: str = ""
    grade: str = ""
    variant_attrs: VariantAttrs = {}

    @field_validator("base_unit", "sell_uom", "purchase_uom")
    @classmethod
    def normalise_unit(cls, v: str) -> str:
        return _normalise_unit(v)

    @field_validator("pack_qty", "purchase_pack_qty")
    @classmethod
    def valid_pack_qty(cls, v: int) -> int:
        if v < 1:
            raise ValueError("pack_qty must be at least 1")
        return v


class SkuUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    price: float | None = None
    cost: float | None = None
    quantity: float | None = None
    min_stock: int | None = None
    category_id: str | None = None
    product_family_id: str | None = None
    barcode: str | None = None
    vendor_barcode: str | None = None
    base_unit: str | None = None
    sell_uom: str | None = None
    pack_qty: int | None = None
    purchase_uom: str | None = None
    purchase_pack_qty: int | None = None
    variant_label: str | None = None
    spec: str | None = None
    grade: str | None = None
    variant_attrs: VariantAttrs | None = None

    @field_validator("base_unit", "sell_uom", "purchase_uom")
    @classmethod
    def normalise_unit(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _normalise_unit(v)

    @field_validator("pack_qty", "purchase_pack_qty")
    @classmethod
    def valid_pack_qty(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("pack_qty must be at least 1")
        return v


class Sku(AuditedEntity):
    sku: str
    product_family_id: str = ""
    name: str
    description: str = ""
    price: float
    cost: float = 0.0
    quantity: float = 0
    min_stock: int = 5
    category_id: str = ""
    category_name: str = ""
    barcode: str | None = None
    vendor_barcode: str | None = None
    base_unit: str = "each"
    sell_uom: str = "each"
    pack_qty: int = 1
    purchase_uom: str = "each"
    purchase_pack_qty: int = 1
    variant_label: str = ""
    spec: str = ""
    grade: str = ""
    variant_attrs: VariantAttrs = Field(default_factory=dict)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.min_stock
