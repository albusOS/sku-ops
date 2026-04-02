"""Finance persistence and ledger queries. Explicit ``org_id``; ORM + session-bound SQL."""

from __future__ import annotations

import logging
from datetime import datetime

from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services.finance import _billing as billing_ops
from shared.infrastructure.db.services.finance import _credit_notes as cn_ops
from shared.infrastructure.db.services.finance import _invoices as inv_ops
from shared.infrastructure.db.services.finance import (
    _ledger_reporting as lr_rep,
)
from shared.infrastructure.db.services.finance._ledger_orm import (
    ledger_entries_exist_for_reference,
    ledger_get_journal_rows,
    ledger_insert_entries_in_session,
)

logger = logging.getLogger(__name__)


class FinanceDatabaseService(DomainDatabaseService):
    # --- Invoice -----------------------------------------------------------

    async def invoice_next_number(self, org_id: str) -> str:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            n = await inv_ops.invoice_next_number(session, oid)
            await self.end_write_session(session)
            return n

    async def invoice_insert(self, org_id: str, invoice):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await inv_ops.invoice_insert(session, oid, invoice)
            await self.end_write_session(session)
            return out

    async def invoice_get_by_id(self, org_id: str, invoice_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_get_by_id(session, oid, invoice_id)

    async def invoice_list(
        self,
        org_id: str,
        *,
        status: str | None = None,
        billing_entity: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 1000,
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list(
                session,
                oid,
                status=status,
                billing_entity=billing_entity,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

    async def invoice_update_fields(
        self, org_id: str, invoice_id: str, fields: dict
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await inv_ops.invoice_update_fields(
                session, oid, invoice_id, fields
            )
            await self.end_write_session(session)
            return out

    async def invoice_replace_line_items(
        self, org_id: str, invoice_id: str, line_items: list[dict]
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            sub = await inv_ops.invoice_replace_line_items(
                session, oid, invoice_id, line_items
            )
            await self.end_write_session(session)
            return sub

    async def invoice_insert_line_items(
        self, org_id: str, invoice_id: str, line_items: list[dict]
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            sub = await inv_ops.invoice_insert_line_items(
                session, oid, invoice_id, line_items
            )
            await self.end_write_session(session)
            return sub

    async def invoice_link_withdrawal(
        self, org_id: str, invoice_id: str, withdrawal_id: str
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_link_withdrawal(
                session, oid, invoice_id, withdrawal_id
            )
            await self.end_write_session(session)

    async def invoice_unlink_withdrawals(self, org_id: str, invoice_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await inv_ops.invoice_unlink_withdrawals(
                session, oid, invoice_id
            )
            await self.end_write_session(session)
            return out

    async def invoice_soft_delete(self, org_id: str, invoice_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_soft_delete(session, oid, invoice_id)
            await self.end_write_session(session)

    async def invoice_insert_row(self, org_id: str, row: dict):
        from datetime import datetime

        oid = as_uuid_required(org_id)
        async with self.session() as session:
            now = (
                datetime.fromisoformat(row["now"])
                if isinstance(row["now"], str)
                else row["now"]
            )
            dd = row["due_date"]
            due_s = dd.isoformat() if hasattr(dd, "isoformat") else dd
            await inv_ops.invoice_insert_row(
                session,
                oid,
                row["inv_id"],
                row["invoice_number"],
                row["billing_entity"],
                row["contact_name"],
                row["contact_email"],
                row["tax_rate"],
                row["payment_terms"],
                due_s,
                now,
            )
            await self.end_write_session(session)

    async def invoice_mark_paid_for_withdrawal(
        self, org_id: str, withdrawal_id: str
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_mark_paid_for_withdrawal(
                session, oid, withdrawal_id
            )
            await self.end_write_session(session)

    async def invoice_update_totals(
        self,
        org_id: str,
        invoice_id: str,
        subtotal: float,
        tax: float,
        total: float,
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_update_totals(
                session, oid, invoice_id, subtotal, tax, total
            )
            await self.end_write_session(session)

    async def invoice_update_billing(
        self, org_id: str, invoice_id: str, body: dict
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_update_billing(
                session,
                oid,
                invoice_id,
                body["billing_entity"],
                body["contact_name"],
                body["updated_at"],
            )
            await self.end_write_session(session)

    async def invoice_update_fields_dynamic(
        self, org_id: str, invoice_id: str, fields: dict
    ) -> None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_update_fields_dynamic(
                session, oid, invoice_id, fields
            )
            await self.end_write_session(session)

    async def invoice_set_xero_invoice_id(
        self,
        org_id: str,
        invoice_id: str,
        xero_id: str,
        xero_cogs_journal_id: str | None = None,
    ) -> None:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_set_xero_invoice_id(
                session,
                oid,
                invoice_id,
                xero_id,
                xero_cogs_journal_id,
            )
            await self.end_write_session(session)

    async def invoice_set_xero_sync_status(
        self, org_id: str, invoice_id: str, status: str
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await inv_ops.invoice_set_xero_sync_status(
                session, oid, invoice_id, status
            )
            await self.end_write_session(session)

    async def invoice_list_unsynced(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list_unsynced(session, oid)

    async def invoice_list_needing_reconciliation(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list_needing_reconciliation(
                session, oid
            )

    async def invoice_list_failed(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list_failed(session, oid)

    async def invoice_list_mismatch(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list_mismatch(session, oid)

    async def invoice_list_stale_cogs(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await inv_ops.invoice_list_stale_cogs(session, oid)

    # --- Credit notes ------------------------------------------------------

    async def credit_note_insert(
        self,
        org_id: str,
        return_id: str,
        invoice_id: str | None,
        items: list[dict],
        subtotal: float,
        tax: float,
        total: float,
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await cn_ops.credit_note_insert(
                session,
                oid,
                return_id,
                invoice_id,
                items,
                subtotal,
                tax,
                total,
            )
            await self.end_write_session(session)
            return out

    async def credit_note_get_by_id(self, org_id: str, credit_note_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_get_by_id(
                session, oid, credit_note_id
            )

    async def credit_note_list(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_list(session, oid, **kwargs)

    async def credit_note_apply(self, org_id: str, credit_note_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await cn_ops.credit_note_apply(session, oid, credit_note_id)
            await self.end_write_session(session)
            return out

    async def credit_note_set_xero_id(
        self, org_id: str, credit_note_id: str, xero_id: str
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await cn_ops.credit_note_set_xero_id(
                session, oid, credit_note_id, xero_id
            )
            await self.end_write_session(session)

    async def credit_note_set_sync_status(
        self, org_id: str, credit_note_id: str, status: str
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await cn_ops.credit_note_set_sync_status(
                session, oid, credit_note_id, status
            )
            await self.end_write_session(session)

    async def credit_note_list_unsynced(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_list_unsynced(session, oid)

    async def credit_note_list_needing_reconciliation(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_list_needing_reconciliation(
                session, oid
            )

    async def credit_note_list_failed(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_list_failed(session, oid)

    async def credit_note_list_mismatch(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await cn_ops.credit_note_list_mismatch(session, oid)

    # --- Payments ----------------------------------------------------------

    async def payment_insert(
        self, org_id: str, payment, withdrawal_ids: list[str] | None = None
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.payment_insert(
                session, oid, payment, withdrawal_ids
            )
            await self.end_write_session(session)

    async def payment_get_by_id(self, org_id: str, payment_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.payment_get_by_id(session, oid, payment_id)

    async def payment_list(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.payment_list(session, oid, **kwargs)

    async def payment_list_for_invoice(self, org_id: str, invoice_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.payment_list_for_invoice(
                session, oid, invoice_id
            )

    # --- Billing entities --------------------------------------------------

    async def billing_entity_insert(self, org_id: str, entity):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.billing_entity_insert(session, oid, entity)
            await self.end_write_session(session)
        logger.info(
            "billing_entity.created",
            extra={
                "org_id": org_id,
                "entity_id": entity.id,
                "entity_name": entity.name,
            },
        )

    async def billing_entity_get_by_id(self, org_id: str, entity_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.billing_entity_get_by_id(
                session, oid, entity_id
            )

    async def billing_entity_get_by_name(self, org_id: str, name: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.billing_entity_get_by_name(
                session, oid, name
            )

    async def billing_entity_list(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.billing_entity_list(session, oid, **kwargs)

    async def billing_entity_update(
        self, org_id: str, entity_id: str, updates: dict
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await billing_ops.billing_entity_update(
                session, oid, entity_id, updates
            )
            await self.end_write_session(session)
        logger.info(
            "billing_entity.updated",
            extra={"org_id": org_id, "entity_id": entity_id},
        )
        return out

    async def billing_entity_search(
        self, org_id: str, query: str, limit: int = 20
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.billing_entity_search(
                session, oid, query, limit
            )

    async def billing_entity_ensure(self, org_id: str, name: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await billing_ops.billing_entity_ensure(session, oid, name)
            await self.end_write_session(session)
            return out

    # --- Ledger ORM --------------------------------------------------------

    async def ledger_entries_exist(
        self, org_id: str, reference_type: str, reference_id: str
    ) -> bool:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await ledger_entries_exist_for_reference(
                session, oid, reference_type, reference_id
            )

    async def ledger_insert_entries(self, org_id: str, entries: list):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await ledger_insert_entries_in_session(session, oid, entries)
            await self.end_write_session(session)

    async def ledger_get_journal(self, org_id: str, journal_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await ledger_get_journal_rows(session, oid, journal_id)

    # --- Fiscal ------------------------------------------------------------

    async def fiscal_get_period(self, org_id: str, period_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.fiscal_get_period(session, oid, period_id)

    async def fiscal_list_periods(self, org_id: str, status: str | None = None):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.fiscal_list_periods(session, oid, status)

    async def fiscal_insert_period(
        self,
        org_id: str,
        period_id: str,
        name: str,
        start_date: str,
        end_date: str,
        created_at,
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.fiscal_insert_period(
                session,
                oid,
                period_id,
                name,
                start_date,
                end_date,
                created_at,
            )
            await self.end_write_session(session)

    async def fiscal_close_period(
        self,
        org_id: str,
        period_id: str,
        closed_by_id: str,
        closed_at,
    ):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.fiscal_close_period(
                session, oid, period_id, closed_by_id, closed_at
            )
            await self.end_write_session(session)

    async def fiscal_find_closed_covering(self, org_id: str, entry_date):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.fiscal_find_closed_covering(
                session, oid, entry_date
            )

    async def fiscal_check_period_open(
        self, org_id: str, entry_date: str | datetime
    ) -> None:
        """Raise ValueError if entry_date falls in a closed fiscal period."""
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            period = await billing_ops.fiscal_find_closed_covering(
                session, oid, entry_date
            )
        if period:
            period_id, period_name = period
            raise ValueError(
                f"Cannot create entries in closed fiscal period '{period_name or period_id}'"
            )

    # --- Org settings / OAuth ----------------------------------------------

    async def org_settings_get(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await billing_ops.org_settings_get(session, oid)

    async def org_settings_upsert(self, org_id: str, settings):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            out = await billing_ops.org_settings_upsert(session, oid, settings)
            await self.end_write_session(session)
            return out

    async def org_settings_clear_xero_tokens(self, org_id: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.org_settings_clear_xero_tokens(session, oid)
            await self.end_write_session(session)

    async def oauth_save_state(self, org_id: str, state: str):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            await billing_ops.oauth_save_state(session, oid, state)
            await self.end_write_session(session)

    async def oauth_pop_state(self, org_id: str, state: str):
        del org_id
        async with self.session() as session:
            out = await billing_ops.oauth_pop_state(session, state)
            await self.end_write_session(session)
            return out

    # --- Ledger reporting --------------------------------------------------

    async def ledger_summary_by_account(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.summary_by_account(session, oid, **kwargs)

    async def ledger_summary_by_department(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            raw = await lr_rep.summary_by_department(session, oid, **kwargs)
        from shared.kernel.types import round_money

        out = []
        for row in raw:
            revenue = row["revenue"]
            cost = row["cost"]
            shrinkage = row["shrinkage"]
            profit = round_money(revenue - cost)
            rev_f = float(revenue)
            out.append(
                {
                    "department": row["department"],
                    "revenue": revenue,
                    "cost": cost,
                    "shrinkage": shrinkage,
                    "profit": profit,
                    "margin_pct": round(float(profit) / rev_f * 100, 1)
                    if rev_f > 0
                    else 0.0,
                }
            )
        return out

    async def ledger_summary_by_job(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        limit = kwargs.get("limit", 100)
        offset = kwargs.get("offset", 0)
        search = kwargs.get("search")
        async with self.session() as session:
            (
                rows,
                total,
                all_revenue,
                all_cost,
            ) = await lr_rep.summary_by_job_aggregate(
                session,
                oid,
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
                search=search,
                limit=limit,
                offset=offset,
            )
        from shared.kernel.types import round_money

        result = []
        for row in rows:
            revenue = row["revenue"]
            cost = row["cost"]
            profit = round_money(revenue - cost)
            rev_f = float(revenue)
            result.append(
                {
                    "job_id": row["job_id"],
                    "billing_entity": row["billing_entity"],
                    "revenue": revenue,
                    "cost": cost,
                    "profit": profit,
                    "margin_pct": round(float(profit) / rev_f * 100, 1)
                    if rev_f > 0
                    else 0.0,
                    "withdrawal_count": row["transaction_count"],
                }
            )
        return {
            "rows": result,
            "total": total,
            "all_revenue": all_revenue,
            "all_cost": all_cost,
        }

    async def ledger_summary_by_billing_entity(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            raw = await lr_rep.summary_by_billing_entity(session, oid, **kwargs)
        from shared.kernel.types import round_money

        result = []
        for row in raw:
            revenue = row["revenue"]
            cost = row["cost"]
            profit = round_money(revenue - cost)
            result.append(
                {
                    "billing_entity": row["billing_entity"],
                    "revenue": revenue,
                    "cost": cost,
                    "profit": profit,
                    "ar_balance": row["ar_balance"],
                    "transaction_count": row["transaction_count"],
                }
            )
        return result

    async def ledger_summary_by_contractor(self, org_id: str, **kwargs):
        from operations.application.contractor_service import get_users_by_ids

        oid = as_uuid_required(org_id)
        async with self.session() as session:
            rows = await lr_rep.summary_by_contractor_raw(
                session, oid, **kwargs
            )
        cids = [r["contractor_id"] for r in rows]
        user_map = await get_users_by_ids(cids)
        return [
            {
                "contractor_id": row["contractor_id"],
                "revenue": row["revenue"],
                "ar_balance": row["ar_balance"],
                "transaction_count": row["transaction_count"],
                "name": user_map[row["contractor_id"]].name
                if row["contractor_id"] in user_map
                else "",
                "company": user_map[row["contractor_id"]].company
                if row["contractor_id"] in user_map
                else "",
            }
            for row in rows
        ]

    async def analytics_trend_series(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.trend_series(session, oid, **kwargs)

    async def analytics_ar_aging(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.ar_aging(session, oid, **kwargs)

    async def analytics_product_margins(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.product_margins(session, oid, **kwargs)

    async def analytics_purchase_spend(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.purchase_spend(session, oid, **kwargs)

    async def analytics_reference_counts(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.reference_counts(session, oid, **kwargs)

    async def analytics_returns_total(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            return await lr_rep.returns_total(session, oid, **kwargs)

    async def analytics_inventory_carrying_cost(self, org_id: str, **kwargs):
        oid = as_uuid_required(org_id)
        hr = float(kwargs.get("holding_rate_pct", 25.0))
        async with self.session() as session:
            return await lr_rep.inventory_carrying_cost(
                session, oid, holding_rate_pct=hr
            )
