"""Credit note persistence via SQLModel ORM (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from finance.domain.credit_note import CreditNote, CreditNoteLineItem
from finance.domain.enums import CreditNoteStatus, InvoiceStatus
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services.finance._helpers import uuids_to_str
from shared.infrastructure.types.public_sql_model_models import (
    CreditNoteLineItems,
    CreditNotes,
    InvoiceCounters,
    Invoices,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ApplyCreditNoteResult:
    __slots__ = ("auto_paid", "credit_note", "invoice_id")

    def __init__(self, credit_note: CreditNote, auto_paid: bool, invoice_id: str) -> None:
        self.credit_note = credit_note
        self.auto_paid = auto_paid
        self.invoice_id = invoice_id


async def _next_credit_note_number(session: AsyncSession, org_id: uuid.UUID) -> str:
    stmt = (
        pg_insert(InvoiceCounters)
        .values(organization_id=org_id, key="cn", counter=1)
        .on_conflict_do_update(
            index_elements=[
                InvoiceCounters.organization_id,
                InvoiceCounters.key,
            ],
            set_={"counter": InvoiceCounters.counter + 1},
        )
    )
    await session.execute(stmt)
    r = await session.execute(
        select(InvoiceCounters.counter).where(
            InvoiceCounters.organization_id == org_id,
            InvoiceCounters.key == "cn",
        )
    )
    num = r.scalar_one()
    return f"CN-{str(num).zfill(5)}"


def _cn_row_to_model(row: CreditNotes) -> CreditNote:
    d = uuids_to_str(row.model_dump(mode="python"))
    return CreditNote.model_validate(d)


def _cn_line_to_model(row: CreditNoteLineItems) -> CreditNoteLineItem:
    d = uuids_to_str(row.model_dump(mode="python"))
    return CreditNoteLineItem.model_validate(d)


async def credit_note_get_by_id(
    session: AsyncSession, org_id: uuid.UUID, credit_note_id: str
) -> CreditNote | None:
    cid = as_uuid_required(credit_note_id)
    r = await session.execute(
        select(CreditNotes).where(
            CreditNotes.id == cid,
            CreditNotes.organization_id == org_id,
        )
    )
    row = r.scalar_one_or_none()
    if row is None:
        return None
    cn = _cn_row_to_model(row)
    lr = await session.execute(
        select(CreditNoteLineItems)
        .where(CreditNoteLineItems.credit_note_id == cid)
        .order_by(CreditNoteLineItems.id)
    )
    cn.line_items = [_cn_line_to_model(x) for x in lr.scalars().all()]
    return cn


async def credit_note_insert(
    session: AsyncSession,
    org_id: uuid.UUID,
    return_id: str,
    invoice_id: str | None,
    items: list[dict],
    subtotal: float,
    tax: float,
    total: float,
) -> CreditNote:
    cn_id = new_uuid7_str()
    now = datetime.now(UTC)
    cn_number = await _next_credit_note_number(session, org_id)
    billing_entity = ""
    inv_uuid = as_uuid_required(invoice_id) if invoice_id else None
    if inv_uuid:
        ir = await session.execute(
            select(Invoices.billing_entity).where(
                Invoices.id == inv_uuid,
                Invoices.organization_id == org_id,
            )
        )
        be = ir.scalar_one_or_none()
        if be:
            billing_entity = be
    rid = as_uuid_required(return_id)
    session.add(
        CreditNotes(
            id=as_uuid_required(cn_id),
            credit_note_number=cn_number,
            invoice_id=inv_uuid,
            return_id=rid,
            billing_entity=billing_entity,
            status="draft",
            subtotal=subtotal,
            tax=tax,
            total=total,
            notes=None,
            xero_credit_note_id=None,
            organization_id=org_id,
            created_at=now,
            updated_at=now,
            xero_sync_status="pending",
        )
    )
    for item in items:
        qty = item.get("quantity", 1)
        price = float(item.get("unit_price") or item.get("price") or 0)
        amt = round(qty * price, 2)
        session.add(
            CreditNoteLineItems(
                id=as_uuid_required(new_uuid7_str()),
                credit_note_id=as_uuid_required(cn_id),
                description=item.get("name") or item.get("description", ""),
                quantity=float(qty),
                unit_price=price,
                amount=amt,
                cost=float(item.get("cost", 0)),
                sku_id=as_uuid_required(item["sku_id"]) if item.get("sku_id") else None,
                unit="each",
                sell_cost=float(item.get("cost", 0)),
            )
        )
    await session.flush()
    result = await credit_note_get_by_id(session, org_id, cn_id)
    if not result:
        raise RuntimeError(f"Credit note {cn_id} missing immediately after insert")
    return result


async def credit_note_list(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    invoice_id: str | None = None,
    billing_entity: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[CreditNote]:
    conds = [CreditNotes.organization_id == org_id]
    if invoice_id:
        conds.append(CreditNotes.invoice_id == as_uuid_required(invoice_id))
    if billing_entity:
        conds.append(CreditNotes.billing_entity == billing_entity)
    if status:
        conds.append(CreditNotes.status == status)
    if start_date:
        conds.append(CreditNotes.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conds.append(CreditNotes.created_at <= datetime.fromisoformat(end_date))
    r = await session.execute(
        select(CreditNotes).where(and_(*conds)).order_by(CreditNotes.created_at.desc()).limit(limit)
    )
    return [_cn_row_to_model(x) for x in r.scalars().all()]


async def credit_note_apply(
    session: AsyncSession, org_id: uuid.UUID, credit_note_id: str
) -> ApplyCreditNoteResult:
    cn = await credit_note_get_by_id(session, org_id, credit_note_id)
    if not cn:
        raise ValueError("Credit note not found")
    if cn.status != CreditNoteStatus.DRAFT:
        raise ValueError(f"Credit note is already {cn.status}")
    if not cn.invoice_id:
        raise ValueError("Credit note has no linked invoice")

    inv_id = cn.invoice_id
    cn_total = cn.total
    iid = as_uuid_required(inv_id)
    ir = await session.execute(
        select(Invoices.total, Invoices.amount_credited, Invoices.status).where(
            Invoices.id == iid,
            Invoices.organization_id == org_id,
        )
    )
    inv_row = ir.first()
    if not inv_row:
        raise ValueError(f"Linked invoice {inv_id} not found")
    total, amount_credited, inv_status = inv_row[0], inv_row[1], inv_row[2]
    new_credited = round(float(amount_credited or 0) + cn_total, 2)
    balance_due = round(float(total) - new_credited, 2)
    now = datetime.now(UTC)

    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(amount_credited=new_credited, updated_at=now)
    )
    auto_paid = False
    if balance_due <= 0 and inv_status != InvoiceStatus.PAID.value:
        await session.execute(
            update(Invoices)
            .where(Invoices.id == iid, Invoices.organization_id == org_id)
            .values(status=InvoiceStatus.PAID.value, updated_at=now)
        )
        auto_paid = True

    await session.execute(
        update(CreditNotes)
        .where(
            CreditNotes.id == as_uuid_required(credit_note_id),
            CreditNotes.organization_id == org_id,
        )
        .values(status=CreditNoteStatus.APPLIED.value, updated_at=now)
    )
    await session.flush()
    updated = await credit_note_get_by_id(session, org_id, credit_note_id)
    if not updated:
        raise RuntimeError(f"Credit note {credit_note_id} missing after apply")
    return ApplyCreditNoteResult(credit_note=updated, auto_paid=auto_paid, invoice_id=inv_id)


async def credit_note_set_xero_id(
    session: AsyncSession,
    org_id: uuid.UUID,
    credit_note_id: str,
    xero_credit_note_id: str,
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(CreditNotes)
        .where(
            CreditNotes.id == as_uuid_required(credit_note_id),
            CreditNotes.organization_id == org_id,
        )
        .values(
            xero_credit_note_id=xero_credit_note_id,
            xero_sync_status="synced",
            updated_at=now,
        )
    )
    await session.flush()


async def credit_note_set_sync_status(
    session: AsyncSession,
    org_id: uuid.UUID,
    credit_note_id: str,
    status: str,
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(CreditNotes)
        .where(
            CreditNotes.id == as_uuid_required(credit_note_id),
            CreditNotes.organization_id == org_id,
        )
        .values(xero_sync_status=status, updated_at=now)
    )
    await session.flush()


async def credit_note_list_unsynced(session: AsyncSession, org_id: uuid.UUID) -> list[CreditNote]:
    r = await session.execute(
        select(CreditNotes)
        .where(
            CreditNotes.organization_id == org_id,
            CreditNotes.status == "applied",
            CreditNotes.xero_credit_note_id.is_(None),
        )
        .order_by(CreditNotes.created_at)
    )
    return [_cn_row_to_model(x) for x in r.scalars().all()]


async def credit_note_list_needing_reconciliation(
    session: AsyncSession, org_id: uuid.UUID
) -> list[CreditNote]:
    r = await session.execute(
        select(CreditNotes)
        .where(
            CreditNotes.organization_id == org_id,
            CreditNotes.xero_credit_note_id.is_not(None),
            CreditNotes.xero_sync_status != "mismatch",
        )
        .order_by(CreditNotes.created_at)
    )
    rows = r.scalars().all()
    if not rows:
        return []
    ids = [x.id for x in rows]
    cr = await session.execute(
        select(CreditNoteLineItems.credit_note_id, func.count())
        .where(CreditNoteLineItems.credit_note_id.in_(ids))
        .group_by(CreditNoteLineItems.credit_note_id)
    )
    count_map = {row[0]: int(row[1]) for row in cr.all()}
    out: list[CreditNote] = []
    for row in rows:
        d = uuids_to_str(row.model_dump(mode="python"))
        d["line_count"] = count_map.get(row.id, 0)
        out.append(CreditNote.model_validate(d))
    return out


async def credit_note_list_failed(session: AsyncSession, org_id: uuid.UUID) -> list[CreditNote]:
    r = await session.execute(
        select(CreditNotes)
        .where(
            CreditNotes.organization_id == org_id,
            CreditNotes.xero_sync_status == "failed",
        )
        .order_by(CreditNotes.created_at)
    )
    return [_cn_row_to_model(x) for x in r.scalars().all()]


async def credit_note_list_mismatch(session: AsyncSession, org_id: uuid.UUID) -> list[CreditNote]:
    r = await session.execute(
        select(CreditNotes)
        .where(
            CreditNotes.organization_id == org_id,
            CreditNotes.xero_sync_status == "mismatch",
        )
        .order_by(CreditNotes.created_at)
    )
    return [_cn_row_to_model(x) for x in r.scalars().all()]
