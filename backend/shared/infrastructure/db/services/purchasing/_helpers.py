"""Row mapping and SQLModel builders for purchasing / PO persistence."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from finance.domain.enums import XeroSyncStatus

if TYPE_CHECKING:
    from uuid import UUID
from purchasing.domain.purchase_order import (
    POItemRow,
    POItemStatus,
    PORow,
    POStatus,
    PurchaseOrder,
    PurchaseOrderItem,
)
from shared.infrastructure.db.orm_utils import as_uuid, as_uuid_required
from shared.infrastructure.types.public_sql_model_models import (
    PurchaseOrderItems,
    PurchaseOrders,
)


def _document_date_for_row(po: PurchaseOrder) -> str | None:
    dd = po.document_date
    if dd is None:
        return None
    if isinstance(dd, datetime):
        return dd.date().isoformat()
    if isinstance(dd, date):
        return dd.isoformat()
    return str(dd)


def build_purchase_orders_row(
    po: PurchaseOrder, org_uuid: UUID
) -> PurchaseOrders:
    """Map domain PurchaseOrder to SQLModel row for insert."""
    return PurchaseOrders(
        id=as_uuid_required(po.id),
        vendor_id=as_uuid(po.vendor_id),
        vendor_name=po.vendor_name,
        document_date=_document_date_for_row(po),
        total=po.total,
        status=po.status.value
        if isinstance(po.status, POStatus)
        else str(po.status),
        notes=po.notes,
        created_by_id=as_uuid_required(po.created_by_id),
        created_by_name=po.created_by_name,
        received_at=po.received_at,
        received_by_id=as_uuid(po.received_by_id),
        received_by_name=po.received_by_name,
        created_at=po.created_at,
        updated_at=po.updated_at,
        organization_id=org_uuid,
        xero_sync_status=str(XeroSyncStatus.PENDING),
    )


def build_purchase_order_item_row(
    item: PurchaseOrderItem,
) -> PurchaseOrderItems:
    st = (
        item.status.value
        if isinstance(item.status, POItemStatus)
        else str(item.status)
    )
    return PurchaseOrderItems(
        id=as_uuid_required(item.id),
        po_id=as_uuid_required(item.po_id),
        name=item.name,
        original_sku=item.original_sku,
        ordered_qty=item.ordered_qty,
        delivered_qty=item.delivered_qty,
        unit_price=item.unit_price,
        cost=item.cost,
        base_unit=item.base_unit,
        sell_uom=item.sell_uom,
        pack_qty=item.pack_qty,
        purchase_uom=item.purchase_uom,
        purchase_pack_qty=item.purchase_pack_qty,
        suggested_department=item.suggested_department,
        status=st,
        sku_id=as_uuid(item.sku_id),
        organization_id=as_uuid_required(item.organization_id),
    )


def purchase_orders_row_to_porow(
    row: PurchaseOrders,
    *,
    item_count: int = 0,
    ordered_count: int = 0,
    pending_count: int = 0,
    arrived_count: int = 0,
) -> PORow:
    xs = row.xero_sync_status
    return PORow(
        id=str(row.id),
        vendor_id=str(row.vendor_id) if row.vendor_id else "",
        vendor_name=row.vendor_name or "",
        document_date=_parse_document_date(row.document_date),
        total=row.total,
        status=POStatus(row.status),
        notes=row.notes,
        created_by_id=str(row.created_by_id),
        created_by_name=row.created_by_name,
        received_at=row.received_at,
        received_by_id=str(row.received_by_id) if row.received_by_id else None,
        received_by_name=row.received_by_name,
        created_at=row.created_at,
        updated_at=row.updated_at,
        organization_id=str(row.organization_id) if row.organization_id else "",
        xero_bill_id=row.xero_bill_id,
        xero_sync_status=XeroSyncStatus(xs) if xs else None,
        item_count=item_count,
        ordered_count=ordered_count,
        pending_count=pending_count,
        arrived_count=arrived_count,
    )


def _parse_document_date(raw: str | None) -> datetime | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.combine(
                datetime.strptime(raw, "%Y-%m-%d").date(), datetime.min.time()
            )
        except ValueError:
            return None


def purchase_order_item_row_to_poitemrow(row: PurchaseOrderItems) -> POItemRow:
    return POItemRow(
        id=str(row.id),
        po_id=str(row.po_id),
        name=row.name,
        original_sku=row.original_sku,
        ordered_qty=row.ordered_qty,
        delivered_qty=row.delivered_qty,
        unit_price=row.unit_price,
        cost=row.cost,
        base_unit=row.base_unit,
        sell_uom=row.sell_uom,
        pack_qty=row.pack_qty,
        purchase_uom=row.purchase_uom,
        purchase_pack_qty=row.purchase_pack_qty,
        suggested_department=row.suggested_department,
        status=POItemStatus(row.status),
        sku_id=str(row.sku_id) if row.sku_id else None,
        organization_id=str(row.organization_id) if row.organization_id else "",
    )
