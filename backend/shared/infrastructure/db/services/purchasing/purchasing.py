"""Purchasing / PO persistence via SQLModel. ``org_id`` is explicit on each method."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

from sqlalchemy import Numeric, case, cast, func, select, update

from finance.domain.enums import XeroSyncStatus
from purchasing.domain.purchase_order import (
    POItemRow,
    POItemStatus,
    PORow,
    PurchaseOrder,
    PurchaseOrderItem,
    VendorPerformance,
)
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services.purchasing._helpers import (
    build_purchase_order_item_row,
    build_purchase_orders_row,
    purchase_order_item_row_to_poitemrow,
    purchase_orders_row_to_porow,
)
from shared.infrastructure.types.public_sql_model_models import (
    PurchaseOrderItems,
    PurchaseOrders,
    Skus,
    VendorItems,
)


class VendorCatalogRow(TypedDict):
    vendor_sku: str | None
    cost: float
    lead_time_days: int | None
    moq: float | None
    is_preferred: bool
    purchase_uom: str
    purchase_pack_qty: int
    sku: str
    name: str
    quantity: float
    min_stock: int
    sell_uom: str
    department: str


class PurchaseHistoryItem(TypedDict):
    id: str
    vendor_name: str
    document_date: str | None
    total: float | None
    status: str
    created_at: datetime
    received_at: datetime | None
    items: list[dict]
    item_count: int


class ReorderRow(TypedDict):
    sku_id: str
    sku: str
    name: str
    quantity: float
    min_stock: int
    current_cost: float
    sell_uom: str
    department: str
    vendor_options: list[dict]
    deficit: float


class PurchasingDatabaseService(DomainDatabaseService):
    async def insert_po(self, org_id: str, po: PurchaseOrder) -> None:
        oid = as_uuid_required(org_id)
        po.organization_id = org_id
        row = build_purchase_orders_row(po, oid)
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def insert_po_items(
        self, org_id: str, items: list[PurchaseOrderItem]
    ) -> None:
        _ = as_uuid_required(org_id)
        async with self.session() as session:
            for item in items:
                item.organization_id = org_id
                session.add(build_purchase_order_item_row(item))
            await self.end_write_session(session)

    async def list_pos(
        self, org_id: str, status: str | None = None
    ) -> list[PORow]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(PurchaseOrders).where(
                PurchaseOrders.organization_id == oid
            )
            if status:
                stmt = stmt.where(PurchaseOrders.status == status)
            stmt = stmt.order_by(PurchaseOrders.created_at.desc())
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [purchase_orders_row_to_porow(r) for r in rows]

    async def list_pos_with_counts(
        self, org_id: str, status: str | None = None
    ) -> list[PORow]:
        oid = as_uuid_required(org_id)
        ord_v = POItemStatus.ORDERED.value
        pend_v = POItemStatus.PENDING.value
        arr_v = POItemStatus.ARRIVED.value
        item_cnt = func.count(PurchaseOrderItems.id)
        async with self.session() as session:
            stmt = (
                select(
                    PurchaseOrders,
                    item_cnt.label("item_count"),
                    item_cnt.filter(PurchaseOrderItems.status == ord_v).label(
                        "ordered_count"
                    ),
                    item_cnt.filter(PurchaseOrderItems.status == pend_v).label(
                        "pending_count"
                    ),
                    item_cnt.filter(PurchaseOrderItems.status == arr_v).label(
                        "arrived_count"
                    ),
                )
                .outerjoin(
                    PurchaseOrderItems,
                    PurchaseOrderItems.po_id == PurchaseOrders.id,
                )
                .where(PurchaseOrders.organization_id == oid)
            )
            if status:
                stmt = stmt.where(PurchaseOrders.status == status)
            stmt = stmt.group_by(PurchaseOrders.id).order_by(
                PurchaseOrders.created_at.desc()
            )
            result = await session.execute(stmt)
            out: list[PORow] = []
            for (
                row,
                ic,
                oc,
                pc,
                ac,
            ) in result.all():
                out.append(
                    purchase_orders_row_to_porow(
                        row,
                        item_count=int(ic or 0),
                        ordered_count=int(oc or 0),
                        pending_count=int(pc or 0),
                        arrived_count=int(ac or 0),
                    )
                )
            return out

    async def get_po(self, org_id: str, po_id: str) -> PORow | None:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        async with self.session() as session:
            row = await session.scalar(
                select(PurchaseOrders).where(
                    PurchaseOrders.id == pid,
                    PurchaseOrders.organization_id == oid,
                )
            )
            return purchase_orders_row_to_porow(row) if row else None

    async def get_po_items(self, org_id: str, po_id: str) -> list[POItemRow]:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        async with self.session() as session:
            result = await session.execute(
                select(PurchaseOrderItems)
                .where(
                    PurchaseOrderItems.po_id == pid,
                    PurchaseOrderItems.organization_id == oid,
                )
                .order_by(PurchaseOrderItems.id)
            )
            rows = result.scalars().all()
            return [purchase_order_item_row_to_poitemrow(r) for r in rows]

    async def update_po_item(
        self,
        org_id: str,
        item_id: str,
        status: POItemStatus,
        sku_id: str | None = None,
        delivered_qty: float | None = None,
    ) -> bool:
        oid = as_uuid_required(org_id)
        iid = as_uuid_required(item_id)
        vals: dict[str, Any] = {"status": status.value}
        if sku_id is not None:
            vals["sku_id"] = as_uuid_required(sku_id)
        if delivered_qty is not None:
            vals["delivered_qty"] = delivered_qty
        async with self.session() as session:
            res = await session.execute(
                update(PurchaseOrderItems)
                .where(
                    PurchaseOrderItems.id == iid,
                    PurchaseOrderItems.status != POItemStatus.ARRIVED.value,
                    PurchaseOrderItems.organization_id == oid,
                )
                .values(**vals)
            )
            await self.end_write_session(session)
            return res.rowcount > 0

    async def update_po_status(
        self,
        org_id: str,
        po_id: str,
        status: str,
        received_at: datetime | str | None = None,
        received_by_id: str | None = None,
        received_by_name: str | None = None,
    ) -> None:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        ra = received_at
        if isinstance(ra, str):
            ra = datetime.fromisoformat(ra.replace("Z", "+00:00"))
        vals: dict[str, Any] = {"status": status}
        if ra is not None:
            vals["received_at"] = ra
        if received_by_id is not None:
            vals["received_by_id"] = as_uuid_required(received_by_id)
        if received_by_name is not None:
            vals["received_by_name"] = received_by_name
        async with self.session() as session:
            await session.execute(
                update(PurchaseOrders)
                .where(
                    PurchaseOrders.id == pid,
                    PurchaseOrders.organization_id == oid,
                )
                .values(**vals)
            )
            await self.end_write_session(session)

    async def list_unsynced_po_bills(self, org_id: str) -> list[dict]:
        oid = as_uuid_required(org_id)
        pending = str(XeroSyncStatus.PENDING)
        async with self.session() as session:
            result = await session.execute(
                select(
                    PurchaseOrders.id,
                    PurchaseOrders.vendor_name,
                    PurchaseOrders.total,
                    PurchaseOrders.document_date,
                    PurchaseOrders.created_at,
                )
                .where(
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.status == "received",
                    PurchaseOrders.xero_bill_id.is_(None),
                    PurchaseOrders.xero_sync_status == pending,
                )
                .order_by(PurchaseOrders.created_at)
            )
            return [
                {
                    "id": str(r.id),
                    "vendor_name": r.vendor_name,
                    "total": r.total,
                    "document_date": r.document_date,
                    "created_at": r.created_at,
                }
                for r in result.all()
            ]

    async def list_failed_po_bills(self, org_id: str) -> list[dict]:
        oid = as_uuid_required(org_id)
        failed = str(XeroSyncStatus.FAILED)
        async with self.session() as session:
            result = await session.execute(
                select(
                    PurchaseOrders.id,
                    PurchaseOrders.vendor_name,
                    PurchaseOrders.total,
                    PurchaseOrders.document_date,
                    PurchaseOrders.created_at,
                )
                .where(
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.xero_sync_status == failed,
                )
                .order_by(PurchaseOrders.created_at)
            )
            return [
                {
                    "id": str(r.id),
                    "vendor_name": r.vendor_name,
                    "total": r.total,
                    "document_date": r.document_date,
                    "created_at": r.created_at,
                }
                for r in result.all()
            ]

    async def get_po_with_cost(self, org_id: str, po_id: str) -> dict | None:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        async with self.session() as session:
            po_row = await session.scalar(
                select(PurchaseOrders).where(
                    PurchaseOrders.id == pid,
                    PurchaseOrders.organization_id == oid,
                )
            )
            if not po_row:
                return None
            cost_total = await session.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            PurchaseOrderItems.cost
                            * func.coalesce(
                                PurchaseOrderItems.delivered_qty,
                                PurchaseOrderItems.ordered_qty,
                            )
                        ),
                        0.0,
                    )
                ).where(
                    PurchaseOrderItems.po_id == pid,
                    PurchaseOrderItems.organization_id == oid,
                )
            )
            items_result = await session.execute(
                select(
                    PurchaseOrderItems.name,
                    func.coalesce(
                        PurchaseOrderItems.delivered_qty,
                        PurchaseOrderItems.ordered_qty,
                    ).label("qty"),
                    PurchaseOrderItems.cost,
                ).where(
                    PurchaseOrderItems.po_id == pid,
                    PurchaseOrderItems.organization_id == oid,
                )
            )
            d = {
                c.key: getattr(po_row, c.key)
                for c in PurchaseOrders.__table__.columns
            }
            for k, v in list(d.items()):
                if hasattr(v, "hex"):
                    d[k] = str(v)
            d["cost_total"] = float(cost_total or 0.0)
            d["items"] = [
                {
                    "name": r.name,
                    "qty": float(r.qty or 0),
                    "cost": float(r.cost),
                }
                for r in items_result.all()
            ]
            return d

    async def set_po_xero_sync_status(
        self, org_id: str, po_id: str, status: str, updated_at: datetime
    ) -> None:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        async with self.session() as session:
            await session.execute(
                update(PurchaseOrders)
                .where(
                    PurchaseOrders.id == pid,
                    PurchaseOrders.organization_id == oid,
                )
                .values(xero_sync_status=status, updated_at=updated_at)
            )
            await self.end_write_session(session)

    async def po_summary_by_status(self, org_id: str) -> dict[str, dict]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(
                    PurchaseOrders.status,
                    func.count(PurchaseOrders.id).label("cnt"),
                    func.coalesce(func.sum(PurchaseOrders.total), 0).label(
                        "total"
                    ),
                )
                .where(PurchaseOrders.organization_id == oid)
                .group_by(PurchaseOrders.status)
            )
            return {
                r.status: {"count": int(r.cnt), "total": float(r.total)}
                for r in result.all()
            }

    async def set_po_xero_bill_id(
        self, org_id: str, po_id: str, xero_bill_id: str, updated_at: datetime
    ) -> None:
        oid = as_uuid_required(org_id)
        pid = as_uuid_required(po_id)
        async with self.session() as session:
            await session.execute(
                update(PurchaseOrders)
                .where(
                    PurchaseOrders.id == pid,
                    PurchaseOrders.organization_id == oid,
                )
                .values(
                    xero_bill_id=xero_bill_id,
                    xero_sync_status=str(XeroSyncStatus.SYNCED),
                    updated_at=updated_at,
                )
            )
            await self.end_write_session(session)

    async def vendor_catalog(
        self, org_id: str, vendor_id: str
    ) -> list[VendorCatalogRow]:
        oid = as_uuid_required(org_id)
        vid = as_uuid_required(vendor_id)
        async with self.session() as session:
            stmt = (
                select(
                    VendorItems.vendor_sku,
                    VendorItems.cost,
                    VendorItems.lead_time_days,
                    VendorItems.moq,
                    VendorItems.is_preferred,
                    VendorItems.purchase_uom,
                    VendorItems.purchase_pack_qty,
                    Skus.sku,
                    Skus.name,
                    Skus.quantity,
                    Skus.min_stock,
                    Skus.sell_uom,
                    Skus.category_name.label("department"),
                )
                .join(Skus, Skus.id == VendorItems.sku_id)
                .where(
                    VendorItems.vendor_id == vid,
                    VendorItems.organization_id == oid,
                    VendorItems.deleted_at.is_(None),
                    Skus.deleted_at.is_(None),
                )
                .order_by(VendorItems.is_preferred.desc(), Skus.name)
            )
            result = await session.execute(stmt)
            return [VendorCatalogRow(**dict(r._mapping)) for r in result.all()]

    async def vendor_performance(
        self,
        org_id: str,
        vendor_id: str,
        days: int = 90,
        vendor_name: str = "",
    ) -> VendorPerformance:
        oid = as_uuid_required(org_id)
        vid = as_uuid_required(vendor_id)
        since = datetime.now(UTC) - timedelta(days=days)
        async with self.session() as session:
            s1 = await session.execute(
                select(
                    func.count(PurchaseOrders.id).label("po_count"),
                    func.round(
                        cast(
                            func.coalesce(func.sum(PurchaseOrders.total), 0),
                            Numeric,
                        ),
                        2,
                    ).label("total_spend"),
                    func.sum(
                        case((PurchaseOrders.status == "received", 1), else_=0)
                    ).label("received_count"),
                ).where(
                    PurchaseOrders.vendor_id == vid,
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.created_at >= since,
                )
            )
            summary = s1.one()

            s2 = await session.execute(
                select(
                    func.round(
                        cast(
                            func.avg(
                                func.extract(
                                    "epoch",
                                    PurchaseOrders.received_at
                                    - PurchaseOrders.created_at,
                                )
                                / 86400.0
                            ),
                            Numeric,
                        ),
                        1,
                    ).label("avg_lead_time_days"),
                    func.round(
                        cast(
                            (
                                func.sum(PurchaseOrderItems.delivered_qty)
                                * 1.0
                                / func.nullif(
                                    func.sum(PurchaseOrderItems.ordered_qty), 0
                                )
                            ),
                            Numeric,
                        ),
                        2,
                    ).label("fill_rate"),
                )
                .select_from(PurchaseOrders)
                .join(
                    PurchaseOrderItems,
                    PurchaseOrderItems.po_id == PurchaseOrders.id,
                )
                .where(
                    PurchaseOrders.vendor_id == vid,
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.created_at >= since,
                    PurchaseOrders.received_at.isnot(None),
                )
            )
            perf = s2.one()
        return VendorPerformance(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            days=days,
            po_count=int(summary.po_count or 0),
            total_spend=float(summary.total_spend or 0),
            received_count=int(summary.received_count or 0),
            avg_lead_time_days=float(perf.avg_lead_time_days)
            if perf.avg_lead_time_days is not None
            else None,
            fill_rate=float(perf.fill_rate)
            if perf.fill_rate is not None
            else None,
        )

    async def purchase_history(
        self, org_id: str, vendor_id: str, days: int = 90, limit: int = 20
    ) -> list[PurchaseHistoryItem]:
        oid = as_uuid_required(org_id)
        vid = as_uuid_required(vendor_id)
        since = datetime.now(UTC) - timedelta(days=days)
        async with self.session() as session:
            po_rows = await session.execute(
                select(
                    PurchaseOrders.id,
                    PurchaseOrders.vendor_name,
                    PurchaseOrders.document_date,
                    PurchaseOrders.total,
                    PurchaseOrders.status,
                    PurchaseOrders.created_at,
                    PurchaseOrders.received_at,
                )
                .where(
                    PurchaseOrders.vendor_id == vid,
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.created_at >= since,
                )
                .order_by(PurchaseOrders.created_at.desc())
                .limit(limit)
            )
            pos: list[PurchaseHistoryItem] = [
                PurchaseHistoryItem(
                    id=str(r.id),
                    vendor_name=r.vendor_name,
                    document_date=r.document_date,
                    total=r.total,
                    status=r.status,
                    created_at=r.created_at,
                    received_at=r.received_at,
                    items=[],
                    item_count=0,
                )
                for r in po_rows.all()
            ]
            for po in pos:
                item_result = await session.execute(
                    select(
                        PurchaseOrderItems.name,
                        PurchaseOrderItems.ordered_qty,
                        PurchaseOrderItems.delivered_qty,
                        PurchaseOrderItems.unit_price,
                        PurchaseOrderItems.cost,
                        PurchaseOrderItems.status,
                    ).where(
                        PurchaseOrderItems.po_id == as_uuid_required(po["id"]),
                        PurchaseOrderItems.organization_id == oid,
                    )
                )
                po["items"] = [dict(ir._mapping) for ir in item_result.all()]
                po["item_count"] = len(po["items"])
            return pos

    async def reorder_with_vendor_context(
        self, org_id: str, limit: int = 30
    ) -> list[ReorderRow]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(
                    Skus.id.label("sku_id"),
                    Skus.sku,
                    Skus.name,
                    Skus.quantity,
                    Skus.min_stock,
                    Skus.cost.label("current_cost"),
                    Skus.sell_uom,
                    Skus.category_name.label("department"),
                )
                .where(
                    Skus.quantity <= Skus.min_stock,
                    Skus.organization_id == oid,
                    Skus.deleted_at.is_(None),
                )
                .order_by((Skus.min_stock - Skus.quantity).desc())
                .limit(limit)
            )
            low_stock: list[ReorderRow] = [
                ReorderRow(
                    sku_id=str(r.sku_id),
                    sku=r.sku,
                    name=r.name,
                    quantity=float(r.quantity),
                    min_stock=int(r.min_stock),
                    current_cost=float(r.current_cost),
                    sell_uom=r.sell_uom,
                    department=r.department,
                    vendor_options=[],
                    deficit=0.0,
                )
                for r in result.all()
            ]
        vendor_items_by_sku = await get_database_manager().catalog.list_vendor_items_by_skus_grouped(
            org_id, [item["sku_id"] for item in low_stock]
        )
        for item in low_stock:
            vendor_items = vendor_items_by_sku.get(item["sku_id"], [])
            item["vendor_options"] = [
                {
                    "vendor_id": vi.vendor_id,
                    "vendor_name": vi.vendor_name,
                    "cost": vi.cost,
                    "lead_time_days": vi.lead_time_days,
                    "moq": vi.moq,
                    "is_preferred": vi.is_preferred,
                    "purchase_uom": vi.purchase_uom,
                    "purchase_pack_qty": vi.purchase_pack_qty,
                }
                for vi in vendor_items
            ]
            item["deficit"] = round(item["min_stock"] - item["quantity"], 2)
        return low_stock

    async def get_po_items_enriched(
        self, org_id: str, po_id: str
    ) -> list[POItemRow]:
        """PO line items with catalog enrichment (same as legacy queries.get_po_items)."""
        items = await self.get_po_items(org_id, po_id)
        sku_ids = [i.sku_id for i in items if i.sku_id]
        if not sku_ids:
            return items
        products: dict[str, Any] = {}
        for pid in set(sku_ids):
            p = await get_database_manager().catalog.get_sku_by_id(pid, org_id)
            if p:
                products[pid] = p
        enriched = []
        for item in items:
            pid = item.sku_id
            if pid and pid in products:
                p = products[pid]
                enriched.append(
                    item.model_copy(
                        update={
                            "matched_sku": p.sku,
                            "matched_name": p.name,
                            "matched_quantity": p.quantity,
                            "matched_cost": p.cost,
                        }
                    )
                )
            else:
                enriched.append(item)
        return enriched

    async def vendor_lead_time_actual(
        self, org_id: str, vendor_id: str, days: int = 180
    ) -> dict[str, Any]:
        """Lead time stats from received POs plus stated median lead from vendor_items."""
        oid = as_uuid_required(org_id)
        vid = as_uuid_required(vendor_id)
        since = datetime.now(UTC) - timedelta(days=days)
        async with self.session() as session:
            res = await session.execute(
                select(
                    PurchaseOrders.id,
                    (
                        func.extract(
                            "epoch",
                            PurchaseOrders.received_at
                            - PurchaseOrders.created_at,
                        )
                        / 86400.0
                    ).label("lead_days"),
                )
                .where(
                    PurchaseOrders.vendor_id == vid,
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrders.created_at >= since,
                    PurchaseOrders.received_at.isnot(None),
                )
                .order_by(PurchaseOrders.received_at)
            )
            rows = [dict(r._mapping) for r in res.all()]

            stated_scalar = await session.scalar(
                select(
                    func.percentile_cont(0.5).within_group(
                        VendorItems.lead_time_days
                    )
                ).where(
                    VendorItems.vendor_id == vid,
                    VendorItems.lead_time_days.isnot(None),
                    VendorItems.organization_id == oid,
                    VendorItems.deleted_at.is_(None),
                )
            )

        if not rows:
            return {
                "vendor_id": vendor_id,
                "po_count": 0,
                "actual_median_days": None,
                "actual_p90_days": None,
                "stated_days": None,
                "trend": "no_data",
            }

        lead_days = [float(r["lead_days"]) for r in rows]
        lead_days_sorted = sorted(lead_days)
        n = len(lead_days_sorted)
        median_days = lead_days_sorted[n // 2]
        p90_idx = min(int(n * 0.9), n - 1)
        p90_days = lead_days_sorted[p90_idx]

        trend = "stable"
        if n >= 4:
            recent_3 = lead_days[-3:]
            prior = lead_days[:-3]
            recent_avg = sum(recent_3) / len(recent_3)
            prior_avg = sum(prior) / len(prior)
            if prior_avg > 0:
                drift_pct = (recent_avg - prior_avg) / prior_avg * 100
                if drift_pct > 20:
                    trend = "degrading"
                elif drift_pct < -20:
                    trend = "improving"

        stated_days = (
            float(stated_scalar) if stated_scalar is not None else None
        )

        return {
            "vendor_id": vendor_id,
            "po_count": n,
            "actual_median_days": round(median_days, 1),
            "actual_p90_days": round(p90_days, 1),
            "stated_days": round(stated_days, 1) if stated_days else None,
            "trend": trend,
        }

    async def last_po_created_at_by_vendor_for_sku(
        self, org_id: str, sku_id: str
    ) -> dict[str, datetime | None]:
        """Latest PO created_at per vendor for order lines matching sku_id (org scoped)."""
        oid = as_uuid_required(org_id)
        sid = as_uuid_required(sku_id)
        async with self.session() as session:
            stmt = (
                select(
                    PurchaseOrders.vendor_id,
                    func.max(PurchaseOrders.created_at).label("last_po_date"),
                )
                .select_from(PurchaseOrders)
                .join(
                    PurchaseOrderItems,
                    PurchaseOrderItems.po_id == PurchaseOrders.id,
                )
                .where(
                    PurchaseOrders.organization_id == oid,
                    PurchaseOrderItems.sku_id == sid,
                )
                .group_by(PurchaseOrders.vendor_id)
            )
            result = await session.execute(stmt)
            rows = result.mappings().all()
        out: dict[str, datetime | None] = {}
        for r in rows:
            vid = r["vendor_id"]
            if vid is not None:
                out[str(vid)] = r["last_po_date"]
        return out
