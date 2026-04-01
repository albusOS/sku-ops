"""SKU write/mutation operations."""

import json
from datetime import UTC, datetime

from catalog.domain.sku import Sku
from catalog.infrastructure.sku_repo import get_by_id
from shared.infrastructure.db import get_org_id, sql_execute


async def insert(sku: Sku) -> None:
    sku_dict = sku.model_dump()
    org_id = sku_dict.get("organization_id") or get_org_id()
    await sql_execute(
        """INSERT INTO skus (id, sku, product_family_id, name, description, price, cost, quantity, min_stock,
           category_id, category_name, barcode, vendor_barcode,
           base_unit, sell_uom, pack_qty, purchase_uom, purchase_pack_qty,
           variant_label, spec, grade, variant_attrs,
           organization_id, created_at, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25)""",
        (
            sku_dict["id"],
            sku_dict["sku"],
            sku_dict["product_family_id"],
            sku_dict["name"],
            sku_dict.get("description", ""),
            sku_dict["price"],
            sku_dict.get("cost", 0),
            sku_dict.get("quantity", 0),
            sku_dict.get("min_stock", 5),
            sku_dict["category_id"],
            sku_dict.get("category_name", ""),
            sku_dict.get("barcode"),
            sku_dict.get("vendor_barcode"),
            sku_dict.get("base_unit", "each"),
            sku_dict.get("sell_uom", "each"),
            sku_dict.get("pack_qty", 1),
            sku_dict.get("purchase_uom", "each"),
            sku_dict.get("purchase_pack_qty", 1),
            sku_dict.get("variant_label", ""),
            sku_dict.get("spec", ""),
            sku_dict.get("grade", ""),
            json.dumps(sku_dict.get("variant_attrs") or {}),
            org_id,
            sku_dict.get("created_at") or datetime.now(UTC),
            sku_dict.get("updated_at") or datetime.now(UTC),
        ),
    )


async def update(sku_id: str, updates: dict) -> Sku | None:
    org_id = get_org_id()
    n = 1
    set_parts = [f"updated_at = ${n}"]
    values = [updates.get("updated_at", datetime.now(UTC))]
    n += 1
    for key in (
        "sku",
        "name",
        "description",
        "price",
        "cost",
        "quantity",
        "min_stock",
        "category_id",
        "category_name",
        "product_family_id",
        "barcode",
        "vendor_barcode",
        "base_unit",
        "sell_uom",
        "pack_qty",
        "purchase_uom",
        "purchase_pack_qty",
        "variant_label",
        "spec",
        "grade",
    ):
        if key in updates and updates[key] is not None:
            set_parts.append(f"{key} = ${n}")
            values.append(updates[key])
            n += 1

    if "variant_attrs" in updates and updates["variant_attrs"] is not None:
        set_parts.append(f"variant_attrs = ${n}")
        values.append(json.dumps(updates["variant_attrs"]))
        n += 1
    if len(set_parts) <= 1:
        return await get_by_id(sku_id)
    values.append(sku_id)
    where = f"WHERE id = ${n} AND organization_id = ${n + 1}"
    values.append(org_id)
    query = "UPDATE skus SET "
    query += ", ".join(set_parts)
    query += " " + where
    await sql_execute(query, values)
    return await get_by_id(sku_id)


async def delete(sku_id: str) -> int:
    org_id = get_org_id()
    now = datetime.now(UTC)
    params: list = [now, sku_id]
    where = "WHERE id = $2 AND deleted_at IS NULL AND organization_id = $3"
    params.append(org_id)
    query = "UPDATE skus SET deleted_at = $1 "
    query += where
    cursor = await sql_execute(query, params)
    return cursor.rowcount


async def atomic_decrement(sku_id: str, quantity: float, updated_at: datetime) -> Sku | None:
    """Decrement quantity only if >= requested. Returns updated row or None if insufficient."""
    org_id = get_org_id()
    params: list = [quantity, updated_at, sku_id, quantity]
    where = "WHERE id = $3 AND quantity >= $4 AND organization_id = $5"
    params.append(org_id)
    query = "UPDATE skus SET quantity = quantity - $1, updated_at = $2 "
    query += where
    cursor = await sql_execute(query, params)
    if cursor.rowcount == 0:
        return None
    return await get_by_id(sku_id)


async def increment_quantity(sku_id: str, quantity: float, updated_at: datetime) -> None:
    """Rollback: add quantity back."""
    org_id = get_org_id()
    params: list = [quantity, updated_at, sku_id]
    where = "WHERE id = $3 AND organization_id = $4"
    params.append(org_id)
    query = "UPDATE skus SET quantity = quantity + $1, updated_at = $2 "
    query += where
    await sql_execute(query, params)


async def add_quantity(sku_id: str, quantity: float, updated_at: datetime) -> Sku | None:
    """Add quantity (receiving) and return updated row."""
    org_id = get_org_id()
    params: list = [quantity, updated_at, sku_id]
    where = "WHERE id = $3 AND organization_id = $4"
    params.append(org_id)
    query = "UPDATE skus SET quantity = quantity + $1, updated_at = $2 "
    query += where
    await sql_execute(query, params)
    return await get_by_id(sku_id)


async def atomic_adjust(
    sku_id: str,
    quantity_delta: float,
    updated_at: datetime,
) -> Sku | None:
    """Atomically adjust quantity by delta (+ or -).
    Returns updated row or None if adjustment would result in negative stock.
    """
    org_id = get_org_id()
    params: list = [quantity_delta, updated_at, sku_id, quantity_delta]
    where = "WHERE id = $3 AND quantity + $4 >= 0 AND organization_id = $5"
    params.append(org_id)
    query = "UPDATE skus SET quantity = quantity + $1, updated_at = $2 "
    query += where
    cursor = await sql_execute(query, params)
    if cursor.rowcount == 0:
        return None
    return await get_by_id(sku_id)
