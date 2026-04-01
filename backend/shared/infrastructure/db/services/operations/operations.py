"""Operations context persistence via SQLModel (withdrawals, MRs, returns, contractors)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import case, cast, func, select, update
from sqlalchemy.types import Numeric

from operations.domain.enums import MaterialRequestStatus, PaymentStatus
from operations.domain.material_request import MaterialRequest
from operations.domain.returns import MaterialReturn
from operations.domain.withdrawal import MaterialWithdrawal
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services.operations._helpers import (
    build_material_request_item_row,
    build_material_request_row,
    build_return_item_row,
    build_return_row,
    build_withdrawal_item_row,
    build_withdrawal_row,
    hydrate_material_request,
    hydrate_material_requests,
    hydrate_return,
    hydrate_returns,
    hydrate_withdrawal,
    hydrate_withdrawals,
)
from shared.infrastructure.logging_config import org_id_var
from shared.infrastructure.types.public_sql_model_models import (
    MaterialRequests,
    Returns,
    WithdrawalItems,
    Withdrawals,
)
from shared.kernel.errors import InvalidTransitionError


@asynccontextmanager
async def _scoped_org(org_id: str) -> AsyncIterator[None]:
    token = org_id_var.set(org_id)
    try:
        yield None
    finally:
        org_id_var.reset(token)


class OperationsDatabaseService(DomainDatabaseService):
    # --- Withdrawals ---------------------------------------------------------

    async def insert_withdrawal(
        self, org_id: str, withdrawal: MaterialWithdrawal
    ) -> None:
        oid = as_uuid_required(org_id)
        withdrawal.organization_id = org_id
        parent_row = build_withdrawal_row(withdrawal, oid)
        async with self.session() as session:
            session.add(parent_row)
            for item in withdrawal.items:
                session.add(
                    build_withdrawal_item_row(parent_row.id, item),
                )
            await self.end_write_session(session)

    async def list_withdrawals(
        self,
        org_id: str,
        *,
        contractor_id: str | None = None,
        payment_status: str | None = None,
        billing_entity: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 10000,
        offset: int = 0,
    ) -> list[MaterialWithdrawal]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(Withdrawals).where(Withdrawals.organization_id == oid)
            if contractor_id:
                stmt = stmt.where(
                    Withdrawals.contractor_id == as_uuid_required(contractor_id)
                )
            if payment_status:
                stmt = stmt.where(Withdrawals.payment_status == payment_status)
            if billing_entity:
                stmt = stmt.where(Withdrawals.billing_entity == billing_entity)
            if start_date:
                stmt = stmt.where(Withdrawals.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Withdrawals.created_at <= end_date)
            stmt = (
                stmt.order_by(Withdrawals.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
            return await hydrate_withdrawals(session, rows)

    async def get_withdrawal_by_id(
        self, org_id: str, withdrawal_id: str
    ) -> MaterialWithdrawal | None:
        oid = as_uuid_required(org_id)
        wid = as_uuid_required(withdrawal_id)
        async with self.session() as session:
            result = await session.execute(
                select(Withdrawals).where(
                    Withdrawals.id == wid,
                    Withdrawals.organization_id == oid,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return await hydrate_withdrawal(session, row)

    async def mark_withdrawal_paid(
        self, org_id: str, withdrawal_id: str, paid_at: datetime
    ) -> tuple[MaterialWithdrawal | None, bool]:
        oid = as_uuid_required(org_id)
        wid = as_uuid_required(withdrawal_id)
        paid_s = str(PaymentStatus.PAID)
        async with self.session() as session:
            res = await session.execute(
                update(Withdrawals)
                .where(
                    Withdrawals.id == wid,
                    Withdrawals.payment_status != paid_s,
                    Withdrawals.organization_id == oid,
                )
                .values(
                    payment_status=paid_s,
                    paid_at=paid_at,
                )
            )
            changed = res.rowcount > 0
            await self.end_write_session(session)
        updated = await self.get_withdrawal_by_id(org_id, withdrawal_id)
        return updated, changed

    async def bulk_mark_withdrawals_paid(
        self, org_id: str, withdrawal_ids: list[str], paid_at: datetime
    ) -> list[str]:
        if not withdrawal_ids:
            return []
        oid = as_uuid_required(org_id)
        uuids = [as_uuid_required(i) for i in withdrawal_ids]
        paid_s = str(PaymentStatus.PAID)
        async with self.session() as session:
            stmt = (
                update(Withdrawals)
                .where(
                    Withdrawals.id.in_(uuids),
                    Withdrawals.payment_status != paid_s,
                    Withdrawals.organization_id == oid,
                )
                .values(payment_status=paid_s, paid_at=paid_at)
                .returning(Withdrawals.id)
            )
            result = await session.execute(stmt)
            ids = [str(r[0]) for r in result.all()]
            await self.end_write_session(session)
            return ids

    async def link_withdrawal_to_invoice(
        self, org_id: str, withdrawal_id: str, invoice_id: str
    ) -> bool:
        oid = as_uuid_required(org_id)
        wid = as_uuid_required(withdrawal_id)
        iid = as_uuid_required(invoice_id)
        text_invoiced = str(PaymentStatus.INVOICED)
        text_unpaid = str(PaymentStatus.UNPAID)
        async with self.session() as session:
            res = await session.execute(
                update(Withdrawals)
                .where(
                    Withdrawals.id == wid,
                    Withdrawals.invoice_id.is_(None),
                    Withdrawals.payment_status == text_unpaid,
                    Withdrawals.organization_id == oid,
                )
                .values(invoice_id=iid, payment_status=text_invoiced)
            )
            n = res.rowcount
            await self.end_write_session(session)
            return n > 0

    async def unlink_withdrawals_from_invoice(
        self, org_id: str, withdrawal_ids: list[str]
    ) -> None:
        if not withdrawal_ids:
            return
        oid = as_uuid_required(org_id)
        uuids = [as_uuid_required(i) for i in withdrawal_ids]
        text_unpaid = str(PaymentStatus.UNPAID)
        async with self.session() as session:
            await session.execute(
                update(Withdrawals)
                .where(
                    Withdrawals.id.in_(uuids),
                    Withdrawals.organization_id == oid,
                )
                .values(invoice_id=None, payment_status=text_unpaid)
            )
            await self.end_write_session(session)

    async def mark_withdrawals_paid_by_invoice(
        self, org_id: str, invoice_id: str, paid_at: datetime
    ) -> None:
        oid = as_uuid_required(org_id)
        iid = as_uuid_required(invoice_id)
        text_paid = str(PaymentStatus.PAID)
        async with self.session() as session:
            await session.execute(
                update(Withdrawals)
                .where(
                    Withdrawals.invoice_id == iid,
                    Withdrawals.organization_id == oid,
                )
                .values(payment_status=text_paid, paid_at=paid_at)
            )
            await self.end_write_session(session)

    async def units_sold_by_product(
        self,
        org_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, float]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = (
                select(
                    WithdrawalItems.sku_id, func.sum(WithdrawalItems.quantity)
                )
                .join(
                    Withdrawals, WithdrawalItems.withdrawal_id == Withdrawals.id
                )
                .where(Withdrawals.organization_id == oid)
                .group_by(WithdrawalItems.sku_id)
            )
            if start_date:
                stmt = stmt.where(Withdrawals.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Withdrawals.created_at <= end_date)
            result = await session.execute(stmt)
            return {str(row[0]): float(row[1]) for row in result.all()}

    async def payment_status_breakdown(
        self,
        org_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, float]:
        oid = as_uuid_required(org_id)
        paid_s = str(PaymentStatus.PAID)
        status_label = case(
            (Withdrawals.payment_status == paid_s, "Paid"),
            (Withdrawals.invoice_id.isnot(None), "Invoiced"),
            else_="Unpaid",
        )
        async with self.session() as session:
            stmt = (
                select(
                    status_label,
                    func.round(
                        cast(func.sum(Withdrawals.total), Numeric),
                        2,
                    ),
                )
                .where(Withdrawals.organization_id == oid)
                .group_by(status_label)
            )
            if start_date:
                stmt = stmt.where(Withdrawals.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Withdrawals.created_at <= end_date)
            result = await session.execute(stmt)
            return {row[0]: float(row[1]) for row in result.all()}

    # --- Material requests ---------------------------------------------------

    async def insert_material_request(
        self, org_id: str, request: MaterialRequest
    ) -> None:
        oid = as_uuid_required(org_id)
        parent = build_material_request_row(request, oid)
        async with self.session() as session:
            session.add(parent)
            for item in request.items:
                session.add(build_material_request_item_row(parent.id, item))
            await self.end_write_session(session)

    async def get_material_request_by_id(
        self, org_id: str, request_id: str
    ) -> MaterialRequest | None:
        oid = as_uuid_required(org_id)
        rid = as_uuid_required(request_id)
        async with self.session() as session:
            result = await session.execute(
                select(MaterialRequests).where(
                    MaterialRequests.id == rid,
                    MaterialRequests.organization_id == oid,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return await hydrate_material_request(session, row)

    async def list_pending_material_requests(
        self, org_id: str, *, limit: int = 100
    ) -> list[MaterialRequest]:
        oid = as_uuid_required(org_id)
        pending = str(MaterialRequestStatus.PENDING)
        async with self.session() as session:
            result = await session.execute(
                select(MaterialRequests)
                .where(
                    MaterialRequests.status == pending,
                    MaterialRequests.organization_id == oid,
                )
                .order_by(MaterialRequests.created_at.desc())
                .limit(limit)
            )
            rows = list(result.scalars().all())
            return await hydrate_material_requests(session, rows)

    async def list_material_requests_by_contractor(
        self, org_id: str, contractor_id: str, *, limit: int = 100
    ) -> list[MaterialRequest]:
        oid = as_uuid_required(org_id)
        cid = as_uuid_required(contractor_id)
        async with self.session() as session:
            result = await session.execute(
                select(MaterialRequests)
                .where(
                    MaterialRequests.contractor_id == cid,
                    MaterialRequests.organization_id == oid,
                )
                .order_by(MaterialRequests.created_at.desc())
                .limit(limit)
            )
            rows = list(result.scalars().all())
            return await hydrate_material_requests(session, rows)

    async def mark_material_request_processed(
        self,
        org_id: str,
        request_id: str,
        withdrawal_id: str,
        processed_by_id: str,
        processed_at: datetime,
    ) -> bool:
        oid = as_uuid_required(org_id)
        rid = as_uuid_required(request_id)
        wid = as_uuid_required(withdrawal_id)
        pid = as_uuid_required(processed_by_id)
        pending = str(MaterialRequestStatus.PENDING)
        done = str(MaterialRequestStatus.PROCESSED)
        async with self.session() as session:
            res = await session.execute(
                update(MaterialRequests)
                .where(
                    MaterialRequests.id == rid,
                    MaterialRequests.status == pending,
                    MaterialRequests.organization_id == oid,
                )
                .values(
                    status=done,
                    withdrawal_id=wid,
                    processed_by_id=pid,
                    processed_at=processed_at,
                )
            )
            if res.rowcount == 0:
                raise InvalidTransitionError(
                    "MaterialRequest", "processed", "processed"
                )
            await self.end_write_session(session)
            return True

    # --- Returns -------------------------------------------------------------

    async def insert_return(self, org_id: str, ret: MaterialReturn) -> None:
        oid = as_uuid_required(org_id)
        row = build_return_row(ret, oid)
        async with self.session() as session:
            session.add(row)
            for item in ret.items:
                session.add(build_return_item_row(row.id, item))
            await self.end_write_session(session)

    async def get_return_by_id(
        self, org_id: str, return_id: str
    ) -> MaterialReturn | None:
        oid = as_uuid_required(org_id)
        rid = as_uuid_required(return_id)
        async with self.session() as session:
            result = await session.execute(
                select(Returns).where(
                    Returns.id == rid,
                    Returns.organization_id == oid,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return await hydrate_return(session, row)

    async def list_returns(
        self,
        org_id: str,
        *,
        contractor_id: str | None = None,
        withdrawal_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 500,
    ) -> list[MaterialReturn]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(Returns).where(Returns.organization_id == oid)
            if contractor_id:
                stmt = stmt.where(
                    Returns.contractor_id == as_uuid_required(contractor_id)
                )
            if withdrawal_id:
                stmt = stmt.where(
                    Returns.withdrawal_id == as_uuid_required(withdrawal_id)
                )
            if start_date:
                stmt = stmt.where(Returns.created_at >= start_date)
            if end_date:
                stmt = stmt.where(Returns.created_at <= end_date)
            stmt = stmt.order_by(Returns.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
            return await hydrate_returns(session, rows)

    async def list_returns_by_withdrawal(
        self, org_id: str, withdrawal_id: str
    ) -> list[MaterialReturn]:
        oid = as_uuid_required(org_id)
        wid = as_uuid_required(withdrawal_id)
        async with self.session() as session:
            result = await session.execute(
                select(Returns)
                .where(
                    Returns.withdrawal_id == wid,
                    Returns.organization_id == oid,
                )
                .order_by(Returns.created_at.desc())
            )
            rows = list(result.scalars().all())
            return await hydrate_returns(session, rows)

    async def link_return_credit_note(
        self, org_id: str, return_id: str, credit_note_id: str
    ) -> None:
        oid = as_uuid_required(org_id)
        rid = as_uuid_required(return_id)
        cid = as_uuid_required(credit_note_id)
        async with self.session() as session:
            await session.execute(
                update(Returns)
                .where(Returns.id == rid, Returns.organization_id == oid)
                .values(credit_note_id=cid)
            )
            await self.end_write_session(session)

    # --- Contractors (application service still owns business rules) --------

    async def get_contractor_by_id(self, org_id: str, user_id: str):
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.get_contractor_by_id(user_id)

    async def get_contractors_by_ids(self, org_id: str, user_ids: list[str]):
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.get_users_by_ids(user_ids)

    async def list_contractors(self, org_id: str, search: str | None = None):
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.list_contractors(search=search)

    async def count_contractors(self, org_id: str) -> int:
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.count_contractors()

    async def create_contractor(
        self,
        org_id: str,
        email: str,
        password: str,
        name: str,
        company: str | None = None,
        billing_entity_name: str | None = None,
        phone: str | None = None,
    ):
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.create_contractor(
                email,
                password,
                name,
                company=company,
                billing_entity_name=billing_entity_name,
                phone=phone,
            )

    async def update_contractor(self, org_id: str, contractor_id: str, updates):
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.update_contractor(
                contractor_id, updates
            )

    async def delete_contractor(self, org_id: str, contractor_id: str) -> int:
        from operations.application import contractor_service

        async with _scoped_org(org_id):
            return await contractor_service.delete_contractor(contractor_id)
