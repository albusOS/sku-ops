"""Stub Xero adapter — used in dev/test when no Xero credentials are configured."""

from finance.domain.invoice import InvoiceWithDetails
from finance.ports.invoicing_port import InvoiceSyncResult
from identity.domain.org_settings import OrgSettings


class StubXeroAdapter:
    async def sync_invoice(
        self, invoice: InvoiceWithDetails, _settings: OrgSettings
    ) -> InvoiceSyncResult:
        return InvoiceSyncResult(
            success=True,
            external_id=f"XERO-STUB-{invoice.id}",
            external_journal_id=f"XERO-STUB-JNL-{invoice.id}",
        )

    async def sync_po_receipt(
        self, po: dict, _cost_total: float, _settings: OrgSettings
    ) -> InvoiceSyncResult:
        return InvoiceSyncResult(
            success=True,
            external_id=f"XERO-STUB-BILL-{po.get('id', 'unknown')}",
        )

    async def sync_credit_note(self, credit_note, _settings: OrgSettings) -> InvoiceSyncResult:
        cn_id = credit_note.id if hasattr(credit_note, "id") else credit_note.get("id", "unknown")
        return InvoiceSyncResult(
            success=True,
            external_id=f"XERO-STUB-CN-{cn_id}",
        )

    async def repost_cogs_journal(
        self, invoice: InvoiceWithDetails, _settings: OrgSettings, _old_journal_id=None
    ) -> str:
        return f"XERO-STUB-COGS-REPOST-{invoice.id}"

    async def fetch_invoice_by_number(
        self, _invoice_number: str, _settings: OrgSettings
    ) -> dict | None:
        return None

    async def fetch_invoice(self, _xero_invoice_id: str, _settings: OrgSettings) -> dict:
        return {"total": 0.0, "line_count": 0, "status": "STUB"}

    async def fetch_credit_note(self, _xero_credit_note_id: str, _settings: OrgSettings) -> dict:
        return {"total": 0.0, "line_count": 0, "status": "STUB"}

    async def list_tracking_categories(self, _settings: OrgSettings) -> list[dict]:
        return [{"TrackingCategoryID": "stub-cat-id", "Name": "Job", "Status": "ACTIVE"}]

    async def refresh_token(self, settings: OrgSettings) -> OrgSettings:
        return settings

    async def get_tenants(self, _access_token: str) -> list[dict]:
        return [{"tenantId": "stub-tenant", "tenantName": "Stub Organisation"}]
