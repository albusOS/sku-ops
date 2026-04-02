"""Billing entities, payments, fiscal periods, org settings, OAuth (ORM, Phase 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from finance.domain.billing_entity import BillingEntity
from finance.domain.fiscal_period import FiscalPeriod
from finance.domain.org_settings import OrgSettings as OrgSettingsDomain
from finance.domain.payment import Payment
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services.finance._helpers import uuids_to_str
from shared.infrastructure.types.public_sql_model_models import (
    BillingEntities,
    FiscalPeriods,
    OauthStates,
    OrgSettings,
    Payments,
    PaymentWithdrawals,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _be_row(row: BillingEntities | None) -> BillingEntity | None:
    if row is None:
        return None
    d = uuids_to_str(row.model_dump(mode="python"))
    if "is_active" in d and not isinstance(d["is_active"], bool):
        d["is_active"] = bool(d["is_active"])
    return BillingEntity.model_validate(d)


async def billing_entity_insert(
    session: AsyncSession, org_id: uuid.UUID, entity: BillingEntity
) -> None:
    d = entity.model_dump()
    session.add(
        BillingEntities(
            id=as_uuid_required(d["id"]),
            name=d["name"],
            contact_name=d.get("contact_name", ""),
            contact_email=d.get("contact_email", ""),
            billing_address=d.get("billing_address", ""),
            payment_terms=d.get("payment_terms", "net_30"),
            xero_contact_id=d.get("xero_contact_id"),
            is_active=bool(d.get("is_active", True)),
            organization_id=org_id,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
    )
    await session.flush()


async def billing_entity_get_by_id(
    session: AsyncSession, org_id: uuid.UUID, entity_id: str
) -> BillingEntity | None:
    eid = as_uuid_required(entity_id)
    r = await session.execute(
        select(BillingEntities).where(
            BillingEntities.id == eid,
            BillingEntities.organization_id == org_id,
        )
    )
    return _be_row(r.scalar_one_or_none())


async def billing_entity_get_by_name(
    session: AsyncSession, org_id: uuid.UUID, name: str
) -> BillingEntity | None:
    nm = name.strip().lower()
    r = await session.execute(
        select(BillingEntities).where(
            BillingEntities.organization_id == org_id,
            func.lower(func.trim(BillingEntities.name)) == nm,
        )
    )
    return _be_row(r.scalar_one_or_none())


async def billing_entity_list(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    is_active: bool | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[BillingEntity]:
    conds = [BillingEntities.organization_id == org_id]
    if is_active is not None:
        conds.append(BillingEntities.is_active == is_active)
    if q:
        like = f"%{q.lower()}%"
        conds.append(
            or_(
                func.lower(BillingEntities.name).like(like),
                func.lower(BillingEntities.contact_name).like(like),
            )
        )
    r = await session.execute(
        select(BillingEntities)
        .where(and_(*conds))
        .order_by(BillingEntities.name)
        .limit(limit)
        .offset(offset)
    )
    rows = r.scalars().all()
    return [x for row in rows if (x := _be_row(row)) is not None]


async def billing_entity_update(
    session: AsyncSession,
    org_id: uuid.UUID,
    entity_id: str,
    updates: dict[str, Any],
) -> BillingEntity | None:
    vals: dict[str, Any] = {}
    for key in (
        "name",
        "contact_name",
        "contact_email",
        "billing_address",
        "payment_terms",
        "xero_contact_id",
    ):
        if key in updates and updates[key] is not None:
            vals[key] = updates[key]
    if "is_active" in updates and updates["is_active"] is not None:
        vals["is_active"] = bool(updates["is_active"])
    if not vals:
        return await billing_entity_get_by_id(session, org_id, entity_id)
    vals["updated_at"] = datetime.now(UTC)
    eid = as_uuid_required(entity_id)
    await session.execute(
        update(BillingEntities)
        .where(
            BillingEntities.id == eid,
            BillingEntities.organization_id == org_id,
        )
        .values(**vals)
    )
    await session.flush()
    return await billing_entity_get_by_id(session, org_id, entity_id)


async def billing_entity_search(
    session: AsyncSession, org_id: uuid.UUID, query: str, limit: int = 20
) -> list[BillingEntity]:
    like = f"%{query.lower()}%"
    r = await session.execute(
        select(BillingEntities)
        .where(
            BillingEntities.organization_id == org_id,
            BillingEntities.is_active.is_(True),
            or_(
                func.lower(BillingEntities.name).like(like),
                func.lower(BillingEntities.contact_name).like(like),
            ),
        )
        .order_by(BillingEntities.name)
        .limit(limit)
    )
    rows = r.scalars().all()
    return [x for row in rows if (x := _be_row(row)) is not None]


async def billing_entity_ensure(
    session: AsyncSession, org_id: uuid.UUID, name: str
) -> BillingEntity | None:
    if not name or not name.strip():
        return None
    existing = await billing_entity_get_by_name(session, org_id, name)
    if existing:
        return existing
    entity = BillingEntity(name=name.strip(), organization_id=str(org_id))
    await billing_entity_insert(session, org_id, entity)
    return await billing_entity_get_by_name(session, org_id, name)


def _pay_row(row: Payments | None) -> Payment | None:
    if row is None:
        return None
    d = uuids_to_str(row.model_dump(mode="python"))
    return Payment.model_validate(d)


async def payment_insert(
    session: AsyncSession,
    org_id: uuid.UUID,
    payment: Payment,
    withdrawal_ids: list[str] | None = None,
) -> None:
    d = payment.model_dump()
    pid = as_uuid_required(d["id"])
    session.add(
        Payments(
            id=pid,
            invoice_id=as_uuid(d.get("invoice_id")),
            billing_entity_id=as_uuid(d.get("billing_entity_id")),
            amount=d["amount"],
            method=d.get("method", "bank_transfer"),
            reference=d.get("reference", ""),
            payment_date=d["payment_date"],
            notes=d.get("notes"),
            recorded_by_id=as_uuid_required(d["recorded_by_id"]),
            xero_payment_id=d.get("xero_payment_id"),
            organization_id=org_id,
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
    )
    for wid in withdrawal_ids or []:
        session.add(
            PaymentWithdrawals(
                payment_id=pid,
                withdrawal_id=as_uuid_required(wid),
            )
        )
    await session.flush()


# as_uuid for optional - import
from shared.infrastructure.db.orm_utils import as_uuid


async def payment_get_by_id(
    session: AsyncSession, org_id: uuid.UUID, payment_id: str
) -> Payment | None:
    pid = as_uuid_required(payment_id)
    r = await session.execute(
        select(Payments).where(
            Payments.id == pid,
            Payments.organization_id == org_id,
        )
    )
    row = r.scalar_one_or_none()
    p = _pay_row(row)
    if p:
        wr = await session.execute(
            select(PaymentWithdrawals.withdrawal_id).where(
                PaymentWithdrawals.payment_id == pid
            )
        )
        p.withdrawal_ids = [str(x[0]) for x in wr.all()]
    return p


async def payment_list(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    invoice_id: str | None = None,
    billing_entity_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[Payment]:
    conds = [Payments.organization_id == org_id]
    if invoice_id:
        conds.append(Payments.invoice_id == as_uuid_required(invoice_id))
    if billing_entity_id:
        conds.append(
            Payments.billing_entity_id == as_uuid_required(billing_entity_id)
        )
    if start_date:
        conds.append(
            Payments.payment_date >= datetime.fromisoformat(start_date)
        )
    if end_date:
        conds.append(Payments.payment_date <= datetime.fromisoformat(end_date))
    r = await session.execute(
        select(Payments)
        .where(and_(*conds))
        .order_by(Payments.payment_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_pay_row(x) for x in r.scalars().all() if _pay_row(x)]


async def payment_list_for_invoice(
    session: AsyncSession, org_id: uuid.UUID, invoice_id: str
) -> list[Payment]:
    iid = as_uuid_required(invoice_id)
    r = await session.execute(
        select(Payments)
        .where(
            Payments.invoice_id == iid,
            Payments.organization_id == org_id,
        )
        .order_by(Payments.payment_date.desc())
    )
    return [_pay_row(x) for x in r.scalars().all() if _pay_row(x)]


async def fiscal_get_period(
    session: AsyncSession, org_id: uuid.UUID, period_id: str
) -> FiscalPeriod | None:
    pid = as_uuid_required(period_id)
    r = await session.execute(
        select(FiscalPeriods).where(
            FiscalPeriods.id == pid,
            FiscalPeriods.organization_id == org_id,
        )
    )
    row = r.scalar_one_or_none()
    if not row:
        return None
    d = uuids_to_str(row.model_dump(mode="python"))
    return FiscalPeriod.model_validate(d)


async def fiscal_list_periods(
    session: AsyncSession, org_id: uuid.UUID, status: str | None = None
) -> list[FiscalPeriod]:
    conds = [FiscalPeriods.organization_id == org_id]
    if status:
        conds.append(FiscalPeriods.status == status)
    r = await session.execute(
        select(FiscalPeriods)
        .where(and_(*conds))
        .order_by(FiscalPeriods.start_date.desc())
    )
    return [
        FiscalPeriod.model_validate(uuids_to_str(x.model_dump(mode="python")))
        for x in r.scalars().all()
    ]


async def fiscal_insert_period(
    session: AsyncSession,
    org_id: uuid.UUID,
    period_id: str,
    name: str,
    start_date: str,
    end_date: str,
    created_at: datetime,
) -> None:
    sd = date.fromisoformat(start_date)
    if isinstance(start_date, str) and "T" not in start_date:
        sd = date.fromisoformat(start_date)
    else:
        sd = datetime.fromisoformat(start_date).date()
    ed = (
        date.fromisoformat(end_date)
        if isinstance(end_date, str) and "T" not in end_date
        else datetime.fromisoformat(end_date).date()
    )
    session.add(
        FiscalPeriods(
            id=as_uuid_required(period_id),
            name=name,
            start_date=sd,
            end_date=ed,
            status="open",
            organization_id=org_id,
            created_at=created_at,
        )
    )
    await session.flush()


async def fiscal_close_period(
    session: AsyncSession,
    org_id: uuid.UUID,
    period_id: str,
    closed_by_id: str,
    closed_at: str,
) -> None:
    pid = as_uuid_required(period_id)
    cat = (
        datetime.fromisoformat(closed_at)
        if isinstance(closed_at, str)
        else closed_at
    )
    await session.execute(
        update(FiscalPeriods)
        .where(
            FiscalPeriods.id == pid,
            FiscalPeriods.organization_id == org_id,
        )
        .values(
            status="closed",
            closed_by_id=as_uuid_required(closed_by_id),
            closed_at=cat,
        )
    )
    await session.flush()


async def fiscal_find_closed_covering(
    session: AsyncSession, org_id: uuid.UUID, entry_date: str | datetime
) -> tuple[str, str] | None:
    if isinstance(entry_date, str):
        ed = datetime.fromisoformat(entry_date)
    else:
        ed = entry_date
    ed_date = ed.date()
    r = await session.execute(
        select(FiscalPeriods.id, FiscalPeriods.name)
        .where(
            FiscalPeriods.organization_id == org_id,
            FiscalPeriods.status == "closed",
            FiscalPeriods.start_date <= ed_date,
            FiscalPeriods.end_date >= ed_date,
        )
        .limit(1)
    )
    row = r.first()
    if not row:
        return None
    return str(row[0]), str(row[1])


def _org_settings_domain_from_row(row: OrgSettings | None) -> OrgSettingsDomain:
    if row is None:
        raise ValueError("row required")
    d = uuids_to_str(row.model_dump(mode="python"))
    return OrgSettingsDomain.model_validate(d)


async def org_settings_get(
    session: AsyncSession, org_id: uuid.UUID
) -> OrgSettingsDomain:
    r = await session.execute(
        select(OrgSettings).where(OrgSettings.organization_id == org_id)
    )
    row = r.scalar_one_or_none()
    if row is None:
        return OrgSettingsDomain(organization_id=str(org_id))
    return _org_settings_domain_from_row(row)


async def org_settings_upsert(
    session: AsyncSession, org_id: uuid.UUID, settings: OrgSettingsDomain
) -> OrgSettingsDomain:
    now = datetime.now(UTC)
    s = settings
    stmt = (
        pg_insert(OrgSettings)
        .values(
            organization_id=org_id,
            auto_invoice=bool(s.auto_invoice),
            default_tax_rate=s.default_tax_rate,
            xero_tenant_id=s.xero_tenant_id,
            xero_access_token=s.xero_access_token,
            xero_refresh_token=s.xero_refresh_token,
            xero_token_expiry=s.xero_token_expiry.isoformat()
            if s.xero_token_expiry
            else None,
            xero_sales_account_code=s.xero_sales_account_code,
            xero_cogs_account_code=s.xero_cogs_account_code,
            xero_inventory_account_code=s.xero_inventory_account_code,
            xero_ap_account_code=s.xero_ap_account_code,
            xero_tracking_category_id=s.xero_tracking_category_id,
            xero_tax_type=s.xero_tax_type,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[OrgSettings.organization_id],
            set_={
                "auto_invoice": s.auto_invoice,
                "default_tax_rate": s.default_tax_rate,
                "xero_tenant_id": s.xero_tenant_id,
                "xero_access_token": s.xero_access_token,
                "xero_refresh_token": s.xero_refresh_token,
                "xero_token_expiry": s.xero_token_expiry.isoformat()
                if s.xero_token_expiry
                else None,
                "xero_sales_account_code": s.xero_sales_account_code,
                "xero_cogs_account_code": s.xero_cogs_account_code,
                "xero_inventory_account_code": s.xero_inventory_account_code,
                "xero_ap_account_code": s.xero_ap_account_code,
                "xero_tracking_category_id": s.xero_tracking_category_id,
                "xero_tax_type": s.xero_tax_type,
                "updated_at": now,
            },
        )
    )
    await session.execute(stmt)
    await session.flush()
    return await org_settings_get(session, org_id)


async def org_settings_clear_xero_tokens(
    session: AsyncSession, org_id: uuid.UUID
) -> None:
    now = datetime.now(UTC)
    await session.execute(
        update(OrgSettings)
        .where(OrgSettings.organization_id == org_id)
        .values(
            xero_access_token=None,
            xero_refresh_token=None,
            xero_tenant_id=None,
            xero_token_expiry=None,
            updated_at=now,
        )
    )
    await session.flush()


async def oauth_save_state(
    session: AsyncSession, org_id: uuid.UUID, state: str
) -> None:
    now = datetime.now(UTC)
    stmt = (
        pg_insert(OauthStates)
        .values(state=state, org_id=org_id, created_at=now)
        .on_conflict_do_update(
            index_elements=[OauthStates.state],
            set_={"org_id": org_id, "created_at": now},
        )
    )
    await session.execute(stmt)
    await session.flush()


async def oauth_pop_state(session: AsyncSession, state: str) -> str | None:
    r = await session.execute(
        select(OauthStates.org_id).where(OauthStates.state == state)
    )
    row = r.first()
    if not row:
        return None
    oid = row[0]
    await session.execute(delete(OauthStates).where(OauthStates.state == state))
    await session.flush()
    return str(oid)


from sqlalchemy import delete
