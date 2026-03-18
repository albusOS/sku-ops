"""Product (parent concept) domain model.

A Product groups related SKUs under a single conceptual item.
Example: "Nitrile Gloves" is the product; "Blue Medium 100ct" and
"Blue Large 100ct" are individual SKUs.
"""

from shared.kernel.entity import AuditedEntity


class ProductFamily(AuditedEntity):
    name: str
    description: str = ""
    category_id: str
    category_name: str = ""
    sku_count: int = 0
