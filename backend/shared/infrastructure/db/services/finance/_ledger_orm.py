"""Financial ledger writes and journal reads via SQLModel (Phase 3)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.types.public_sql_model_models import FinancialLedger
from shared.kernel.types import round_money

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from finance.domain.ledger import FinancialEntry


def _financial_entry_to_row(e: FinancialEntry, org_id: uuid.UUID) -> FinancialLedger:
    jid = as_uuid_required(e.journal_id) if e.journal_id else None
    job = as_uuid_required(e.job_id) if e.job_id else None
    contractor = as_uuid_required(e.contractor_id) if e.contractor_id else None
    sku = as_uuid_required(e.sku_id) if e.sku_id else None
    perf = as_uuid_required(e.performed_by_user_id) if e.performed_by_user_id else None
    return FinancialLedger(
        id=as_uuid_required(e.id),
        journal_id=jid,
        account=e.account.value,
        amount=round_money(e.amount),
        quantity=e.quantity,
        unit=e.unit,
        unit_cost=e.unit_cost,
        department=e.department,
        job_id=job,
        billing_entity=e.billing_entity,
        billing_entity_id=None,
        contractor_id=contractor,
        vendor_name=e.vendor_name,
        sku_id=sku,
        performed_by_user_id=perf,
        reference_type=e.reference_type.value,
        reference_id=e.reference_id,
        organization_id=org_id,
        created_at=e.created_at,
    )


async def ledger_entries_exist_for_reference(
    session: AsyncSession,
    org_id: uuid.UUID,
    reference_type: str,
    reference_id: str,
) -> bool:
    result = await session.execute(
        select(FinancialLedger.id)
        .where(
            FinancialLedger.reference_type == reference_type,
            FinancialLedger.reference_id == reference_id,
            FinancialLedger.organization_id == org_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def ledger_insert_entries_in_session(
    session: AsyncSession,
    org_id: uuid.UUID,
    entries: list[FinancialEntry],
) -> None:
    for e in entries:
        session.add(_financial_entry_to_row(e, org_id))


async def ledger_get_journal_rows(
    session: AsyncSession,
    org_id: uuid.UUID,
    journal_id: str,
) -> list[dict[str, Any]]:
    jid = as_uuid_required(journal_id)
    result = await session.execute(
        select(FinancialLedger)
        .where(
            FinancialLedger.journal_id == jid,
            FinancialLedger.organization_id == org_id,
        )
        .order_by(FinancialLedger.id)
    )
    rows = result.scalars().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = r.model_dump(mode="python")
        for k, v in list(d.items()):
            if isinstance(v, uuid.UUID):
                d[k] = str(v)
        out.append(d)
    return out
