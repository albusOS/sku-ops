"""Finance persistence and ledger queries. Explicit ``org_id``; legacy repos use ``get_org_id()``."""

from __future__ import annotations

from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.db.services._org_scope import run_with_org


class FinanceDatabaseService(DomainDatabaseService):
    # --- Invoice (InvoiceRepo facade) ---------------------------------------

    async def invoice_next_number(self, org_id: str) -> str:
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.next_invoice_number)

    async def invoice_insert(self, org_id: str, invoice):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.insert, invoice)

    async def invoice_get_by_id(self, org_id: str, invoice_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.get_by_id, invoice_id)

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
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id,
            invoice_repo.list_invoices,
            status,
            billing_entity,
            start_date,
            end_date,
            limit,
        )

    async def invoice_update_fields(
        self, org_id: str, invoice_id: str, fields: dict
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.update_fields, invoice_id, fields
        )

    async def invoice_replace_line_items(
        self, org_id: str, invoice_id: str, line_items: list[dict]
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.replace_line_items, invoice_id, line_items
        )

    async def invoice_insert_line_items(
        self, org_id: str, invoice_id: str, line_items: list[dict]
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.insert_line_items, invoice_id, line_items
        )

    async def invoice_link_withdrawal(
        self, org_id: str, invoice_id: str, withdrawal_id: str
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.link_withdrawal, invoice_id, withdrawal_id
        )

    async def invoice_unlink_withdrawals(self, org_id: str, invoice_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.unlink_withdrawals, invoice_id
        )

    async def invoice_soft_delete(self, org_id: str, invoice_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.soft_delete, invoice_id)

    async def invoice_insert_row(self, org_id: str, row: dict):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.insert_invoice_row, row)

    async def invoice_mark_paid_for_withdrawal(
        self, org_id: str, withdrawal_id: str
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.mark_paid_for_withdrawal, withdrawal_id
        )

    async def invoice_update_totals(self, org_id: str, invoice_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.update_invoice_totals, invoice_id
        )

    async def invoice_update_billing(
        self, org_id: str, invoice_id: str, body: dict
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.update_invoice_billing, invoice_id, body
        )

    async def invoice_update_fields_dynamic(
        self, org_id: str, invoice_id: str, fields: dict
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id,
            invoice_repo.update_invoice_fields_dynamic,
            invoice_id,
            fields,
        )

    async def invoice_set_xero_invoice_id(
        self, org_id: str, invoice_id: str, xero_id: str
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.set_xero_invoice_id, invoice_id, xero_id
        )

    async def invoice_set_xero_sync_status(
        self, org_id: str, invoice_id: str, status: str
    ):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.set_xero_sync_status, invoice_id, status
        )

    async def invoice_list_unsynced(self, org_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.list_unsynced_invoices)

    async def invoice_list_needing_reconciliation(self, org_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(
            org_id, invoice_repo.list_invoices_needing_reconciliation
        )

    async def invoice_list_failed(self, org_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.list_failed_invoices)

    async def invoice_list_mismatch(self, org_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.list_mismatch_invoices)

    async def invoice_list_stale_cogs(self, org_id: str):
        from finance.infrastructure.invoice_repo import invoice_repo

        return await run_with_org(org_id, invoice_repo.list_stale_cogs_invoices)

    # --- Credit notes -------------------------------------------------------

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
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id,
            credit_note_repo.insert_credit_note,
            return_id,
            invoice_id,
            items,
            subtotal,
            tax,
            total,
        )

    async def credit_note_get_by_id(self, org_id: str, credit_note_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.get_by_id, credit_note_id
        )

    async def credit_note_list(self, org_id: str, **kwargs):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.list_credit_notes, **kwargs
        )

    async def credit_note_apply(self, org_id: str, credit_note_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id,
            credit_note_repo.apply_credit_note,
            credit_note_id,
        )

    async def credit_note_set_xero_id(
        self, org_id: str, credit_note_id: str, xero_id: str
    ):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id,
            credit_note_repo.set_xero_credit_note_id,
            credit_note_id,
            xero_id,
        )

    async def credit_note_set_sync_status(
        self, org_id: str, credit_note_id: str, status: str
    ):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id,
            credit_note_repo.set_credit_note_sync_status,
            credit_note_id,
            status,
        )

    async def credit_note_list_unsynced(self, org_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.list_unsynced_credit_notes
        )

    async def credit_note_list_needing_reconciliation(self, org_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.list_credit_notes_needing_reconciliation
        )

    async def credit_note_list_failed(self, org_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.list_failed_credit_notes
        )

    async def credit_note_list_mismatch(self, org_id: str):
        from finance.infrastructure.credit_note_repo import credit_note_repo

        return await run_with_org(
            org_id, credit_note_repo.list_mismatch_credit_notes
        )

    # --- Payments -----------------------------------------------------------

    async def payment_insert(
        self, org_id: str, payment, withdrawal_ids: list[str] | None = None
    ):
        from finance.infrastructure.payment_repo import payment_repo

        return await run_with_org(
            org_id, payment_repo.insert, payment, withdrawal_ids
        )

    async def payment_get_by_id(self, org_id: str, payment_id: str):
        from finance.infrastructure.payment_repo import payment_repo

        return await run_with_org(org_id, payment_repo.get_by_id, payment_id)

    async def payment_list(self, org_id: str, **kwargs):
        from finance.infrastructure.payment_repo import payment_repo

        return await run_with_org(org_id, payment_repo.list_payments, **kwargs)

    async def payment_list_for_invoice(self, org_id: str, invoice_id: str):
        from finance.infrastructure.payment_repo import payment_repo

        return await run_with_org(
            org_id, payment_repo.list_for_invoice, invoice_id
        )

    # --- Billing entities ----------------------------------------------------

    async def billing_entity_insert(self, org_id: str, entity):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(org_id, billing_entity_repo.insert, entity)

    async def billing_entity_get_by_id(self, org_id: str, entity_id: str):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(
            org_id, billing_entity_repo.get_by_id, entity_id
        )

    async def billing_entity_get_by_name(self, org_id: str, name: str):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(org_id, billing_entity_repo.get_by_name, name)

    async def billing_entity_list(self, org_id: str, **kwargs):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(
            org_id, billing_entity_repo.list_billing_entities, **kwargs
        )

    async def billing_entity_update(
        self, org_id: str, entity_id: str, updates: dict
    ):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(
            org_id, billing_entity_repo.update, entity_id, updates
        )

    async def billing_entity_search(
        self, org_id: str, query: str, limit: int = 20
    ):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(
            org_id, billing_entity_repo.search, query, limit
        )

    async def billing_entity_ensure(self, org_id: str, name: str):
        from finance.infrastructure.billing_entity_repo import (
            billing_entity_repo,
        )

        return await run_with_org(
            org_id, billing_entity_repo.ensure_billing_entity, name
        )

    # --- Ledger --------------------------------------------------------------

    async def ledger_entries_exist(
        self, org_id: str, reference_type: str, reference_id: str
    ) -> bool:
        from finance.infrastructure.ledger_repo import entries_exist

        return await run_with_org(
            org_id, entries_exist, reference_type, reference_id
        )

    async def ledger_insert_entries(self, org_id: str, entries: list):
        from finance.infrastructure.ledger_repo import insert_entries

        return await run_with_org(org_id, insert_entries, entries)

    async def ledger_get_journal(self, org_id: str, journal_id: str):
        from finance.infrastructure.ledger_repo import get_journal

        return await run_with_org(org_id, get_journal, journal_id)

    # --- Fiscal periods ------------------------------------------------------

    async def fiscal_get_period(self, org_id: str, period_id: str):
        from finance.infrastructure import fiscal_period_repo as fpr

        return await run_with_org(org_id, fpr.get_period, period_id)

    async def fiscal_list_periods(self, org_id: str, status: str | None = None):
        from finance.infrastructure import fiscal_period_repo as fpr

        return await run_with_org(org_id, fpr.list_periods, status)

    async def fiscal_insert_period(
        self,
        org_id: str,
        period_id: str,
        name: str,
        start_date: str,
        end_date: str,
        created_at,
    ):
        from finance.infrastructure import fiscal_period_repo as fpr

        return await run_with_org(
            org_id,
            fpr.insert_period,
            period_id,
            name,
            start_date,
            end_date,
            created_at,
        )

    async def fiscal_close_period(
        self, org_id: str, period_id: str, closed_by_id: str, closed_at: str
    ):
        from finance.infrastructure import fiscal_period_repo as fpr

        return await run_with_org(
            org_id, fpr.close_period, period_id, closed_by_id, closed_at
        )

    async def fiscal_find_closed_covering(self, org_id: str, entry_date):
        from finance.infrastructure import fiscal_period_repo as fpr

        return await run_with_org(
            org_id, fpr.find_closed_period_covering, entry_date
        )

    # --- Org settings / OAuth -----------------------------------------------

    async def org_settings_get(self, org_id: str):
        from finance.infrastructure.org_settings_repo import org_settings_repo

        return await run_with_org(org_id, org_settings_repo.get_org_settings)

    async def org_settings_upsert(self, org_id: str, settings):
        from finance.infrastructure.org_settings_repo import org_settings_repo

        return await run_with_org(
            org_id, org_settings_repo.upsert_org_settings, settings
        )

    async def org_settings_clear_xero_tokens(self, org_id: str):
        from finance.infrastructure.org_settings_repo import org_settings_repo

        return await run_with_org(org_id, org_settings_repo.clear_xero_tokens)

    async def oauth_save_state(self, org_id: str, state: str):
        from finance.infrastructure.oauth_state_repo import save_oauth_state

        return await run_with_org(org_id, save_oauth_state, state)

    async def oauth_pop_state(self, org_id: str, state: str):
        from finance.infrastructure.oauth_state_repo import pop_oauth_state

        return await run_with_org(org_id, pop_oauth_state, state)

    # --- Ledger queries / analytics -----------------------------------------

    async def ledger_summary_by_account(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await run_with_org(org_id, lq.summary_by_account, **kwargs)

    async def ledger_summary_by_department(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await run_with_org(org_id, lq.summary_by_department, **kwargs)

    async def ledger_summary_by_job(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await run_with_org(org_id, lq.summary_by_job, **kwargs)

    async def ledger_summary_by_billing_entity(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await run_with_org(
            org_id, lq.summary_by_billing_entity, **kwargs
        )

    async def ledger_summary_by_contractor(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await run_with_org(org_id, lq.summary_by_contractor, **kwargs)

    async def ledger_units_sold_by_product(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await lq.units_sold_by_product(
            org_id,
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

    async def ledger_payment_status_breakdown(self, org_id: str, **kwargs):
        from finance.application import ledger_queries as lq

        return await lq.payment_status_breakdown(
            org_id,
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

    async def analytics_trend_series(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.trend_series, **kwargs)

    async def analytics_ar_aging(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.ar_aging, **kwargs)

    async def analytics_product_margins(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.product_margins, **kwargs)

    async def analytics_purchase_spend(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.purchase_spend, **kwargs)

    async def analytics_reference_counts(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.reference_counts, **kwargs)

    async def analytics_returns_total(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.returns_total, **kwargs)

    async def analytics_inventory_carrying_cost(self, org_id: str, **kwargs):
        from finance.application import ledger_analytics as la

        return await run_with_org(org_id, la.inventory_carrying_cost, **kwargs)
