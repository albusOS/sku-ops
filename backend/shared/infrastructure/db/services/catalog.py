"""Catalog context persistence (SQLModel + session-bound SQL)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text

from catalog.domain.department import Department
from catalog.domain.product_family import ProductFamily
from catalog.domain.sku import Sku
from catalog.domain.unit_of_measure import UnitOfMeasure
from catalog.domain.vendor import Vendor
from catalog.domain.vendor_item import VendorItem
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.types.public_sql_model_models import (
    Departments,
    VendorItems,
)
from shared.kernel.errors import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _coerce_uuid_mapping(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def _sku_row_to_domain(row: dict[str, Any]) -> Sku | None:
    if not row:
        return None
    d = dict(row)
    if "min_stock" in d and d["min_stock"] is not None:
        d["min_stock"] = int(d["min_stock"])
    if "variant_attrs" in d and isinstance(d["variant_attrs"], str):
        try:
            d["variant_attrs"] = json.loads(d["variant_attrs"])
        except (ValueError, TypeError):
            d["variant_attrs"] = {}
    for k, v in list(d.items()):
        if isinstance(v, (type(None), str, int, float, bool, dict, list)):
            continue
        d[k] = str(v) if v is not None else None
    return Sku.model_validate(d)


def _row_to_product_family(row: dict[str, Any]) -> ProductFamily | None:
    if not row:
        return None
    return ProductFamily.model_validate(_coerce_uuid_mapping(dict(row)))


def _row_to_vendor(row: dict[str, Any]) -> Vendor | None:
    if not row:
        return None
    return Vendor.model_validate(_coerce_uuid_mapping(dict(row)))


def _row_to_uom(row: dict[str, Any]) -> UnitOfMeasure | None:
    if not row:
        return None
    return UnitOfMeasure.model_validate(_coerce_uuid_mapping(dict(row)))


def _row_to_vendor_item(row: dict[str, Any]) -> VendorItem | None:
    if not row:
        return None
    d = _coerce_uuid_mapping(dict(row))
    if "is_preferred" in d and not isinstance(d["is_preferred"], bool):
        d["is_preferred"] = bool(d["is_preferred"])
    return VendorItem.model_validate(d)


def _dept_row_to_domain(row: Departments) -> Department:
    return Department.model_validate(
        {
            "id": str(row.id),
            "organization_id": str(row.organization_id)
            if row.organization_id
            else "",
            "created_at": row.created_at,
            "name": row.name,
            "code": row.code,
            "description": row.description,
            "sku_count": row.sku_count,
        }
    )


class CatalogDatabaseService(DomainDatabaseService):
    # --- Departments ---
    async def list_departments(self, org_id: str) -> list[Department]:
        """List departments with live sku_count from skus (denormalized column can be stale after bulk import)."""
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """
                    SELECT d.id,
                           d.organization_id,
                           d.created_at,
                           d.name,
                           d.code,
                           d.description,
                           COALESCE(
                               (
                                   SELECT COUNT(*)::integer
                                   FROM skus s
                                   WHERE s.category_id = d.id
                                     AND s.deleted_at IS NULL
                                     AND s.organization_id = d.organization_id
                               ),
                               0
                           ) AS sku_count
                    FROM departments d
                    WHERE d.organization_id = :oid
                      AND d.deleted_at IS NULL
                    ORDER BY d.name ASC
                    """
                ),
                {"oid": oid},
            )
            out: list[Department] = []
            for row in result.mappings().all():
                rid = row["id"]
                roid = row["organization_id"]
                out.append(
                    Department.model_validate(
                        {
                            "id": str(rid),
                            "organization_id": str(roid) if roid else "",
                            "created_at": row["created_at"],
                            "name": row["name"],
                            "code": row["code"],
                            "description": row["description"] or "",
                            "sku_count": int(row["sku_count"] or 0),
                        }
                    )
                )
            return out

    async def get_department_by_id(
        self, dept_id: str, org_id: str
    ) -> Department | None:
        did, oid = as_uuid_required(dept_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(Departments).where(
                    Departments.id == did,
                    Departments.organization_id == oid,
                    Departments.deleted_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            return _dept_row_to_domain(row) if row else None

    async def get_department_by_code(
        self, code: str, org_id: str
    ) -> Department | None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(Departments).where(
                    Departments.code == code.upper(),
                    Departments.organization_id == oid,
                    Departments.deleted_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            return _dept_row_to_domain(row) if row else None

    async def insert_department(self, department: Department) -> None:
        dept_dict = department.model_dump()
        oid = as_uuid_required(dept_dict["organization_id"])
        row = Departments(
            id=as_uuid_required(dept_dict["id"]),
            name=dept_dict["name"],
            code=dept_dict["code"].upper(),
            description=dept_dict.get("description", ""),
            sku_count=dept_dict.get("sku_count", 0),
            organization_id=oid,
            created_at=dept_dict.get("created_at") or datetime.now(UTC),
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def update_department(
        self, dept_id: str, org_id: str, name: str, description: str
    ) -> Department | None:
        did, oid = as_uuid_required(dept_id), as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE departments SET name = :name, description = :desc "
                    "WHERE id = :did AND organization_id = :oid"
                ),
                {
                    "name": name,
                    "desc": description or "",
                    "did": did,
                    "oid": oid,
                },
            )
            await session.execute(
                text(
                    "UPDATE skus SET category_name = :name "
                    "WHERE category_id = :did AND organization_id = :oid"
                ),
                {"name": name, "did": did, "oid": oid},
            )
            await session.execute(
                text(
                    "UPDATE products SET category_name = :name "
                    "WHERE category_id = :did AND organization_id = :oid"
                ),
                {"name": name, "did": did, "oid": oid},
            )
            await self.end_write_session(session)
        return await self.get_department_by_id(dept_id, org_id)

    async def count_skus_by_department(self, dept_id: str, org_id: str) -> int:
        did, oid = as_uuid_required(dept_id), as_uuid_required(org_id)
        async with self.session() as session:
            r = await session.execute(
                text(
                    "SELECT COUNT(*) FROM skus WHERE category_id = :did "
                    "AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"did": did, "oid": oid},
            )
            return int(r.scalar_one() or 0)

    async def soft_delete_department(self, dept_id: str, org_id: str) -> int:
        did, oid = as_uuid_required(dept_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE departments SET deleted_at = :now "
                    "WHERE id = :did AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "did": did, "oid": oid},
            )
            await self.end_write_session(session)
            return res.rowcount or 0

    async def increment_department_sku_count(
        self, dept_id: str, org_id: str, delta: int
    ) -> None:
        did, oid = as_uuid_required(dept_id), as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE departments SET sku_count = sku_count + :delta "
                    "WHERE id = :did AND organization_id = :oid"
                ),
                {"delta": delta, "did": did, "oid": oid},
            )
            await self.end_write_session(session)

    async def recompute_department_sku_counts(self, org_id: str) -> None:
        """Set departments.sku_count from live SKU rows (fixes stale denormalized counts)."""
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    """
                    UPDATE departments d
                    SET sku_count = COALESCE(
                        (
                            SELECT COUNT(*)::integer FROM skus s
                            WHERE s.category_id = d.id
                              AND s.deleted_at IS NULL
                              AND s.organization_id = d.organization_id
                        ),
                        0
                    )
                    WHERE d.organization_id = :oid
                      AND d.deleted_at IS NULL
                    """
                ),
                {"oid": oid},
            )
            await self.end_write_session(session)
        logger.info(
            "department_sku_counts_recomputed",
            extra={
                "org_id": org_id,
                "action": "recompute_department_sku_counts",
            },
        )

    # --- SKUs (list uses joined SQL for parity with legacy repo) ---
    async def list_skus(
        self,
        org_id: str,
        *,
        category_id: str | None = None,
        search: str | None = None,
        low_stock: bool = False,
        limit: int | None = None,
        offset: int = 0,
        product_family_id: str | None = None,
    ) -> list[Sku]:
        oid = as_uuid_required(org_id)
        sql = (
            "SELECT s.*, p.name AS product_family_name,"
            " v.name AS preferred_vendor_name"
            " FROM skus s"
            " LEFT JOIN products p ON p.id = s.product_family_id"
            " LEFT JOIN vendor_items vi ON vi.sku_id = s.id AND vi.is_preferred = true AND vi.deleted_at IS NULL"
            " LEFT JOIN vendors v ON v.id = vi.vendor_id AND v.deleted_at IS NULL"
            " WHERE s.organization_id = :org_id AND s.deleted_at IS NULL"
        )
        params: dict[str, Any] = {"org_id": oid}
        if category_id:
            sql += " AND s.category_id = :category_id"
            params["category_id"] = as_uuid_required(category_id)
        if product_family_id:
            sql += " AND s.product_family_id = :product_family_id"
            params["product_family_id"] = as_uuid_required(product_family_id)
        if search:
            sql += (
                " AND (s.name LIKE :t1 OR s.sku LIKE :t2 OR s.barcode LIKE :t3)"
            )
            term = f"%{search}%"
            params["t1"] = term
            params["t2"] = term
            params["t3"] = term
        if low_stock:
            sql += " AND s.quantity <= s.min_stock"
        sql += " ORDER BY s.name"
        if limit is not None:
            sql += " LIMIT :lim OFFSET :off"
            params["lim"] = limit
            params["off"] = offset
        async with self.session() as session:
            result = await session.execute(text(sql), params)
            rows = result.mappings().all()
            return [
                s
                for r in rows
                if (s := _sku_row_to_domain(dict(r))) is not None
            ]

    async def count_skus(
        self,
        org_id: str,
        *,
        category_id: str | None = None,
        search: str | None = None,
        low_stock: bool = False,
        product_family_id: str | None = None,
    ) -> int:
        oid = as_uuid_required(org_id)
        sql = "SELECT COUNT(*) FROM skus WHERE organization_id = :org_id AND deleted_at IS NULL"
        params: dict[str, Any] = {"org_id": oid}
        if category_id:
            sql += " AND category_id = :category_id"
            params["category_id"] = as_uuid_required(category_id)
        if product_family_id:
            sql += " AND product_family_id = :product_family_id"
            params["product_family_id"] = as_uuid_required(product_family_id)
        if search:
            sql += " AND (name LIKE :t1 OR sku LIKE :t2 OR barcode LIKE :t3)"
            term = f"%{search}%"
            params["t1"] = term
            params["t2"] = term
            params["t3"] = term
        if low_stock:
            sql += " AND quantity <= min_stock"
        async with self.session() as session:
            r = await session.execute(text(sql), params)
            return int(r.scalar_one() or 0)

    async def get_sku_by_id(self, sku_id: str, org_id: str) -> Sku | None:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM skus WHERE id = :sid AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"sid": sid, "oid": oid},
            )
            row = result.mappings().first()
            return _sku_row_to_domain(dict(row)) if row else None

    async def find_sku_by_code(self, org_id: str, sku: str) -> Sku | None:
        s = sku.strip().upper() if sku else ""
        if not s:
            return None
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM skus WHERE UPPER(sku) = :s AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"s": s, "oid": oid},
            )
            row = result.mappings().first()
            return _sku_row_to_domain(dict(row)) if row else None

    async def find_sku_by_barcode(
        self,
        org_id: str,
        barcode: str,
        exclude_sku_id: str | None = None,
    ) -> Sku | None:
        b = barcode.strip() if barcode else ""
        if not b:
            return None
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            if exclude_sku_id:
                result = await session.execute(
                    text(
                        "SELECT * FROM skus WHERE (barcode = :b OR sku = :b OR vendor_barcode = :b) "
                        "AND id != :ex AND organization_id = :oid AND deleted_at IS NULL"
                    ),
                    {
                        "b": b,
                        "ex": as_uuid_required(exclude_sku_id),
                        "oid": oid,
                    },
                )
            else:
                result = await session.execute(
                    text(
                        "SELECT * FROM skus WHERE (barcode = :b OR sku = :b OR vendor_barcode = :b) "
                        "AND organization_id = :oid AND deleted_at IS NULL"
                    ),
                    {"b": b, "oid": oid},
                )
            row = result.mappings().first()
            return _sku_row_to_domain(dict(row)) if row else None

    async def find_sku_by_name_and_vendor(
        self, org_id: str, name: str, vendor_id: str
    ) -> Sku | None:
        if not name or not str(name).strip() or not vendor_id:
            return None
        norm = str(name).strip().lower()
        oid = as_uuid_required(org_id)
        vid = as_uuid_required(vendor_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT s.* FROM skus s "
                    "INNER JOIN vendor_items vi ON vi.sku_id = s.id AND vi.deleted_at IS NULL "
                    "WHERE vi.vendor_id = :vid AND TRIM(LOWER(s.name)) = :norm "
                    "AND s.organization_id = :oid AND s.deleted_at IS NULL"
                ),
                {"vid": vid, "norm": norm, "oid": oid},
            )
            row = result.mappings().first()
            return _sku_row_to_domain(dict(row)) if row else None

    async def find_skus_by_product_family(
        self, org_id: str, product_family_id: str
    ) -> list[Sku]:
        pid, oid = as_uuid_required(product_family_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM skus WHERE product_family_id = :pid AND organization_id = :oid AND deleted_at IS NULL ORDER BY name"
                ),
                {"pid": pid, "oid": oid},
            )
            rows = result.mappings().all()
            return [
                s
                for r in rows
                if (s := _sku_row_to_domain(dict(r))) is not None
            ]

    async def count_all_skus(self, org_id: str) -> int:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            r = await session.execute(
                text(
                    "SELECT COUNT(*) FROM skus WHERE organization_id = :oid AND deleted_at IS NULL"
                ),
                {"oid": oid},
            )
            return int(r.scalar_one() or 0)

    async def count_low_stock_skus(self, org_id: str) -> int:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            r = await session.execute(
                text(
                    "SELECT COUNT(*) FROM skus WHERE quantity <= min_stock AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"oid": oid},
            )
            return int(r.scalar_one() or 0)

    async def list_low_stock_skus(
        self, org_id: str, limit: int = 10
    ) -> list[Sku]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM skus WHERE quantity <= min_stock AND organization_id = :oid "
                    "AND deleted_at IS NULL ORDER BY quantity LIMIT :lim"
                ),
                {"oid": oid, "lim": limit},
            )
            rows = result.mappings().all()
            return [
                s
                for r in rows
                if (s := _sku_row_to_domain(dict(r))) is not None
            ]

    async def insert_sku(self, sku: Sku) -> None:
        sku_dict = sku.model_dump()
        org_id = sku_dict.get("organization_id")
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO skus (id, sku, product_family_id, name, description, price, cost, quantity, min_stock,
                    category_id, category_name, barcode, vendor_barcode,
                    base_unit, sell_uom, pack_qty, purchase_uom, purchase_pack_qty,
                    variant_label, spec, grade, variant_attrs,
                    organization_id, created_at, updated_at)
                    VALUES (:id, :sku, :product_family_id, :name, :description, :price, :cost, :quantity, :min_stock,
                    :category_id, :category_name, :barcode, :vendor_barcode,
                    :base_unit, :sell_uom, :pack_qty, :purchase_uom, :purchase_pack_qty,
                    :variant_label, :spec, :grade, :variant_attrs,
                    :organization_id, :created_at, :updated_at)"""
                ),
                {
                    "id": as_uuid_required(sku_dict["id"]),
                    "sku": sku_dict["sku"],
                    "product_family_id": as_uuid_required(
                        sku_dict["product_family_id"]
                    ),
                    "name": sku_dict["name"],
                    "description": sku_dict.get("description", ""),
                    "price": sku_dict["price"],
                    "cost": sku_dict.get("cost", 0),
                    "quantity": sku_dict.get("quantity", 0),
                    "min_stock": sku_dict.get("min_stock", 5),
                    "category_id": as_uuid_required(sku_dict["category_id"]),
                    "category_name": sku_dict.get("category_name", ""),
                    "barcode": sku_dict.get("barcode"),
                    "vendor_barcode": sku_dict.get("vendor_barcode"),
                    "base_unit": sku_dict.get("base_unit", "each"),
                    "sell_uom": sku_dict.get("sell_uom", "each"),
                    "pack_qty": sku_dict.get("pack_qty", 1),
                    "purchase_uom": sku_dict.get("purchase_uom", "each"),
                    "purchase_pack_qty": sku_dict.get("purchase_pack_qty", 1),
                    "variant_label": sku_dict.get("variant_label", ""),
                    "spec": sku_dict.get("spec", ""),
                    "grade": sku_dict.get("grade", ""),
                    "variant_attrs": json.dumps(
                        sku_dict.get("variant_attrs") or {}
                    ),
                    "organization_id": oid,
                    "created_at": sku_dict.get("created_at")
                    or datetime.now(UTC),
                    "updated_at": sku_dict.get("updated_at")
                    or datetime.now(UTC),
                },
            )
            await self.end_write_session(session)

    async def update_sku(
        self, sku_id: str, org_id: str, updates: dict
    ) -> Sku | None:
        """Dynamic UPDATE mirroring sku_mutations.update."""
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        set_parts: list[str] = ["updated_at = :updated_at"]
        params: dict[str, Any] = {
            "updated_at": updates.get("updated_at", datetime.now(UTC)),
            "sid": sid,
            "oid": oid,
        }
        n = 0
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
                pname = f"v{n}"
                set_parts.append(f"{key} = :{pname}")
                val = updates[key]
                if key in ("category_id", "product_family_id"):
                    val = as_uuid_required(val)
                params[pname] = val
                n += 1
        if "variant_attrs" in updates and updates["variant_attrs"] is not None:
            pname = f"v{n}"
            set_parts.append(f"variant_attrs = :{pname}")
            params[pname] = json.dumps(updates["variant_attrs"])
            n += 1
        if len(set_parts) <= 1:
            return await self.get_sku_by_id(sku_id, org_id)
        sql = "UPDATE skus SET " + ", ".join(set_parts)
        sql += " WHERE id = :sid AND organization_id = :oid"
        async with self.session() as session:
            await session.execute(text(sql), params)
            await self.end_write_session(session)
        return await self.get_sku_by_id(sku_id, org_id)

    async def soft_delete_sku(self, sku_id: str, org_id: str) -> int:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE skus SET deleted_at = :now WHERE id = :sid AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "sid": sid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def sku_atomic_decrement(
        self, sku_id: str, org_id: str, quantity: float, updated_at: datetime
    ) -> Sku | None:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE skus SET quantity = quantity - :qty, updated_at = :ua "
                    "WHERE id = :sid AND quantity >= :qty AND organization_id = :oid"
                ),
                {"qty": quantity, "ua": updated_at, "sid": sid, "oid": oid},
            )
            await self.end_write_session(session)
            rowcount = res.rowcount or 0
        if rowcount == 0:
            return None
        return await self.get_sku_by_id(sku_id, org_id)

    async def sku_increment_quantity(
        self, sku_id: str, org_id: str, quantity: float, updated_at: datetime
    ) -> None:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE skus SET quantity = quantity + :qty, updated_at = :ua "
                    "WHERE id = :sid AND organization_id = :oid"
                ),
                {"qty": quantity, "ua": updated_at, "sid": sid, "oid": oid},
            )
            await self.end_write_session(session)

    async def sku_add_quantity(
        self, sku_id: str, org_id: str, quantity: float, updated_at: datetime
    ) -> Sku | None:
        await self.sku_increment_quantity(sku_id, org_id, quantity, updated_at)
        return await self.get_sku_by_id(sku_id, org_id)

    async def sku_atomic_adjust(
        self,
        sku_id: str,
        org_id: str,
        quantity_delta: float,
        updated_at: datetime,
    ) -> Sku | None:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE skus SET quantity = quantity + :delta, updated_at = :ua "
                    "WHERE id = :sid AND quantity + :delta >= 0 AND organization_id = :oid"
                ),
                {
                    "delta": quantity_delta,
                    "ua": updated_at,
                    "sid": sid,
                    "oid": oid,
                },
            )
            await self.end_write_session(session)
            rowcount = res.rowcount or 0
        if rowcount == 0:
            return None
        return await self.get_sku_by_id(sku_id, org_id)

    # --- Product families (products table) ---
    async def insert_product_family(self, product: ProductFamily) -> None:
        p = product.model_dump()
        oid = as_uuid_required(p.get("organization_id"))
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO products (id, name, description, category_id, category_name,
                    sku_count, organization_id, created_at, updated_at)
                    VALUES (:id, :name, :description, :category_id, :category_name,
                    :sku_count, :organization_id, :created_at, :updated_at)"""
                ),
                {
                    "id": as_uuid_required(p["id"]),
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "category_id": as_uuid_required(p["category_id"]),
                    "category_name": p.get("category_name", ""),
                    "sku_count": p.get("sku_count", 0),
                    "organization_id": oid,
                    "created_at": p.get("created_at") or datetime.now(UTC),
                    "updated_at": p.get("updated_at") or datetime.now(UTC),
                },
            )
            await self.end_write_session(session)

    async def get_product_family_by_id(
        self, product_id: str, org_id: str
    ) -> ProductFamily | None:
        pid, oid = as_uuid_required(product_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM products WHERE id = :pid AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"pid": pid, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_product_family(dict(row)) if row else None

    async def list_product_families(
        self,
        org_id: str,
        *,
        category_id: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ProductFamily]:
        oid = as_uuid_required(org_id)
        sql = "SELECT * FROM products WHERE organization_id = :oid AND deleted_at IS NULL"
        params: dict[str, Any] = {"oid": oid}
        if category_id:
            sql += " AND category_id = :category_id"
            params["category_id"] = as_uuid_required(category_id)
        if search:
            sql += " AND name LIKE :search"
            params["search"] = f"%{search}%"
        sql += " ORDER BY name"
        if limit is not None:
            sql += " LIMIT :lim OFFSET :off"
            params["lim"] = limit
            params["off"] = offset
        async with self.session() as session:
            result = await session.execute(text(sql), params)
            return [
                p
                for r in result.mappings().all()
                if (p := _row_to_product_family(dict(r))) is not None
            ]

    async def count_product_families(
        self,
        org_id: str,
        *,
        category_id: str | None = None,
        search: str | None = None,
    ) -> int:
        oid = as_uuid_required(org_id)
        sql = "SELECT COUNT(*) FROM products WHERE organization_id = :oid AND deleted_at IS NULL"
        params: dict[str, Any] = {"oid": oid}
        if category_id:
            sql += " AND category_id = :category_id"
            params["category_id"] = as_uuid_required(category_id)
        if search:
            sql += " AND name LIKE :search"
            params["search"] = f"%{search}%"
        async with self.session() as session:
            r = await session.execute(text(sql), params)
            return int(r.scalar_one() or 0)

    async def update_product_family(
        self, product_id: str, org_id: str, updates: dict
    ) -> ProductFamily | None:
        pid, oid = as_uuid_required(product_id), as_uuid_required(org_id)
        set_parts: list[str] = ["updated_at = :updated_at"]
        params: dict[str, Any] = {
            "updated_at": updates.get("updated_at", datetime.now(UTC)),
            "pid": pid,
            "oid": oid,
        }
        n = 0
        for key in ("name", "description", "category_id", "category_name"):
            if key in updates and updates[key] is not None:
                pname = f"v{n}"
                set_parts.append(f"{key} = :{pname}")
                val = updates[key]
                if key == "category_id":
                    val = as_uuid_required(val)
                params[pname] = val
                n += 1
        if len(set_parts) <= 1:
            return await self.get_product_family_by_id(product_id, org_id)
        sql = "UPDATE products SET " + ", ".join(set_parts)
        sql += " WHERE id = :pid AND organization_id = :oid"
        async with self.session() as session:
            await session.execute(text(sql), params)
            await self.end_write_session(session)
        return await self.get_product_family_by_id(product_id, org_id)

    async def soft_delete_product_family(
        self, product_id: str, org_id: str
    ) -> int:
        pid, oid = as_uuid_required(product_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE products SET deleted_at = :now WHERE id = :pid AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "pid": pid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def increment_product_sku_count(
        self, product_id: str, org_id: str, delta: int
    ) -> None:
        pid, oid = as_uuid_required(product_id), as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE products SET sku_count = sku_count + :delta WHERE id = :pid AND organization_id = :oid"
                ),
                {"delta": delta, "pid": pid, "oid": oid},
            )
            await self.end_write_session(session)

    async def list_vendors(self, org_id: str) -> list[Vendor]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, name, contact_name, email, phone, address, organization_id, created_at FROM vendors
               WHERE organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"oid": oid},
            )
            return [
                v
                for r in result.mappings().all()
                if (v := _row_to_vendor(dict(r))) is not None
            ]

    async def get_vendor_by_id(
        self, vendor_id: str, org_id: str
    ) -> Vendor | None:
        vid, oid = as_uuid_required(vendor_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, name, contact_name, email, phone, address, organization_id, created_at FROM vendors
               WHERE id = :vid AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"vid": vid, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_vendor(dict(row)) if row else None

    async def find_vendor_by_name(
        self, org_id: str, name: str
    ) -> Vendor | None:
        if not name or not name.strip():
            return None
        norm = name.strip().lower()
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, name, contact_name, email, phone, address, organization_id, created_at FROM vendors
               WHERE TRIM(LOWER(name)) = :norm AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"norm": norm, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_vendor(dict(row)) if row else None

    async def insert_vendor(self, vendor: Vendor) -> None:
        vd = vendor.model_dump()
        oid = as_uuid_required(vd.get("organization_id"))
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO vendors (id, name, contact_name, email, phone, address, organization_id, created_at)
               VALUES (:id, :name, :contact_name, :email, :phone, :address, :organization_id, :created_at)"""
                ),
                {
                    "id": as_uuid_required(vd["id"]),
                    "name": vd["name"],
                    "contact_name": vd.get("contact_name", ""),
                    "email": vd.get("email", ""),
                    "phone": vd.get("phone", ""),
                    "address": vd.get("address", ""),
                    "organization_id": oid,
                    "created_at": vd.get("created_at") or datetime.now(UTC),
                },
            )
            await self.end_write_session(session)

    async def update_vendor(
        self, vendor_id: str, org_id: str, vendor_dict: dict
    ) -> Vendor | None:
        vid, oid = as_uuid_required(vendor_id), as_uuid_required(org_id)
        new_name = vendor_dict.get("name", "")
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE vendors SET name = :name, contact_name = :cn, email = :em, phone = :ph, address = :ad "
                    "WHERE id = :vid AND organization_id = :oid"
                ),
                {
                    "name": new_name,
                    "cn": vendor_dict.get("contact_name", ""),
                    "em": vendor_dict.get("email", ""),
                    "ph": vendor_dict.get("phone", ""),
                    "ad": vendor_dict.get("address", ""),
                    "vid": vid,
                    "oid": oid,
                },
            )
            await session.execute(
                text(
                    "UPDATE vendor_items SET vendor_name = :vname WHERE vendor_id = :vid AND organization_id = :oid"
                ),
                {"vname": new_name, "vid": vid, "oid": oid},
            )
            await self.end_write_session(session)
        return await self.get_vendor_by_id(vendor_id, org_id)

    async def soft_delete_vendor(self, vendor_id: str, org_id: str) -> int:
        vid, oid = as_uuid_required(vendor_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE vendors SET deleted_at = :now WHERE id = :vid AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "vid": vid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def count_vendors(self, org_id: str) -> int:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            r = await session.execute(
                text(
                    "SELECT COUNT(*) FROM vendors WHERE organization_id = :oid AND deleted_at IS NULL"
                ),
                {"oid": oid},
            )
            return int(r.scalar_one() or 0)

    async def list_uoms(self, org_id: str) -> list[UnitOfMeasure]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE organization_id = :oid AND deleted_at IS NULL ORDER BY code"""
                ),
                {"oid": oid},
            )
            return [
                u
                for r in result.mappings().all()
                if (u := _row_to_uom(dict(r))) is not None
            ]

    async def get_uom_by_code(
        self, org_id: str, code: str
    ) -> UnitOfMeasure | None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE code = :code AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"code": code.lower(), "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_uom(dict(row)) if row else None

    async def get_uom_by_id(
        self, uom_id: str, org_id: str
    ) -> UnitOfMeasure | None:
        uid, oid = as_uuid_required(uom_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT id, code, name, family, organization_id, created_at
           FROM units_of_measure
           WHERE id = :uid AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"uid": uid, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_uom(dict(row)) if row else None

    async def insert_uom(self, uom: UnitOfMeasure) -> None:
        d = uom.model_dump()
        oid = as_uuid_required(d["organization_id"])
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO units_of_measure (id, code, name, family, organization_id, created_at)
           VALUES (:id, :code, :name, :family, :organization_id, :created_at)"""
                ),
                {
                    "id": as_uuid_required(d["id"]),
                    "code": d["code"],
                    "name": d["name"],
                    "family": d["family"],
                    "organization_id": oid,
                    "created_at": d["created_at"],
                },
            )
            await self.end_write_session(session)

    async def soft_delete_uom(self, uom_id: str, org_id: str) -> int:
        uid, oid = as_uuid_required(uom_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    """UPDATE units_of_measure SET deleted_at = :now
           WHERE id = :uid AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"now": now, "uid": uid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def sku_counter_next_preview(
        self, org_id: str, product_family_id: str
    ) -> int:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(product_family_id)
        async with self.session() as session:
            r = await session.execute(
                text(
                    "SELECT counter FROM sku_counters WHERE organization_id = :oid AND product_family_id = :pid"
                ),
                {"oid": oid, "pid": pid},
            )
            row = r.scalar_one_or_none()
            return (int(row) + 1) if row is not None else 1

    async def sku_counter_all(self, org_id: str) -> dict[str, int]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT product_family_id, counter FROM sku_counters WHERE organization_id = :oid"
                ),
                {"oid": oid},
            )
            rows = result.all()
            return {str(a): int(b) for a, b in rows} if rows else {}

    async def sku_counter_increment(
        self, org_id: str, product_family_id: str
    ) -> int:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(product_family_id)
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO sku_counters (organization_id, product_family_id, counter)
           VALUES (:oid, :pid, 1)
           ON CONFLICT(organization_id, product_family_id)
           DO UPDATE SET counter = sku_counters.counter + 1"""
                ),
                {"oid": oid, "pid": pid},
            )
            r = await session.execute(
                text(
                    "SELECT counter FROM sku_counters WHERE organization_id = :oid AND product_family_id = :pid"
                ),
                {"oid": oid, "pid": pid},
            )
            await self.end_write_session(session)
            row = r.scalar_one_or_none()
            return int(row) if row is not None else 1

    async def insert_vendor_item(self, item: VendorItem) -> None:
        d = item.model_dump()
        oid = as_uuid_required(d.get("organization_id"))
        async with self.session() as session:
            await session.execute(
                text(
                    """INSERT INTO vendor_items (id, vendor_id, sku_id, vendor_sku, vendor_name,
           purchase_uom, purchase_pack_qty, cost, lead_time_days, moq, is_preferred, notes,
           organization_id, created_at, updated_at)
           VALUES (:id, :vendor_id, :sku_id, :vendor_sku, :vendor_name,
           :purchase_uom, :purchase_pack_qty, :cost, :lead_time_days, :moq, :is_preferred, :notes,
           :organization_id, :created_at, :updated_at)"""
                ),
                {
                    "id": as_uuid_required(d["id"]),
                    "vendor_id": as_uuid_required(d["vendor_id"]),
                    "sku_id": as_uuid_required(d["sku_id"]),
                    "vendor_sku": d.get("vendor_sku"),
                    "vendor_name": d.get("vendor_name", ""),
                    "purchase_uom": d.get("purchase_uom", "each"),
                    "purchase_pack_qty": d.get("purchase_pack_qty", 1),
                    "cost": d.get("cost", 0),
                    "lead_time_days": d.get("lead_time_days"),
                    "moq": d.get("moq"),
                    "is_preferred": bool(d.get("is_preferred", False)),
                    "notes": d.get("notes"),
                    "organization_id": oid,
                    "created_at": d.get("created_at") or datetime.now(UTC),
                    "updated_at": d.get("updated_at") or datetime.now(UTC),
                },
            )
            await self.end_write_session(session)

    async def add_vendor_item(
        self,
        org_id: str,
        sku_id: str,
        vendor_id: str,
        vendor_sku: str | None = None,
        purchase_uom: str = "each",
        purchase_pack_qty: int = 1,
        cost: float = 0.0,
        lead_time_days: int | None = None,
        moq: float | None = None,
        is_preferred: bool = False,
        notes: str | None = None,
    ) -> VendorItem:
        """Add a vendor relationship to a SKU (preferred flag clears others in same txn)."""
        vendor = await self.get_vendor_by_id(vendor_id, org_id)
        vendor_name = vendor.name if vendor else ""

        item = VendorItem(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            sku_id=sku_id,
            vendor_sku=vendor_sku,
            purchase_uom=purchase_uom,
            purchase_pack_qty=purchase_pack_qty,
            cost=cost,
            lead_time_days=lead_time_days,
            moq=moq,
            is_preferred=is_preferred,
            notes=notes,
            organization_id=org_id,
        )

        # Lazy import: ``shared.infrastructure.db`` imports this module via services.
        from shared.infrastructure.db import transaction as db_transaction

        async with db_transaction():
            if is_preferred:
                await self.clear_preferred_vendor_items_for_sku(sku_id, org_id)
            await self.insert_vendor_item(item)

        logger.info(
            "vendor_item.added",
            extra={
                "org_id": org_id,
                "vendor_item_id": item.id,
                "sku_id": sku_id,
                "vendor_id": vendor_id,
                "is_preferred": is_preferred,
            },
        )
        return item

    async def modify_vendor_item(
        self, org_id: str, item_id: str, updates: dict
    ) -> VendorItem:
        """Update a vendor item; setting preferred clears other preferred for the SKU."""
        existing = await self.get_vendor_item_by_id(item_id, org_id)
        if not existing:
            raise ResourceNotFoundError("VendorItem", item_id)

        payload = {
            **updates,
            "updated_at": updates.get("updated_at") or datetime.now(UTC),
        }
        # Lazy import: ``shared.infrastructure.db`` imports this module via services.
        from shared.infrastructure.db import transaction as db_transaction

        async with db_transaction():
            if updates.get("is_preferred"):
                await self.clear_preferred_vendor_items_for_sku(
                    existing.sku_id, org_id
                )
            result = await self.update_vendor_item(item_id, org_id, payload)
        if not result:
            raise ResourceNotFoundError("VendorItem", item_id)
        logger.info(
            "vendor_item.updated",
            extra={"org_id": org_id, "vendor_item_id": item_id},
        )
        return result

    async def set_preferred_vendor_item(
        self, org_id: str, sku_id: str, vendor_item_id: str
    ) -> None:
        """Set one vendor item preferred for a SKU (clears others)."""
        item = await self.get_vendor_item_by_id(vendor_item_id, org_id)
        if not item or item.sku_id != sku_id:
            raise ResourceNotFoundError("VendorItem", vendor_item_id)

        # Lazy import: ``shared.infrastructure.db`` imports this module via services.
        from shared.infrastructure.db import transaction as db_transaction

        async with db_transaction():
            await self.clear_preferred_vendor_items_for_sku(sku_id, org_id)
            await self.update_vendor_item(
                vendor_item_id,
                org_id,
                {"is_preferred": True, "updated_at": datetime.now(UTC)},
            )
        logger.info(
            "vendor_item.preferred_set",
            extra={
                "org_id": org_id,
                "vendor_item_id": vendor_item_id,
                "sku_id": sku_id,
            },
        )

    async def get_vendor_item_by_id(
        self, item_id: str, org_id: str
    ) -> VendorItem | None:
        iid, oid = as_uuid_required(item_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    "SELECT * FROM vendor_items WHERE id = :iid AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"iid": iid, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_vendor_item(dict(row)) if row else None

    async def list_vendor_items_by_sku(
        self, sku_id: str, org_id: str
    ) -> list[VendorItem]:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT * FROM vendor_items
           WHERE sku_id = :sid AND organization_id = :oid AND deleted_at IS NULL
           ORDER BY is_preferred DESC, vendor_name"""
                ),
                {"sid": sid, "oid": oid},
            )
            return [
                vi
                for r in result.mappings().all()
                if (vi := _row_to_vendor_item(dict(r))) is not None
            ]

    async def list_vendor_items_by_skus(
        self, org_id: str, sku_ids: list[str]
    ) -> list[VendorItem]:
        if not sku_ids:
            return []
        oid = as_uuid_required(org_id)
        uuids = [as_uuid_required(x) for x in sku_ids]
        async with self.session() as session:
            result = await session.execute(
                select(VendorItems).where(
                    VendorItems.organization_id == oid,
                    VendorItems.deleted_at.is_(None),
                    VendorItems.sku_id.in_(uuids),
                )
            )
            rows = result.scalars().all()
        out: list[VendorItem] = []
        for r in rows:
            m = r.model_dump()
            if (vi := _row_to_vendor_item(m)) is not None:
                out.append(vi)
        out.sort(
            key=lambda x: (
                x.sku_id,
                -1 if x.is_preferred else 0,
                x.cost if x.cost is not None else 1e9,
                x.vendor_name or "",
            )
        )
        return out

    async def list_vendor_items_by_skus_grouped(
        self, org_id: str, sku_ids: list[str]
    ) -> dict[str, list[VendorItem]]:
        items = await self.list_vendor_items_by_skus(org_id, sku_ids)
        grouped: dict[str, list[VendorItem]] = {}
        for item in items:
            grouped.setdefault(item.sku_id, []).append(item)
        return grouped

    async def list_vendor_items_by_vendor(
        self, vendor_id: str, org_id: str
    ) -> list[VendorItem]:
        vid, oid = as_uuid_required(vendor_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT * FROM vendor_items
           WHERE vendor_id = :vid AND organization_id = :oid AND deleted_at IS NULL
           ORDER BY vendor_sku"""
                ),
                {"vid": vid, "oid": oid},
            )
            return [
                vi
                for r in result.mappings().all()
                if (vi := _row_to_vendor_item(dict(r))) is not None
            ]

    async def find_vendor_item_by_vendor_and_sku(
        self, org_id: str, vendor_id: str, vendor_sku: str
    ) -> VendorItem | None:
        if not vendor_sku or not str(vendor_sku).strip() or not vendor_id:
            return None
        norm = str(vendor_sku).strip().lower()
        vid, oid = as_uuid_required(vendor_id), as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT * FROM vendor_items
           WHERE vendor_id = :vid AND TRIM(LOWER(COALESCE(vendor_sku, ''))) = :norm
           AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"vid": vid, "norm": norm, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_vendor_item(dict(row)) if row else None

    async def find_vendor_item_by_sku_and_vendor(
        self, sku_id: str, vendor_id: str, org_id: str
    ) -> VendorItem | None:
        sid, vid, oid = (
            as_uuid_required(sku_id),
            as_uuid_required(vendor_id),
            as_uuid_required(org_id),
        )
        async with self.session() as session:
            result = await session.execute(
                text(
                    """SELECT * FROM vendor_items
           WHERE sku_id = :sid AND vendor_id = :vid
           AND organization_id = :oid AND deleted_at IS NULL"""
                ),
                {"sid": sid, "vid": vid, "oid": oid},
            )
            row = result.mappings().first()
            return _row_to_vendor_item(dict(row)) if row else None

    async def update_vendor_item(
        self, item_id: str, org_id: str, updates: dict
    ) -> VendorItem | None:
        iid, oid = as_uuid_required(item_id), as_uuid_required(org_id)
        set_parts: list[str] = ["updated_at = :updated_at"]
        params: dict[str, Any] = {
            "updated_at": updates.get("updated_at", datetime.now(UTC)),
            "iid": iid,
            "oid": oid,
        }
        n = 0
        for key in (
            "vendor_sku",
            "vendor_name",
            "purchase_uom",
            "purchase_pack_qty",
            "cost",
            "lead_time_days",
            "moq",
            "is_preferred",
            "notes",
        ):
            if key in updates and updates[key] is not None:
                pname = f"v{n}"
                set_parts.append(f"{key} = :{pname}")
                val = (
                    bool(updates[key])
                    if key == "is_preferred"
                    else updates[key]
                )
                params[pname] = val
                n += 1
        if len(set_parts) <= 1:
            return await self.get_vendor_item_by_id(item_id, org_id)
        sql = "UPDATE vendor_items SET " + ", ".join(set_parts)
        sql += " WHERE id = :iid AND organization_id = :oid"
        async with self.session() as session:
            await session.execute(text(sql), params)
            await self.end_write_session(session)
        return await self.get_vendor_item_by_id(item_id, org_id)

    async def soft_delete_vendor_item(self, item_id: str, org_id: str) -> int:
        iid, oid = as_uuid_required(item_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE vendor_items SET deleted_at = :now WHERE id = :iid AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "iid": iid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def soft_delete_vendor_items_by_sku(
        self, sku_id: str, org_id: str
    ) -> int:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            res = await session.execute(
                text(
                    "UPDATE vendor_items SET deleted_at = :now WHERE sku_id = :sid AND deleted_at IS NULL AND organization_id = :oid"
                ),
                {"now": now, "sid": sid, "oid": oid},
            )
            await self.end_write_session(session)
            return int(res.rowcount or 0)

    async def clear_preferred_vendor_items_for_sku(
        self, sku_id: str, org_id: str
    ) -> None:
        sid, oid = as_uuid_required(sku_id), as_uuid_required(org_id)
        async with self.session() as session:
            await session.execute(
                text(
                    "UPDATE vendor_items SET is_preferred = FALSE WHERE sku_id = :sid AND organization_id = :oid AND deleted_at IS NULL"
                ),
                {"sid": sid, "oid": oid},
            )
            await self.end_write_session(session)
