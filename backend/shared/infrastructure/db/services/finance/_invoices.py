"""Invoice persistence via SQLModel ORM (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from finance.domain.invoice import (
    Invoice,
    InvoiceLineItem,
    InvoiceWithDetails,
    compute_due_date,
)
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db.orm_utils import as_uuid, as_uuid_required
from shared.infrastructure.db.services.finance._helpers import uuids_to_str
from shared.infrastructure.types.public_sql_model_models import (
    InvoiceCounters,
    InvoiceLineItems,
    Invoices,
    InvoiceWithdrawals,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _inv_row_to_domain(inv: Invoices) -> dict[str, Any]:
    d = uuids_to_str(inv.model_dump(mode="python"))
    return d


def _line_to_domain(li: InvoiceLineItems) -> InvoiceLineItem:
    d = uuids_to_str(li.model_dump(mode="python"))
    return InvoiceLineItem.model_validate(d)


async def invoice_next_number(session: AsyncSession, org_id: uuid.UUID) -> str:
    stmt = (
        pg_insert(InvoiceCounters)
        .values(organization_id=org_id, key="inv", counter=1)
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
            InvoiceCounters.key == "inv",
        )
    )
    num = r.scalar_one()
    return f"INV-{str(num).zfill(5)}"


async def invoice_get_by_id(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: str
) -> InvoiceWithDetails | None:
    iid = as_uuid_required(invoice_id)
    r = await session.execute(
        select(Invoices).where(
            Invoices.id == iid,
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
        )
    )
    inv = r.scalar_one_or_none()
    if inv is None:
        return None
    lr = await session.execute(
        select(InvoiceLineItems)
        .where(InvoiceLineItems.invoice_id == iid)
        .order_by(InvoiceLineItems.id)
    )
    lines = lr.scalars().all()
    wr = await session.execute(
        select(InvoiceWithdrawals.withdrawal_id).where(
            InvoiceWithdrawals.invoice_id == iid
        )
    )
    wids = [str(x[0]) for x in wr.all()]
    d = _inv_row_to_domain(inv)
    d["line_items"] = [_line_to_domain(li) for li in lines]
    d["withdrawal_ids"] = wids
    return InvoiceWithDetails.model_validate(d)


async def invoice_insert(
    session: AsyncSession, org_id: uuid.UUID, invoice: Invoice
) -> InvoiceWithDetails | None:
    invoice_dict = invoice.model_dump()
    invoice_id = invoice_dict.get("id") or new_uuid7_str()
    invoice_number = invoice_dict.get(
        "invoice_number"
    ) or await invoice_next_number(session, org_id)
    now = datetime.now(UTC)
    inv_date = invoice_dict.get("invoice_date") or now
    payment_terms = invoice_dict.get("payment_terms") or "net_30"
    due_date = invoice_dict.get("due_date") or compute_due_date(
        inv_date, payment_terms
    )
    appr = invoice_dict.get("approved_by_id")
    row = Invoices(
        id=as_uuid_required(invoice_id),
        invoice_number=invoice_number,
        billing_entity=invoice_dict.get("billing_entity", ""),
        contact_name=invoice_dict.get("contact_name", ""),
        contact_email=invoice_dict.get("contact_email", ""),
        status=invoice_dict.get("status", "draft"),
        subtotal=float(invoice_dict.get("subtotal", 0)),
        tax=float(invoice_dict.get("tax", 0)),
        tax_rate=float(invoice_dict.get("tax_rate", 0)),
        total=float(invoice_dict.get("total", 0)),
        amount_credited=float(invoice_dict.get("amount_credited", 0)),
        notes=invoice_dict.get("notes"),
        invoice_date=inv_date,
        due_date=due_date,
        payment_terms=payment_terms,
        billing_address=invoice_dict.get("billing_address", ""),
        po_reference=invoice_dict.get("po_reference", ""),
        currency=invoice_dict.get("currency", "USD"),
        approved_by_id=as_uuid(appr),
        approved_at=invoice_dict.get("approved_at"),
        xero_invoice_id=invoice_dict.get("xero_invoice_id"),
        organization_id=org_id,
        created_at=invoice_dict.get("created_at") or now,
        updated_at=invoice_dict.get("updated_at") or now,
        xero_sync_status="pending",
    )
    beid = invoice_dict.get("billing_entity_id")
    if beid:
        row.billing_entity_id = as_uuid_required(beid)
    session.add(row)
    await session.flush()
    return await invoice_get_by_id(session, org_id, invoice_id)


async def invoice_list(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: str | None = None,
    billing_entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 1000,
) -> list[InvoiceWithDetails]:
    conds = [
        Invoices.organization_id == org_id,
        Invoices.deleted_at.is_(None),
    ]
    if status:
        conds.append(Invoices.status == status)
    if billing_entity:
        conds.append(Invoices.billing_entity == billing_entity)
    if start_date:
        conds.append(Invoices.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        conds.append(Invoices.created_at <= datetime.fromisoformat(end_date))
    r = await session.execute(
        select(Invoices)
        .where(and_(*conds))
        .order_by(Invoices.created_at.desc())
        .limit(limit)
    )
    invs = r.scalars().all()
    if not invs:
        return []
    ids = [i.id for i in invs]
    wid_rows = await session.execute(
        select(
            InvoiceWithdrawals.invoice_id, InvoiceWithdrawals.withdrawal_id
        ).where(InvoiceWithdrawals.invoice_id.in_(ids))
    )
    wid_map: dict[uuid.UUID, list[str]] = {}
    for iid, wid in wid_rows.all():
        wid_map.setdefault(iid, []).append(str(wid))
    out: list[InvoiceWithDetails] = []
    for inv in invs:
        lr = await session.execute(
            select(InvoiceLineItems)
            .where(InvoiceLineItems.invoice_id == inv.id)
            .order_by(InvoiceLineItems.id)
        )
        lines = lr.scalars().all()
        d = _inv_row_to_domain(inv)
        d["line_items"] = [_line_to_domain(li) for li in lines]
        wids = wid_map.get(inv.id, [])
        d["withdrawal_ids"] = wids
        d["withdrawal_count"] = len(wids)
        out.append(InvoiceWithDetails.model_validate(d))
    return out


async def _ensure_invoice_org(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: str
) -> uuid.UUID:
    iid = as_uuid_required(invoice_id)
    r = await session.execute(
        select(Invoices.id).where(
            Invoices.id == iid,
            Invoices.organization_id == org_id,
        )
    )
    if r.scalar_one_or_none() is None:
        raise ValueError(f"Invoice {invoice_id} not found in this organisation")
    return iid


async def invoice_update_fields(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    updates: dict[str, Any],
) -> InvoiceWithDetails | None:
    if not updates:
        return await invoice_get_by_id(session, org_id, invoice_id)
    iid = as_uuid_required(invoice_id)
    now = datetime.now(UTC)
    vals = {**updates, "updated_at": now}
    cols = set(Invoices.__table__.columns.keys())
    safe = {k: v for k, v in vals.items() if k in cols and k != "id"}
    if not safe:
        return await invoice_get_by_id(session, org_id, invoice_id)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(**safe)
    )
    await session.flush()
    return await invoice_get_by_id(session, org_id, invoice_id)


async def invoice_replace_line_items(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    line_items: list[dict],
) -> float:
    iid = await _ensure_invoice_org(session, org_id, invoice_id)
    await session.execute(
        delete(InvoiceLineItems).where(InvoiceLineItems.invoice_id == iid)
    )
    subtotal = 0.0
    for item in line_items:
        qty = float(item.get("quantity", 1))
        price = float(item.get("unit_price", 0))
        amt = round(qty * price, 2)
        sku = item.get("sku_id")
        job = item.get("job_id")
        session.add(
            InvoiceLineItems(
                id=as_uuid_required(item.get("id") or new_uuid7_str()),
                invoice_id=iid,
                description=item.get("description", ""),
                quantity=qty,
                unit_price=price,
                amount=amt,
                cost=float(item.get("cost", 0)),
                sku_id=as_uuid(sku),
                job_id=as_uuid(job),
                unit=item.get("unit") or "each",
                sell_cost=float(item.get("sell_cost") or item.get("cost", 0)),
            )
        )
        subtotal += amt
    await session.flush()
    return subtotal


async def invoice_insert_line_items(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    line_items: list[dict],
) -> float:
    iid = await _ensure_invoice_org(session, org_id, invoice_id)
    subtotal = 0.0
    for item in line_items:
        qty = float(item.get("quantity", 1))
        price = float(item.get("unit_price") or item.get("price") or 0)
        amt = round(qty * price, 2)
        sku = item.get("sku_id")
        job = item.get("job_id")
        session.add(
            InvoiceLineItems(
                id=as_uuid_required(new_uuid7_str()),
                invoice_id=iid,
                description=item.get("description") or item.get("name", ""),
                quantity=qty,
                unit_price=price,
                amount=amt,
                cost=float(item.get("cost", 0)),
                sku_id=as_uuid(sku),
                job_id=as_uuid(job),
                unit=item.get("unit") or "each",
                sell_cost=float(item.get("sell_cost") or item.get("cost", 0)),
            )
        )
        subtotal += amt
    await session.flush()
    return subtotal


async def invoice_link_withdrawal(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    withdrawal_id: str,
) -> None:
    iid = await _ensure_invoice_org(session, org_id, invoice_id)
    wid = as_uuid_required(withdrawal_id)
    stmt = (
        pg_insert(InvoiceWithdrawals)
        .values(invoice_id=iid, withdrawal_id=wid)
        .on_conflict_do_nothing()
    )
    await session.execute(stmt)
    await session.flush()


async def invoice_unlink_withdrawals(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: str
) -> list[str]:
    iid = await _ensure_invoice_org(session, org_id, invoice_id)
    wr = await session.execute(
        select(InvoiceWithdrawals.withdrawal_id).where(
            InvoiceWithdrawals.invoice_id == iid
        )
    )
    wids = [str(x[0]) for x in wr.all()]
    await session.execute(
        delete(InvoiceWithdrawals).where(InvoiceWithdrawals.invoice_id == iid)
    )
    await session.flush()
    return wids


async def invoice_soft_delete(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: str
) -> None:
    iid = as_uuid_required(invoice_id)
    now = datetime.now(UTC)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(status="deleted", deleted_at=now, updated_at=now)
    )
    await session.flush()


async def invoice_insert_row(
    session: AsyncSession,
    org_id: uuid.UUID,
    inv_id: str,
    invoice_number: str,
    billing_entity: str,
    contact_name: str,
    contact_email: str,
    tax_rate: float,
    payment_terms: str,
    due_date: str,
    now: datetime,
) -> None:
    due = (
        datetime.fromisoformat(due_date)
        if isinstance(due_date, str)
        else due_date
    )
    row = Invoices(
        id=as_uuid_required(inv_id),
        invoice_number=invoice_number,
        billing_entity=billing_entity,
        contact_name=contact_name,
        contact_email=contact_email,
        status="draft",
        subtotal=0,
        tax=0,
        tax_rate=tax_rate,
        total=0,
        amount_credited=0,
        notes=None,
        invoice_date=now,
        due_date=due,
        payment_terms=payment_terms,
        billing_address="",
        po_reference="",
        currency="USD",
        approved_by_id=None,
        approved_at=None,
        xero_invoice_id=None,
        organization_id=org_id,
        created_at=now,
        updated_at=now,
        xero_sync_status="pending",
    )
    session.add(row)
    await session.flush()


async def invoice_mark_paid_for_withdrawal(
    session: AsyncSession, org_id: uuid.UUID, withdrawal_id: str
) -> None:
    wid = as_uuid_required(withdrawal_id)
    r = await session.execute(
        select(InvoiceWithdrawals.invoice_id).where(
            InvoiceWithdrawals.withdrawal_id == wid
        )
    )
    row = r.first()
    if not row or not row[0]:
        return
    inv_id = row[0]
    now = datetime.now(UTC)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == inv_id, Invoices.organization_id == org_id)
        .values(status="paid", updated_at=now)
    )
    await session.flush()


async def invoice_update_totals(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    subtotal: float,
    tax: float,
    total: float,
) -> None:
    iid = as_uuid_required(invoice_id)
    now = datetime.now(UTC)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(subtotal=subtotal, tax=tax, total=total, updated_at=now)
    )
    await session.flush()


async def invoice_update_billing(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    billing_entity: str,
    contact_name: str,
    updated_at: datetime,
) -> None:
    iid = as_uuid_required(invoice_id)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(
            billing_entity=billing_entity,
            contact_name=contact_name,
            updated_at=updated_at,
        )
    )
    await session.flush()


async def invoice_update_fields_dynamic(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    fields: dict[str, Any],
) -> None:
    if not fields:
        return
    iid = as_uuid_required(invoice_id)
    vals = {**fields, "updated_at": datetime.now(UTC)}
    cols = set(Invoices.__table__.columns.keys())
    safe = {k: v for k, v in vals.items() if k in cols and k != "id"}
    if not safe:
        return
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(**safe)
    )
    await session.flush()


async def invoice_set_xero_invoice_id(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    xero_invoice_id: str,
    xero_cogs_journal_id: str | None = None,
) -> None:
    iid = as_uuid_required(invoice_id)
    now = datetime.now(UTC)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(
            xero_invoice_id=xero_invoice_id,
            xero_cogs_journal_id=xero_cogs_journal_id,
            xero_sync_status="synced",
            updated_at=now,
        )
    )
    await session.flush()


async def invoice_set_xero_sync_status(
    session: AsyncSession,
    org_id: uuid.UUID,
    invoice_id: str,
    status: str,
) -> None:
    iid = as_uuid_required(invoice_id)
    now = datetime.now(UTC)
    await session.execute(
        update(Invoices)
        .where(Invoices.id == iid, Invoices.organization_id == org_id)
        .values(xero_sync_status=status, updated_at=now)
    )
    await session.flush()


def _row_to_invoice_partial(inv: Invoices) -> Invoice:
    d = _inv_row_to_domain(inv)
    return Invoice.model_validate(d)


async def invoice_list_unsynced(
    session: AsyncSession, org_id: uuid.UUID
) -> list[Invoice]:
    r = await session.execute(
        select(Invoices)
        .where(
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
            Invoices.status.in_(("approved", "sent")),
            or_(
                Invoices.xero_invoice_id.is_(None),
                Invoices.xero_sync_status == "syncing",
            ),
        )
        .order_by(Invoices.created_at)
    )
    return [_row_to_invoice_partial(x) for x in r.scalars().all()]


async def invoice_list_needing_reconciliation(
    session: AsyncSession, org_id: uuid.UUID
) -> list[Invoice]:
    r = await session.execute(
        select(Invoices)
        .where(
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
            Invoices.xero_invoice_id.is_not(None),
            Invoices.xero_sync_status != "mismatch",
        )
        .order_by(Invoices.created_at)
    )
    invs = r.scalars().all()
    if not invs:
        return []
    ids = [i.id for i in invs]
    cr = await session.execute(
        select(InvoiceLineItems.invoice_id, func.count())
        .where(InvoiceLineItems.invoice_id.in_(ids))
        .group_by(InvoiceLineItems.invoice_id)
    )
    count_map = {row[0]: int(row[1]) for row in cr.all()}
    out: list[Invoice] = []
    for inv in invs:
        d = _inv_row_to_domain(inv)
        d["line_count"] = count_map.get(inv.id, 0)
        out.append(Invoice.model_validate(d))
    return out


async def invoice_list_failed(
    session: AsyncSession, org_id: uuid.UUID
) -> list[Invoice]:
    r = await session.execute(
        select(Invoices)
        .where(
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
            Invoices.xero_sync_status == "failed",
        )
        .order_by(Invoices.created_at)
    )
    return [_row_to_invoice_partial(x) for x in r.scalars().all()]


async def invoice_list_mismatch(
    session: AsyncSession, org_id: uuid.UUID
) -> list[Invoice]:
    r = await session.execute(
        select(Invoices)
        .where(
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
            Invoices.xero_sync_status == "mismatch",
        )
        .order_by(Invoices.created_at)
    )
    return [_row_to_invoice_partial(x) for x in r.scalars().all()]


async def invoice_list_stale_cogs(
    session: AsyncSession, org_id: uuid.UUID
) -> list[Invoice]:
    r = await session.execute(
        select(Invoices)
        .where(
            Invoices.organization_id == org_id,
            Invoices.deleted_at.is_(None),
            Invoices.xero_sync_status == "cogs_stale",
            Invoices.xero_invoice_id.is_not(None),
        )
        .order_by(Invoices.created_at)
    )
    invs = r.scalars().all()
    if not invs:
        return []
    ids = [i.id for i in invs]
    cr = await session.execute(
        select(InvoiceLineItems.invoice_id, func.count())
        .where(InvoiceLineItems.invoice_id.in_(ids))
        .group_by(InvoiceLineItems.invoice_id)
    )
    count_map = {row[0]: int(row[1]) for row in cr.all()}
    out: list[Invoice] = []
    for inv in invs:
        d = _inv_row_to_domain(inv)
        d["line_count"] = count_map.get(inv.id, 0)
        out.append(Invoice.model_validate(d))
    return out
