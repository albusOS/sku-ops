"""Catalog application queries — safe for cross-context import.

Other bounded contexts import from here, never from catalog.infrastructure directly.
Thin delegation to CatalogDatabaseService / PurchasingDatabaseService.
"""

from datetime import datetime

from catalog.domain.department import Department
from catalog.domain.product_family import ProductFamily
from catalog.domain.sku import Sku, SkuUpdate
from catalog.domain.unit_of_measure import UnitOfMeasure
from catalog.domain.vendor import Vendor
from catalog.domain.vendor_item import VendorItem
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager

# ── Product family (parent) queries ──────────────────────────────────────────


async def list_product_families(
    category_id: str | None = None,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[ProductFamily]:
    org_id = get_org_id()
    return await get_database_manager().catalog.list_product_families(
        org_id,
        category_id=category_id,
        search=search,
        limit=limit,
        offset=offset,
    )


async def count_product_families(
    category_id: str | None = None,
    search: str | None = None,
) -> int:
    org_id = get_org_id()
    return await get_database_manager().catalog.count_product_families(
        org_id,
        category_id=category_id,
        search=search,
    )


async def get_product_family_by_id(product_id: str) -> ProductFamily | None:
    return await get_database_manager().catalog.get_product_family_by_id(
        product_id, get_org_id()
    )


# ── SKU queries ──────────────────────────────────────────────────────────────


async def list_skus(
    category_id: str | None = None,
    search: str | None = None,
    low_stock: bool = False,
    limit: int | None = None,
    offset: int = 0,
    product_family_id: str | None = None,
) -> list[Sku]:
    org_id = get_org_id()
    return await get_database_manager().catalog.list_skus(
        org_id,
        category_id=category_id,
        search=search,
        low_stock=low_stock,
        limit=limit,
        offset=offset,
        product_family_id=product_family_id,
    )


async def count_skus(
    category_id: str | None = None,
    search: str | None = None,
    low_stock: bool = False,
    product_family_id: str | None = None,
) -> int:
    org_id = get_org_id()
    return await get_database_manager().catalog.count_skus(
        org_id,
        category_id=category_id,
        search=search,
        low_stock=low_stock,
        product_family_id=product_family_id,
    )


async def get_sku_by_id(sku_id: str) -> Sku | None:
    return await get_database_manager().catalog.get_sku_by_id(
        sku_id, get_org_id()
    )


async def find_sku_by_sku_code(sku: str) -> Sku | None:
    return await get_database_manager().catalog.find_sku_by_code(
        get_org_id(), sku
    )


async def find_sku_by_barcode(
    barcode: str,
    exclude_sku_id: str | None = None,
) -> Sku | None:
    return await get_database_manager().catalog.find_sku_by_barcode(
        get_org_id(), barcode, exclude_sku_id=exclude_sku_id
    )


async def list_skus_by_product_family(product_family_id: str) -> list[Sku]:
    return await get_database_manager().catalog.find_skus_by_product_family(
        get_org_id(), product_family_id
    )


async def count_all_skus() -> int:
    return await get_database_manager().catalog.count_all_skus(get_org_id())


async def count_low_stock() -> int:
    return await get_database_manager().catalog.count_low_stock_skus(
        get_org_id()
    )


async def list_low_stock(limit: int = 10) -> list[Sku]:
    return await get_database_manager().catalog.list_low_stock_skus(
        get_org_id(), limit=limit
    )


# ── SKU commands (used by inventory / purchasing / documents) ────────────────


async def update_sku(sku_id: str, updates: SkuUpdate) -> Sku | None:
    async with transaction():
        return await get_database_manager().catalog.update_sku(
            sku_id, get_org_id(), updates.model_dump(exclude_none=True)
        )


async def atomic_decrement_sku(
    sku_id: str, quantity: float, updated_at: datetime
) -> Sku | None:
    async with transaction():
        return await get_database_manager().catalog.sku_atomic_decrement(
            sku_id, get_org_id(), quantity, updated_at
        )


async def increment_sku_quantity(
    sku_id: str, quantity: float, updated_at: datetime
) -> None:
    async with transaction():
        await get_database_manager().catalog.sku_increment_quantity(
            sku_id, get_org_id(), quantity, updated_at
        )


async def add_sku_quantity(
    sku_id: str, quantity: float, updated_at: datetime
) -> Sku | None:
    async with transaction():
        return await get_database_manager().catalog.sku_add_quantity(
            sku_id, get_org_id(), quantity, updated_at
        )


async def atomic_adjust_sku(
    sku_id: str, quantity_delta: float, updated_at: datetime
) -> Sku | None:
    async with transaction():
        return await get_database_manager().catalog.sku_atomic_adjust(
            sku_id, get_org_id(), quantity_delta, updated_at
        )


# ── VendorItem queries ───────────────────────────────────────────────────────


async def get_vendor_items_for_skus(
    sku_ids: list[str],
) -> dict[str, list[VendorItem]]:
    items = await get_database_manager().catalog.list_vendor_items_by_skus(
        get_org_id(), sku_ids
    )
    grouped: dict[str, list[VendorItem]] = {}
    for item in items:
        grouped.setdefault(item.sku_id, []).append(item)
    return grouped


async def find_vendor_item_by_vendor_and_sku_code(
    vendor_id: str, vendor_sku: str
) -> VendorItem | None:
    return (
        await get_database_manager().catalog.find_vendor_item_by_vendor_and_sku(
            get_org_id(), vendor_id, vendor_sku
        )
    )


async def find_vendor_item_by_sku_and_vendor(
    sku_id: str, vendor_id: str
) -> VendorItem | None:
    return (
        await get_database_manager().catalog.find_vendor_item_by_sku_and_vendor(
            sku_id, vendor_id, get_org_id()
        )
    )


async def find_product_by_original_sku_and_vendor(
    original_sku: str, vendor_id: str
) -> Sku | None:
    """Resolve vendor part number → VendorItem → SKU."""
    vi = await find_vendor_item_by_vendor_and_sku_code(vendor_id, original_sku)
    if not vi:
        return None
    return await get_sku_by_id(vi.sku_id)


async def find_product_by_name_and_vendor(
    name: str, vendor_id: str
) -> Sku | None:
    """Name-based fallback for PO matching."""
    return await get_database_manager().catalog.find_sku_by_name_and_vendor(
        get_org_id(), name, vendor_id
    )


async def sku_vendor_options(sku_id: str) -> list[dict]:
    """All vendors for a SKU with cost, lead time, moq, preferred, and last PO date."""
    org_id = get_org_id()
    cat = get_database_manager().catalog
    pur = get_database_manager().purchasing
    items = await cat.list_vendor_items_by_sku(sku_id, org_id)
    if not items:
        return []

    last_by_vendor = await pur.last_po_created_at_by_vendor_for_sku(
        org_id, sku_id
    )
    result = []
    for vi in items:
        vendor = await cat.get_vendor_by_id(vi.vendor_id, org_id)
        result.append(
            {
                "vendor_id": vi.vendor_id,
                "vendor_name": vendor.name if vendor else vi.vendor_name,
                "vendor_sku": vi.vendor_sku,
                "cost": vi.cost,
                "lead_time_days": vi.lead_time_days,
                "moq": vi.moq,
                "is_preferred": vi.is_preferred,
                "purchase_uom": vi.purchase_uom,
                "purchase_pack_qty": vi.purchase_pack_qty,
                "last_po_date": last_by_vendor.get(vi.vendor_id),
            }
        )
    return result


# ── Department queries ───────────────────────────────────────────────────────


async def list_departments() -> list[Department]:
    return await get_database_manager().catalog.list_departments(get_org_id())


async def get_department_by_id(dept_id: str) -> Department | None:
    return await get_database_manager().catalog.get_department_by_id(
        dept_id, get_org_id()
    )


async def get_department_by_code(code: str) -> Department | None:
    return await get_database_manager().catalog.get_department_by_code(
        code, get_org_id()
    )


async def insert_department(department: Department | dict) -> None:
    d = (
        Department.model_validate(department)
        if isinstance(department, dict)
        else department
    )
    async with transaction():
        await get_database_manager().catalog.insert_department(d)


async def update_department(
    dept_id: str,
    name: str,
    description: str,
) -> Department | None:
    async with transaction():
        return await get_database_manager().catalog.update_department(
            dept_id, get_org_id(), name, description
        )


async def delete_department(dept_id: str) -> int:
    async with transaction():
        return await get_database_manager().catalog.soft_delete_department(
            dept_id, get_org_id()
        )


async def count_skus_by_department(dept_id: str) -> int:
    return await get_database_manager().catalog.count_skus_by_department(
        dept_id, get_org_id()
    )


# ── Unit of measure queries ──────────────────────────────────────────────


async def list_units_of_measure() -> list[UnitOfMeasure]:
    return await get_database_manager().catalog.list_uoms(get_org_id())


async def get_unit_by_code(code: str) -> UnitOfMeasure | None:
    return await get_database_manager().catalog.get_uom_by_code(
        get_org_id(), code
    )


async def get_unit_by_id(uom_id: str) -> UnitOfMeasure | None:
    return await get_database_manager().catalog.get_uom_by_id(
        uom_id, get_org_id()
    )


async def insert_unit(uom: UnitOfMeasure) -> None:
    async with transaction():
        await get_database_manager().catalog.insert_uom(uom)


async def delete_unit(uom_id: str) -> int:
    async with transaction():
        return await get_database_manager().catalog.soft_delete_uom(
            uom_id, get_org_id()
        )


async def get_known_unit_codes() -> frozenset[str]:
    """Return all active unit codes visible to the current org (global + org-specific)."""
    units = await list_units_of_measure()
    return frozenset(u.code for u in units)


# ── Vendor queries ───────────────────────────────────────────────────────────


async def list_vendors() -> list[Vendor]:
    return await get_database_manager().catalog.list_vendors(get_org_id())


async def get_vendor_by_id(vendor_id: str) -> Vendor | None:
    return await get_database_manager().catalog.get_vendor_by_id(
        vendor_id, get_org_id()
    )


async def find_vendor_by_name(name: str) -> Vendor | None:
    return await get_database_manager().catalog.find_vendor_by_name(
        get_org_id(), name
    )


async def insert_vendor(vendor: Vendor | dict) -> None:
    v = Vendor.model_validate(vendor) if isinstance(vendor, dict) else vendor
    async with transaction():
        await get_database_manager().catalog.insert_vendor(v)


async def update_vendor(
    vendor_id: str,
    vendor_dict: dict,
) -> Vendor | None:
    async with transaction():
        return await get_database_manager().catalog.update_vendor(
            vendor_id, get_org_id(), vendor_dict
        )


async def delete_vendor(vendor_id: str) -> int:
    async with transaction():
        return await get_database_manager().catalog.soft_delete_vendor(
            vendor_id, get_org_id()
        )


async def count_vendors() -> int:
    return await get_database_manager().catalog.count_vendors(get_org_id())


# ── SKU counter queries ─────────────────────────────────────────────────────


async def get_sku_counters() -> dict:
    return await get_database_manager().catalog.sku_counter_all(get_org_id())


async def get_next_sku_number(product_family_id: str) -> int:
    return await get_database_manager().catalog.sku_counter_next_preview(
        get_org_id(), product_family_id
    )


async def increment_sku_counter_and_get(product_family_id: str) -> int:
    """Consume next counter value for a product family (write)."""
    async with transaction():
        return await get_database_manager().catalog.sku_counter_increment(
            get_org_id(), product_family_id
        )
