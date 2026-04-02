"""
SKU lifecycle service: single source of truth for create, update, delete.

All SKU creation (API, CSV import, document import, PO receiving) flows
through this service. Uses transactions to ensure sku_count and stock
ledger stay in sync.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from catalog.application.product_family_lifecycle import (
    create_product as create_product_parent,
)
from catalog.application.sku_service import generate_sku
from catalog.domain.errors import (
    DuplicateBarcodeError,
    DuplicateSkuError,
    InvalidBarcodeError,
)
from catalog.domain.sku import Sku, SkuUpdate
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.barcode import validate_barcode
from shared.kernel.domain_events import CatalogChanged
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _db_catalog():
    return get_database_manager().catalog


StockChangesFn = Callable[..., Awaitable[None]] | None


async def create_sku(
    product_family_id: str,
    category_id: str,
    category_name: str,
    name: str,
    description: str = "",
    price: float = 0,
    cost: float = 0,
    quantity: float = 0,
    min_stock: int = 5,
    barcode: str | None = None,
    base_unit: str = "each",
    sell_uom: str = "each",
    pack_qty: int = 1,
    purchase_uom: str = "each",
    purchase_pack_qty: int = 1,
    variant_label: str = "",
    spec: str = "",
    grade: str = "",
    variant_attrs: dict | None = None,
    user_id: str | None = None,
    user_name: str = "",
    *,
    on_stock_import: StockChangesFn = None,
) -> Sku:
    """Create a SKU under an existing product parent.

    Generates the SKU code, validates/derives barcode, increments counters,
    and optionally records initial stock. All in a single transaction.
    """
    org_id = get_org_id()
    cat = _db_catalog()
    department = await cat.get_department_by_id(category_id, org_id)
    if not department:
        raise ResourceNotFoundError("Department", category_id)

    family = (
        await cat.get_product_family_by_id(product_family_id, org_id)
        if product_family_id
        else None
    )
    family_name = family.name if family else name
    sku_code = await generate_sku(
        department.code, product_family_id, family_name
    )
    barcode_val = (barcode or "").strip() or sku_code

    if barcode_val and barcode_val.isdigit():
        valid, _ = validate_barcode(barcode_val)
        if not valid:
            raise InvalidBarcodeError(
                barcode_val,
                "Invalid UPC (12 digits) or EAN-13 (13 digits) check digit",
            )
    existing = await cat.find_sku_by_barcode(org_id, barcode_val)
    if existing:
        raise DuplicateBarcodeError(barcode_val, existing.name)

    sku = Sku(
        sku=sku_code,
        product_family_id=product_family_id,
        name=name,
        description=description,
        price=price,
        cost=cost,
        quantity=quantity,
        min_stock=min_stock,
        category_id=category_id,
        category_name=category_name,
        barcode=barcode_val,
        base_unit=base_unit,
        sell_uom=sell_uom,
        pack_qty=pack_qty,
        purchase_uom=purchase_uom,
        purchase_pack_qty=purchase_pack_qty,
        variant_label=variant_label,
        spec=spec,
        grade=grade,
        variant_attrs=variant_attrs or {},
        organization_id=org_id,
    )

    async with transaction():
        await cat.insert_sku(sku)
        await cat.increment_department_sku_count(category_id, org_id, 1)
        await cat.increment_product_sku_count(product_family_id, org_id, 1)
        if quantity > 0 and user_id and on_stock_import:
            await on_stock_import(
                sku_id=sku.id,
                sku=sku.sku,
                product_name=sku.name,
                quantity=quantity,
                user_id=user_id,
                user_name=user_name,
            )

    await dispatch(
        CatalogChanged(org_id=org_id, sku_ids=(sku.id,), change_type="created")
    )
    logger.info(
        "sku.created",
        extra={
            "org_id": org_id,
            "sku_id": sku.id,
            "sku": sku.sku,
            "sku_name": sku.name,
            "user_id": user_id,
        },
    )
    return sku


async def create_product_with_sku(
    category_id: str,
    category_name: str,
    name: str,
    description: str = "",
    price: float = 0,
    cost: float = 0,
    quantity: float = 0,
    min_stock: int = 5,
    barcode: str | None = None,
    base_unit: str = "each",
    sell_uom: str = "each",
    pack_qty: int = 1,
    purchase_uom: str = "each",
    purchase_pack_qty: int = 1,
    variant_label: str = "",
    spec: str = "",
    grade: str = "",
    variant_attrs: dict | None = None,
    user_id: str | None = None,
    user_name: str = "",
    *,
    on_stock_import: StockChangesFn = None,
) -> Sku:
    """Convenience: create a Product parent and its first SKU atomically.

    Used by the API create endpoint and PO receiving when creating new items.
    """
    product = await create_product_parent(
        name=name,
        category_id=category_id,
        category_name=category_name,
        description=description,
    )
    return await create_sku(
        product_family_id=product.id,
        category_id=category_id,
        category_name=category_name,
        name=name,
        description=description,
        price=price,
        cost=cost,
        quantity=quantity,
        min_stock=min_stock,
        barcode=barcode,
        base_unit=base_unit,
        sell_uom=sell_uom,
        pack_qty=pack_qty,
        purchase_uom=purchase_uom,
        purchase_pack_qty=purchase_pack_qty,
        variant_label=variant_label,
        spec=spec,
        grade=grade,
        variant_attrs=variant_attrs,
        user_id=user_id,
        user_name=user_name,
        on_stock_import=on_stock_import,
    )


async def update_sku(
    sku_id: str,
    updates: SkuUpdate,
    current_sku: Sku | None = None,
) -> Sku:
    """Update a SKU. Resolves category name changes and adjusts counters."""
    org_id = get_org_id()
    cat = _db_catalog()
    sku = current_sku or await cat.get_sku_by_id(sku_id, org_id)
    if not sku:
        raise ResourceNotFoundError("Sku", sku_id)

    update_data = updates.model_dump(exclude_none=True)
    # quantity is owned by the inventory ledger — never allow a direct overwrite
    # via the catalog edit path. Stock changes must go through inventory adjustment,
    # receiving, or withdrawal flows, which maintain the stock_transactions audit trail.
    update_data.pop("quantity", None)
    update_data["updated_at"] = datetime.now(UTC)

    if "barcode" in update_data:
        barcode_raw = update_data["barcode"]
        barcode_val = (barcode_raw or "").strip() or sku.sku
        update_data["barcode"] = barcode_val or sku.sku
        current_barcode = (sku.barcode or "").strip()
        if update_data["barcode"] != current_barcode:
            if update_data["barcode"] and update_data["barcode"].isdigit():
                valid, _ = validate_barcode(update_data["barcode"])
                if not valid:
                    raise InvalidBarcodeError(
                        update_data["barcode"],
                        "Invalid UPC (12 digits) or EAN-13 (13 digits) check digit",
                    )
            existing = await cat.find_sku_by_barcode(
                org_id,
                update_data["barcode"],
                exclude_sku_id=sku_id,
            )
            if existing:
                raise DuplicateBarcodeError(
                    update_data["barcode"], existing.name
                )

    if "sku" in update_data:
        new_code = update_data["sku"].strip()
        if new_code and new_code != sku.sku:
            existing = await cat.find_sku_by_code(org_id, new_code)
            if existing:
                raise DuplicateSkuError(new_code, existing.name)
            update_data["sku"] = new_code
        else:
            update_data.pop("sku")

    if "category_id" in update_data:
        department = await cat.get_department_by_id(
            update_data["category_id"], org_id
        )
        if department:
            update_data["category_name"] = department.name

    async with transaction():
        if "category_id" in update_data:
            old_cat = sku.category_id
            new_cat = update_data["category_id"]
            if old_cat != new_cat:
                if old_cat:
                    await cat.increment_department_sku_count(
                        old_cat, org_id, -1
                    )
                if new_cat:
                    await cat.increment_department_sku_count(new_cat, org_id, 1)

        result = await cat.update_sku(sku_id, org_id, update_data)
    if not result:
        raise ResourceNotFoundError("Sku", sku_id)

    await dispatch(
        CatalogChanged(org_id=org_id, sku_ids=(sku_id,), change_type="updated")
    )
    logger.info("sku.updated", extra={"org_id": org_id, "sku_id": sku_id})
    return result


async def adopt_sku(sku_id: str, new_family_id: str) -> Sku:
    """Move a SKU from its current product family to a new one.

    Atomically updates the SKU's product_family_id and adjusts sku_count
    on both the old and new families.
    """
    org_id = get_org_id()
    cat = _db_catalog()
    sku = await cat.get_sku_by_id(sku_id, org_id)
    if not sku:
        raise ResourceNotFoundError("Sku", sku_id)

    new_family = await cat.get_product_family_by_id(new_family_id, org_id)
    if not new_family:
        raise ResourceNotFoundError("ProductFamily", new_family_id)

    old_family_id = sku.product_family_id

    async with transaction():
        result = await cat.update_sku(
            sku_id,
            org_id,
            {
                "product_family_id": new_family_id,
                "category_id": new_family.category_id,
                "category_name": new_family.category_name,
                "updated_at": datetime.now(UTC),
            },
        )
        if old_family_id:
            await cat.increment_product_sku_count(old_family_id, org_id, -1)
        await cat.increment_product_sku_count(new_family_id, org_id, 1)
        if old_family_id and sku.category_id != new_family.category_id:
            if sku.category_id:
                await cat.increment_department_sku_count(
                    sku.category_id, org_id, -1
                )
            if new_family.category_id:
                await cat.increment_department_sku_count(
                    new_family.category_id, org_id, 1
                )

    await dispatch(
        CatalogChanged(org_id=org_id, sku_ids=(sku_id,), change_type="updated")
    )
    logger.info(
        "sku.adopted",
        extra={
            "org_id": org_id,
            "sku_id": sku_id,
            "old_family_id": old_family_id,
            "new_family_id": new_family_id,
        },
    )
    if not result:
        raise ResourceNotFoundError("Sku", sku_id)
    return result


async def delete_sku(sku_id: str) -> None:
    """Delete a SKU, update counters, and soft-delete associated vendor items."""
    org_id = get_org_id()
    cat = _db_catalog()
    sku = await cat.get_sku_by_id(sku_id, org_id)
    if not sku:
        raise ResourceNotFoundError("Sku", sku_id)

    async with transaction():
        await cat.soft_delete_vendor_items_by_sku(sku_id, org_id)
        await cat.soft_delete_sku(sku_id, org_id)
        if sku.category_id:
            await cat.increment_department_sku_count(
                sku.category_id, org_id, -1
            )
        if sku.product_family_id:
            await cat.increment_product_sku_count(
                sku.product_family_id, org_id, -1
            )

    await dispatch(
        CatalogChanged(org_id=org_id, sku_ids=(sku_id,), change_type="deleted")
    )
    logger.info("sku.deleted", extra={"org_id": org_id, "sku_id": sku_id})
