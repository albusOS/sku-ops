"""Invoice application services — orchestration for invoice lifecycle."""

from datetime import UTC, datetime
from typing import Any

from finance.domain.enums import InvoiceStatus, XeroSyncStatus
from finance.domain.invoice import (
    InvoiceLineItem,
    InvoiceWithDetails,
    compute_due_date,
)
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import (
    InvoiceApproved,
    InvoiceCreated,
    InvoiceDeleted,
)

__all__ = [
    "add_withdrawals_to_invoice",
    "approve_invoice",
    "create_invoice_from_withdrawals",
    "delete_draft_invoice",
    "get_invoice",
    "list_invoices",
    "mark_paid_for_withdrawal",
    "update_invoice",
]


def _db_finance():
    return get_database_manager().finance


def _db_operations():
    return get_database_manager().operations


# ---------------------------------------------------------------------------
# Read queries
# ---------------------------------------------------------------------------


async def list_invoices(**kwargs):
    org_id = get_org_id()
    kwargs.pop("organization_id", None)
    return await _db_finance().invoice_list(org_id, **kwargs)


async def get_invoice(invoice_id: str) -> InvoiceWithDetails | None:
    return await _db_finance().invoice_get_by_id(get_org_id(), invoice_id)


async def mark_paid_for_withdrawal(withdrawal_id: str) -> None:
    await _db_finance().invoice_mark_paid_for_withdrawal(get_org_id(), withdrawal_id)


# ---------------------------------------------------------------------------
# Invoice creation from withdrawals — typed model flow
# ---------------------------------------------------------------------------


async def _validate_withdrawals_for_invoice(
    org_id: str,
    withdrawal_ids: list[str],
):
    """Fetch and validate withdrawals. Returns (withdrawals, billing_entity, contact_name)."""
    billing_entity: str | None = None
    contact_name = ""
    withdrawals: list[dict] = []

    for wid in withdrawal_ids:
        w = await _db_operations().get_withdrawal_by_id(org_id, wid)
        if not w:
            raise ValueError(f"Withdrawal {wid} not found")
        if w.payment_status != "unpaid":
            raise ValueError(f"Withdrawal {wid} is not unpaid")
        if w.invoice_id:
            raise ValueError(f"Withdrawal {wid} is already on invoice")
        be = w.billing_entity or ""
        if billing_entity is not None and be != billing_entity:
            raise ValueError("All withdrawals must share the same billing_entity")
        billing_entity = be
        contact_name = w.contractor_name or w.contractor_company or ""
        withdrawals.append(w)

    return withdrawals, billing_entity or "", contact_name


def _build_line_items_from_withdrawal(w, inv_id: str) -> list[dict]:
    """Convert typed WithdrawalItems to dicts for persistence."""
    items = []
    for item in w.items:
        line = InvoiceLineItem.from_line_item(item, invoice_id=inv_id, job_id=w.job_id)
        items.append(
            {
                "name": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "cost": line.cost,
                "sku_id": line.sku_id,
                "job_id": line.job_id,
                "unit": item.unit or "each",
                "sell_cost": float(item.sell_cost or item.cost),
            }
        )
    return items


async def create_invoice_from_withdrawals(
    withdrawal_ids: list[str],
) -> InvoiceWithDetails:
    """Create new invoice from unpaid withdrawals. All must share same billing_entity."""
    if not withdrawal_ids:
        raise ValueError("At least one withdrawal required")

    org_id = get_org_id()
    fin = _db_finance()
    (
        withdrawals,
        billing_entity,
        contact_name,
    ) = await _validate_withdrawals_for_invoice(org_id, withdrawal_ids)

    inv_id = new_uuid7_str()
    now = datetime.now(UTC)
    payment_terms = "net_30"
    due_date = compute_due_date(now, payment_terms)
    first_tax_rate = withdrawals[0].tax_rate if withdrawals else 0

    async with transaction():
        invoice_number = await fin.invoice_next_number(org_id)

        await fin.invoice_insert_row(
            org_id,
            {
                "inv_id": inv_id,
                "invoice_number": invoice_number,
                "billing_entity": billing_entity,
                "contact_name": contact_name,
                "contact_email": "",
                "tax_rate": first_tax_rate,
                "payment_terms": payment_terms,
                "due_date": due_date,
                "now": now,
            },
        )

        total_subtotal = 0.0
        total_tax = 0.0
        for w in withdrawals:
            items = _build_line_items_from_withdrawal(w, inv_id)
            subtotal = await fin.invoice_insert_line_items(org_id, inv_id, items)
            total_subtotal += subtotal
            total_tax += w.tax

        total = round(total_subtotal + total_tax, 2)
        await fin.invoice_update_totals(org_id, inv_id, total_subtotal, total_tax, total)

        for wid in withdrawal_ids:
            await fin.invoice_link_withdrawal(org_id, inv_id, wid)
            linked = await _db_operations().link_withdrawal_to_invoice(org_id, wid, inv_id)
            if not linked:
                raise ValueError(f"Withdrawal {wid} was already linked to another invoice")

    await dispatch(
        InvoiceCreated(
            org_id=org_id,
            invoice_id=inv_id,
            withdrawal_ids=tuple(withdrawal_ids),
        )
    )
    out = await fin.invoice_get_by_id(org_id, inv_id)
    if not out:
        raise RuntimeError(f"Invoice {inv_id} missing after create")
    return out


async def add_withdrawals_to_invoice(
    invoice_id: str,
    withdrawal_ids: list[str],
) -> InvoiceWithDetails | None:
    """Link additional withdrawals to an existing invoice."""
    org_id = get_org_id()
    fin = _db_finance()
    if not withdrawal_ids:
        return await fin.invoice_get_by_id(org_id, invoice_id)

    (
        withdrawals,
        billing_entity,
        contact_name,
    ) = await _validate_withdrawals_for_invoice(org_id, withdrawal_ids)

    inv = await fin.invoice_get_by_id(org_id, invoice_id)
    if not inv:
        return None

    if inv.billing_entity and inv.billing_entity != billing_entity:
        raise ValueError("Invoice billing_entity does not match withdrawals")

    async with transaction():
        if not inv.billing_entity and billing_entity:
            await fin.invoice_update_billing(
                org_id,
                invoice_id,
                {
                    "billing_entity": billing_entity,
                    "contact_name": contact_name or inv.contact_name,
                    "updated_at": datetime.now(UTC),
                },
            )

        total_subtotal = 0.0
        total_tax = 0.0
        for w in withdrawals:
            items = _build_line_items_from_withdrawal(w, invoice_id)
            subtotal = await fin.invoice_insert_line_items(org_id, invoice_id, items)
            total_subtotal += subtotal
            total_tax += w.tax

        total = round(total_subtotal + total_tax, 2)
        await fin.invoice_update_totals(org_id, invoice_id, total_subtotal, total_tax, total)

        for wid in withdrawal_ids:
            await fin.invoice_link_withdrawal(org_id, invoice_id, wid)
            linked = await _db_operations().link_withdrawal_to_invoice(org_id, wid, invoice_id)
            if not linked:
                raise ValueError(f"Withdrawal {wid} was already linked to another invoice")

    return await fin.invoice_get_by_id(org_id, invoice_id)


async def update_invoice(
    invoice_id: str,
    billing_entity: str | None = None,
    contact_name: str | None = None,
    contact_email: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    tax: float | None = None,
    tax_rate: float | None = None,
    invoice_date: str | None = None,
    due_date: str | None = None,
    payment_terms: str | None = None,
    billing_address: str | None = None,
    po_reference: str | None = None,
    line_items: list[InvoiceLineItem] | None = None,
) -> InvoiceWithDetails | None:
    """Update invoice fields and/or replace line items."""
    org_id = get_org_id()
    fin = _db_finance()
    inv = await fin.invoice_get_by_id(org_id, invoice_id)
    if not inv:
        return None

    async with transaction():
        if line_items is not None:
            subtotal = await fin.invoice_replace_line_items(
                org_id,
                invoice_id,
                [i.model_dump() if hasattr(i, "model_dump") else i for i in line_items],
            )
            tax_val = tax if tax is not None else float(inv.tax)
            total = round(subtotal + tax_val, 2)
            sync_fields: dict[str, Any] = {
                "subtotal": subtotal,
                "tax": tax_val,
                "total": total,
            }
            if inv.xero_invoice_id:
                sync_fields["xero_sync_status"] = XeroSyncStatus.COGS_STALE
            await fin.invoice_update_fields_dynamic(org_id, invoice_id, sync_fields)
        else:
            updates: dict[str, Any] = {}
            if billing_entity is not None:
                updates["billing_entity"] = billing_entity
            if contact_name is not None:
                updates["contact_name"] = contact_name
            if contact_email is not None:
                updates["contact_email"] = contact_email
            if status is not None:
                updates["status"] = status
            if notes is not None:
                updates["notes"] = notes
            if tax is not None:
                inv_subtotal = float(inv.subtotal)
                updates["tax"] = tax
                updates["total"] = round(inv_subtotal + tax, 2)
            if tax_rate is not None:
                updates["tax_rate"] = tax_rate
            if invoice_date is not None:
                updates["invoice_date"] = invoice_date
            if due_date is not None:
                updates["due_date"] = due_date
            elif payment_terms is not None:
                inv_date = invoice_date or inv.invoice_date or inv.created_at
                updates["due_date"] = compute_due_date(inv_date, payment_terms)
            if payment_terms is not None:
                updates["payment_terms"] = payment_terms
            if billing_address is not None:
                updates["billing_address"] = billing_address
            if po_reference is not None:
                updates["po_reference"] = po_reference
            await fin.invoice_update_fields_dynamic(org_id, invoice_id, updates)

    return await fin.invoice_get_by_id(org_id, invoice_id)


async def approve_invoice(invoice_id: str, approved_by_id: str) -> InvoiceWithDetails | None:
    """Approve a draft invoice, locking it for Xero sync."""
    org_id = get_org_id()
    fin = _db_finance()
    inv = await fin.invoice_get_by_id(org_id, invoice_id)
    if not inv:
        return None
    if not inv.can_transition_to(InvoiceStatus.APPROVED):
        raise ValueError(f"Cannot approve invoice in '{inv.status}' status")

    now = datetime.now(UTC)
    async with transaction():
        result = await fin.invoice_update_fields(
            org_id,
            invoice_id,
            {
                "status": InvoiceStatus.APPROVED,
                "approved_by_id": approved_by_id,
                "approved_at": now,
            },
        )
    await dispatch(InvoiceApproved(org_id=org_id, invoice_id=invoice_id))
    return result


async def delete_draft_invoice(
    invoice_id: str,
) -> bool:
    """Soft-delete draft invoice and unlink withdrawals."""
    org_id = get_org_id()
    fin = _db_finance()
    inv = await fin.invoice_get_by_id(org_id, invoice_id)
    if not inv:
        return False
    if inv.status != InvoiceStatus.DRAFT:
        raise ValueError("Can only delete draft invoices")

    async with transaction():
        wids = await fin.invoice_unlink_withdrawals(org_id, invoice_id)
        await _db_operations().unlink_withdrawals_from_invoice(org_id, wids)
        await fin.invoice_soft_delete(org_id, invoice_id)

    await dispatch(
        InvoiceDeleted(
            org_id=org_id,
            invoice_id=invoice_id,
            withdrawal_ids=tuple(wids),
        )
    )
    return True
