"""Purchasing / PO persistence and queries. ``org_id`` is explicit on the facade."""

from __future__ import annotations

from datetime import datetime

from purchasing.domain.purchase_order import (
    POItemRow,
    POItemStatus,
    PORow,
    PurchaseOrder,
    PurchaseOrderItem,
)
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services._org_scope import scoped_org


class PurchasingDatabaseService(DomainDatabaseService):
    async def insert_po(self, org_id: str, po: PurchaseOrder) -> None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            await po_repo.insert_po(po)

    async def insert_po_items(
        self, org_id: str, items: list[PurchaseOrderItem]
    ) -> None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            await po_repo.insert_items(items)

    async def list_pos(
        self, org_id: str, status: str | None = None
    ) -> list[PORow]:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.list_pos(status=status)

    async def list_pos_with_counts(
        self, org_id: str, status: str | None = None
    ) -> list[PORow]:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.list_pos_with_counts(status=status)

    async def get_po(self, org_id: str, po_id: str) -> PORow | None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.get_po(po_id)

    async def get_po_items(self, org_id: str, po_id: str) -> list[POItemRow]:
        from purchasing.application import queries as pq

        async with scoped_org(org_id):
            return await pq.get_po_items(po_id)

    async def update_po_item(
        self,
        org_id: str,
        item_id: str,
        status: POItemStatus,
        sku_id: str | None = None,
        delivered_qty: float | None = None,
    ) -> bool:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.update_po_item(
                item_id, status, sku_id=sku_id, delivered_qty=delivered_qty
            )

    async def update_po_status(
        self,
        org_id: str,
        po_id: str,
        status: str,
        received_at: str | None = None,
        received_by_id: str | None = None,
        received_by_name: str | None = None,
    ) -> None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            await po_repo.update_po_status(
                po_id,
                status,
                received_at=received_at,
                received_by_id=received_by_id,
                received_by_name=received_by_name,
            )

    async def list_unsynced_po_bills(self, org_id: str) -> list[dict]:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.list_unsynced_po_bills()

    async def list_failed_po_bills(self, org_id: str) -> list[dict]:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.list_failed_po_bills()

    async def get_po_with_cost(self, org_id: str, po_id: str) -> dict | None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.get_po_with_cost(po_id)

    async def set_po_xero_sync_status(
        self, org_id: str, po_id: str, status: str, updated_at: datetime
    ) -> None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            await po_repo.set_xero_sync_status(po_id, status, updated_at)

    async def po_summary_by_status(self, org_id: str) -> dict[str, dict]:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            return await po_repo.summary_by_status()

    async def set_po_xero_bill_id(
        self, org_id: str, po_id: str, xero_bill_id: str, updated_at: datetime
    ) -> None:
        from purchasing.infrastructure.po_repo import po_repo

        async with scoped_org(org_id):
            await po_repo.set_xero_bill_id(po_id, xero_bill_id, updated_at)

    async def vendor_catalog(self, org_id: str, vendor_id: str):
        from purchasing.application import queries as pq

        async with scoped_org(org_id):
            return await pq.vendor_catalog(vendor_id)

    async def vendor_performance(
        self,
        org_id: str,
        vendor_id: str,
        days: int = 90,
        vendor_name: str = "",
    ):
        from purchasing.application import queries as pq

        async with scoped_org(org_id):
            return await pq.vendor_performance(
                vendor_id, days=days, vendor_name=vendor_name
            )

    async def purchase_history(
        self, org_id: str, vendor_id: str, days: int = 90, limit: int = 20
    ):
        from purchasing.application import queries as pq

        async with scoped_org(org_id):
            return await pq.purchase_history(vendor_id, days=days, limit=limit)

    async def reorder_with_vendor_context(self, org_id: str, limit: int = 30):
        from purchasing.application import queries as pq

        async with scoped_org(org_id):
            return await pq.reorder_with_vendor_context(limit=limit)

    async def vendor_lead_time_actual(
        self, org_id: str, vendor_id: str, days: int = 180
    ):
        from purchasing.application import analytics as pa

        async with scoped_org(org_id):
            return await pa.vendor_lead_time_actual(vendor_id, days=days)

    async def reorder_point_smart(
        self,
        org_id: str,
        limit: int = 30,
        velocity_days: int = 30,
        safety_factor: float = 1.5,
    ):
        from purchasing.application import analytics as pa

        async with scoped_org(org_id):
            return await pa.reorder_point_smart(
                limit=limit,
                velocity_days=velocity_days,
                safety_factor=safety_factor,
            )
