"""Finance application queries — safe for API and cross-context import.

API routes and other bounded contexts import from here, never from
finance.infrastructure directly. Thin delegation layer that decouples
consumers from infrastructure details.
"""

from finance.domain.billing_entity import BillingEntity
from finance.domain.credit_note import CreditNote
from finance.domain.invoice import Invoice
from finance.domain.payment import Payment
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _finance():
    return get_database_manager().finance


# ── Billing entity queries ───────────────────────────────────────────────────


async def get_billing_entity_by_id(entity_id: str) -> BillingEntity | None:
    return await _finance().billing_entity_get_by_id(get_org_id(), entity_id)


async def list_billing_entities(
    is_active: bool | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list:
    return await _finance().billing_entity_list(
        get_org_id(),
        is_active=is_active,
        q=q,
        limit=limit,
        offset=offset,
    )


async def search_billing_entities(query: str, limit: int = 20) -> list:
    return await _finance().billing_entity_search(
        get_org_id(), query, limit=limit
    )


# ── Payment queries ──────────────────────────────────────────────────────────


async def list_payments(
    invoice_id: str | None = None,
    billing_entity_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Payment]:
    return await _finance().payment_list(
        get_org_id(),
        invoice_id=invoice_id,
        billing_entity_id=billing_entity_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


async def get_payment_by_id(payment_id: str) -> Payment | None:
    return await _finance().payment_get_by_id(get_org_id(), payment_id)


# ── Credit note queries ─────────────────────────────────────────────────────


async def list_credit_notes(
    invoice_id: str | None = None,
    billing_entity: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[CreditNote]:
    return await _finance().credit_note_list(
        get_org_id(),
        invoice_id=invoice_id,
        billing_entity=billing_entity,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )


async def get_credit_note_by_id(credit_note_id: str) -> CreditNote | None:
    return await _finance().credit_note_get_by_id(get_org_id(), credit_note_id)


async def list_unsynced_credit_notes() -> list[CreditNote]:
    return await _finance().credit_note_list_unsynced(get_org_id())


async def list_mismatch_credit_notes() -> list[CreditNote]:
    return await _finance().credit_note_list_mismatch(get_org_id())


async def list_failed_credit_notes() -> list[CreditNote]:
    return await _finance().credit_note_list_failed(get_org_id())


# ── Invoice queries (Xero health) ────────────────────────────────────────────


async def list_unsynced_invoices() -> list[Invoice]:
    return await _finance().invoice_list_unsynced(get_org_id())


async def list_mismatch_invoices() -> list[Invoice]:
    return await _finance().invoice_list_mismatch(get_org_id())


async def list_failed_invoices() -> list[Invoice]:
    return await _finance().invoice_list_failed(get_org_id())
