"""Row mapping and batch hydration for operations persistence."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from operations.domain.enums import MaterialRequestStatus, PaymentStatus
from operations.domain.material_request import MaterialRequest
from operations.domain.returns import MaterialReturn, ReturnItem
from operations.domain.withdrawal import (
    MaterialWithdrawal,
    WithdrawalItem,
)
from shared.helpers.uuid import new_uuid7
from shared.infrastructure.db.orm_utils import (
    as_uuid,
    as_uuid_required,
    uuid_str,
)
from shared.infrastructure.types.public_sql_model_models import (
    MaterialRequestItems,
    MaterialRequests,
    ReturnItems,
    Returns,
    WithdrawalItems,
    Withdrawals,
)

# Sentinel for line items without a catalog SKU (legacy / free-text rows).
NIL_SKU_UUID = uuid.UUID(int=0)


def line_item_sku_uuid(sku_id: str | None) -> uuid.UUID:
    if not sku_id:
        return NIL_SKU_UUID
    return uuid.UUID(str(sku_id))


def withdrawal_item_to_line_dict(row: WithdrawalItems) -> dict:
    sid = row.sku_id
    return {
        "sku_id": "" if sid == NIL_SKU_UUID else str(sid),
        "sku": row.sku,
        "name": row.name,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "cost": row.cost,
        "unit": row.unit,
        "sell_uom": row.sell_uom,
        "sell_cost": row.sell_cost,
    }


def material_request_item_to_line_dict(row: MaterialRequestItems) -> dict:
    sid = row.sku_id
    return {
        "sku_id": "" if sid == NIL_SKU_UUID else str(sid),
        "sku": row.sku,
        "name": row.name,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "cost": row.cost,
        "unit": row.unit,
    }


def return_item_to_line_dict(row: ReturnItems) -> dict:
    sid = row.sku_id
    return {
        "sku_id": "" if sid == NIL_SKU_UUID else str(sid),
        "sku": row.sku,
        "name": row.name,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "cost": row.cost,
        "unit": row.unit,
        "sell_uom": row.sell_uom,
        "sell_cost": row.sell_cost,
    }


def withdrawal_row_to_domain(row: Withdrawals, items: list[dict]) -> MaterialWithdrawal:
    d = {
        "id": str(row.id),
        "organization_id": str(row.organization_id) if row.organization_id else "",
        "created_at": row.created_at,
        "job_id": str(row.job_id),
        "service_address": row.service_address,
        "notes": row.notes,
        "subtotal": row.subtotal,
        "tax": row.tax,
        "tax_rate": row.tax_rate,
        "total": row.total,
        "cost_total": row.cost_total,
        "contractor_id": str(row.contractor_id),
        "contractor_name": row.contractor_name,
        "contractor_company": row.contractor_company,
        "billing_entity": row.billing_entity,
        "billing_entity_id": uuid_str(row.billing_entity_id),
        "payment_status": PaymentStatus(row.payment_status),
        "invoice_id": uuid_str(row.invoice_id),
        "paid_at": row.paid_at,
        "processed_by_id": str(row.processed_by_id),
        "processed_by_name": row.processed_by_name,
        "items": items,
    }
    return MaterialWithdrawal.model_validate(d)


def material_request_row_to_domain(row: MaterialRequests, items: list[dict]) -> MaterialRequest:
    d = {
        "id": str(row.id),
        "organization_id": str(row.organization_id),
        "created_at": row.created_at,
        "contractor_id": str(row.contractor_id),
        "contractor_name": row.contractor_name,
        "status": MaterialRequestStatus(row.status),
        "withdrawal_id": uuid_str(row.withdrawal_id),
        "job_id": uuid_str(row.job_id),
        "service_address": row.service_address,
        "notes": row.notes,
        "processed_at": row.processed_at,
        "processed_by_id": uuid_str(row.processed_by_id),
        "items": items,
    }
    return MaterialRequest.model_validate(d)


def return_row_to_domain(row: Returns, items: list[dict]) -> MaterialReturn:
    d: dict = {
        "id": str(row.id),
        "organization_id": str(row.organization_id) if row.organization_id else "",
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "withdrawal_id": str(row.withdrawal_id),
        "contractor_id": str(row.contractor_id),
        "contractor_name": row.contractor_name,
        "billing_entity": row.billing_entity,
        "job_id": str(row.job_id),
        "subtotal": row.subtotal,
        "tax": row.tax,
        "total": row.total,
        "cost_total": row.cost_total,
        "reason": row.reason,
        "notes": row.notes,
        "credit_note_id": uuid_str(row.credit_note_id),
        "processed_by_id": str(row.processed_by_id),
        "processed_by_name": row.processed_by_name,
        "items": [ReturnItem.model_validate(x) for x in items],
    }
    return MaterialReturn.model_validate(d)


async def load_withdrawal_items_batch(
    session: AsyncSession, withdrawal_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict]]:
    if not withdrawal_ids:
        return {}
    result = await session.execute(
        select(WithdrawalItems)
        .where(WithdrawalItems.withdrawal_id.in_(withdrawal_ids))
        .order_by(WithdrawalItems.id)
    )
    by_w: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for it in result.scalars().all():
        by_w[it.withdrawal_id].append(withdrawal_item_to_line_dict(it))
    return by_w


async def hydrate_withdrawal(session: AsyncSession, row: Withdrawals) -> MaterialWithdrawal:
    items_map = await load_withdrawal_items_batch(session, [row.id])
    return withdrawal_row_to_domain(row, items_map.get(row.id, []))


async def hydrate_withdrawals(
    session: AsyncSession, rows: list[Withdrawals]
) -> list[MaterialWithdrawal]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    item_map = await load_withdrawal_items_batch(session, ids)
    return [withdrawal_row_to_domain(r, item_map.get(r.id, [])) for r in rows]


async def load_material_request_items_batch(
    session: AsyncSession, request_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict]]:
    if not request_ids:
        return {}
    result = await session.execute(
        select(MaterialRequestItems)
        .where(MaterialRequestItems.material_request_id.in_(request_ids))
        .order_by(MaterialRequestItems.id)
    )
    by_r: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for it in result.scalars().all():
        by_r[it.material_request_id].append(material_request_item_to_line_dict(it))
    return by_r


async def hydrate_material_requests(
    session: AsyncSession, rows: list[MaterialRequests]
) -> list[MaterialRequest]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    item_map = await load_material_request_items_batch(session, ids)
    return [material_request_row_to_domain(r, item_map.get(r.id, [])) for r in rows]


async def hydrate_material_request(session: AsyncSession, row: MaterialRequests) -> MaterialRequest:
    items_map = await load_material_request_items_batch(session, [row.id])
    return material_request_row_to_domain(row, items_map.get(row.id, []))


async def load_return_items_batch(
    session: AsyncSession, return_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[dict]]:
    if not return_ids:
        return {}
    result = await session.execute(
        select(ReturnItems).where(ReturnItems.return_id.in_(return_ids)).order_by(ReturnItems.id)
    )
    by_r: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for it in result.scalars().all():
        by_r[it.return_id].append(return_item_to_line_dict(it))
    return by_r


async def hydrate_returns(session: AsyncSession, rows: list[Returns]) -> list[MaterialReturn]:
    if not rows:
        return []
    ids = [r.id for r in rows]
    item_map = await load_return_items_batch(session, ids)
    return [return_row_to_domain(r, item_map.get(r.id, [])) for r in rows]


async def hydrate_return(session: AsyncSession, row: Returns) -> MaterialReturn:
    items_map = await load_return_items_batch(session, [row.id])
    return return_row_to_domain(row, items_map.get(row.id, []))


def build_withdrawal_row(withdrawal: MaterialWithdrawal, org_uuid: uuid.UUID) -> Withdrawals:
    return Withdrawals(
        id=as_uuid_required(withdrawal.id),
        job_id=as_uuid_required(withdrawal.job_id),
        service_address=withdrawal.service_address,
        notes=withdrawal.notes,
        subtotal=withdrawal.subtotal,
        tax=withdrawal.tax,
        tax_rate=withdrawal.tax_rate,
        total=withdrawal.total,
        cost_total=withdrawal.cost_total,
        contractor_id=as_uuid_required(withdrawal.contractor_id),
        contractor_name=withdrawal.contractor_name,
        contractor_company=withdrawal.contractor_company,
        billing_entity=withdrawal.billing_entity,
        billing_entity_id=as_uuid(withdrawal.billing_entity_id),
        payment_status=str(withdrawal.payment_status),
        invoice_id=as_uuid(withdrawal.invoice_id),
        paid_at=withdrawal.paid_at,
        processed_by_id=as_uuid_required(withdrawal.processed_by_id),
        processed_by_name=withdrawal.processed_by_name,
        organization_id=org_uuid,
        created_at=withdrawal.created_at,
    )


def build_withdrawal_item_row(withdrawal_id: uuid.UUID, item: WithdrawalItem) -> WithdrawalItems:
    qty = item.quantity
    price = item.unit_price
    cost = item.cost
    return WithdrawalItems(
        id=new_uuid7(),
        withdrawal_id=withdrawal_id,
        sku_id=line_item_sku_uuid(item.sku_id),
        sku=item.sku or "",
        name=item.name or "",
        quantity=qty,
        unit_price=price,
        cost=cost,
        unit=item.unit or "each",
        amount=round(qty * price, 2),
        cost_total=round(qty * cost, 2),
        sell_uom=item.sell_uom or "each",
        sell_cost=item.sell_cost,
    )


def build_material_request_row(request: MaterialRequest, org_uuid: uuid.UUID) -> MaterialRequests:
    return MaterialRequests(
        id=as_uuid_required(request.id),
        contractor_id=as_uuid_required(request.contractor_id),
        contractor_name=request.contractor_name,
        status=str(request.status),
        withdrawal_id=as_uuid(request.withdrawal_id),
        job_id=as_uuid(request.job_id) if request.job_id else None,
        service_address=request.service_address,
        notes=request.notes,
        created_at=request.created_at,
        processed_at=request.processed_at,
        processed_by_id=as_uuid(request.processed_by_id),
        organization_id=org_uuid,
    )


def build_material_request_item_row(
    request_id: uuid.UUID, item: WithdrawalItem
) -> MaterialRequestItems:
    return MaterialRequestItems(
        id=new_uuid7(),
        material_request_id=request_id,
        sku_id=line_item_sku_uuid(item.sku_id),
        sku=item.sku or "",
        name=item.name or "",
        quantity=item.quantity,
        unit_price=item.unit_price,
        cost=item.cost,
        unit=item.unit or "each",
    )


def build_return_row(ret: MaterialReturn, org_uuid: uuid.UUID) -> Returns:
    return Returns(
        id=as_uuid_required(ret.id),
        withdrawal_id=as_uuid_required(ret.withdrawal_id),
        contractor_id=as_uuid_required(ret.contractor_id),
        contractor_name=ret.contractor_name,
        billing_entity=ret.billing_entity,
        billing_entity_id=None,
        job_id=as_uuid_required(ret.job_id),
        subtotal=ret.subtotal,
        tax=ret.tax,
        total=ret.total,
        cost_total=ret.cost_total,
        reason=str(ret.reason),
        notes=ret.notes,
        credit_note_id=as_uuid(ret.credit_note_id),
        processed_by_id=as_uuid_required(ret.processed_by_id),
        processed_by_name=ret.processed_by_name,
        organization_id=org_uuid,
        created_at=ret.created_at,
        updated_at=ret.updated_at,
    )


def build_return_item_row(return_id: uuid.UUID, item: ReturnItem) -> ReturnItems:
    qty = item.quantity
    price = item.unit_price
    cost = item.cost
    return ReturnItems(
        id=new_uuid7(),
        return_id=return_id,
        sku_id=line_item_sku_uuid(item.sku_id),
        sku=item.sku or "",
        name=item.name or "",
        quantity=qty,
        unit_price=price,
        cost=cost,
        unit=item.unit or "each",
        amount=round(qty * price, 2),
        cost_total=round(qty * cost, 2),
        sell_uom=item.sell_uom or "each",
        sell_cost=item.sell_cost,
    )
