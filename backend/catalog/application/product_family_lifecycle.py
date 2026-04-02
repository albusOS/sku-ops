"""Product family lifecycle: create, update, delete parent product concepts.

A Product groups related SKUs. Deleting a product cascades to soft-delete
all child SKUs and their vendor items.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from catalog.domain.product_family import ProductFamily
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import CatalogChanged
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _db_catalog():
    return get_database_manager().catalog


async def create_product(
    name: str,
    category_id: str,
    category_name: str = "",
    description: str = "",
) -> ProductFamily:
    """Create a product parent record."""
    org_id = get_org_id()
    cat = _db_catalog()
    dept = await cat.get_department_by_id(category_id, org_id)
    if not dept:
        raise ResourceNotFoundError("Department", category_id)

    product = ProductFamily(
        name=name,
        description=description,
        category_id=category_id,
        category_name=category_name or dept.name,
        organization_id=org_id,
    )

    async with transaction():
        await cat.insert_product_family(product)

    await dispatch(
        CatalogChanged(org_id=org_id, sku_ids=(), change_type="created")
    )
    logger.info(
        "product.created",
        extra={
            "org_id": org_id,
            "product_id": product.id,
            "product_name": product.name,
        },
    )
    return product


async def update_product(
    product_id: str,
    updates: dict,
) -> ProductFamily:
    """Update a product parent record."""
    org_id = get_org_id()
    cat = _db_catalog()
    product = await cat.get_product_family_by_id(product_id, org_id)
    if not product:
        raise ResourceNotFoundError("Product", product_id)

    if "category_id" in updates:
        dept = await cat.get_department_by_id(updates["category_id"], org_id)
        if dept:
            updates["category_name"] = dept.name

    updates["updated_at"] = datetime.now(UTC)

    async with transaction():
        result = await cat.update_product_family(product_id, org_id, updates)
    if not result:
        raise ResourceNotFoundError("Product", product_id)

    child_skus = await cat.find_skus_by_product_family(org_id, product_id)
    child_sku_ids = tuple(s.id for s in child_skus)
    await dispatch(
        CatalogChanged(
            org_id=org_id, sku_ids=child_sku_ids, change_type="updated"
        )
    )
    logger.info(
        "product.updated", extra={"org_id": org_id, "product_id": product_id}
    )
    return result


async def delete_product(product_id: str) -> None:
    """Soft-delete a product and cascade to all child SKUs and their vendor items."""
    org_id = get_org_id()
    cat = _db_catalog()
    product = await cat.get_product_family_by_id(product_id, org_id)
    if not product:
        raise ResourceNotFoundError("Product", product_id)

    child_skus = await cat.find_skus_by_product_family(org_id, product_id)

    child_sku_ids = tuple(s.id for s in child_skus)
    async with transaction():
        for s in child_skus:
            await cat.soft_delete_vendor_items_by_sku(s.id, org_id)
            await cat.soft_delete_sku(s.id, org_id)
            if s.category_id:
                await cat.increment_department_sku_count(
                    s.category_id, org_id, -1
                )
        await cat.soft_delete_product_family(product_id, org_id)

    await dispatch(
        CatalogChanged(
            org_id=org_id, sku_ids=child_sku_ids, change_type="deleted"
        )
    )
    logger.info(
        "product.deleted",
        extra={
            "org_id": org_id,
            "product_id": product_id,
            "cascade_sku_count": len(child_skus),
        },
    )
