"""Shared Xero test fixtures — settings, invoices, POs, mock HTTP clients."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from identity.domain.org_settings import OrgSettings


def make_settings(**overrides) -> OrgSettings:
    base = {
        "organization_id": "org-1",
        "xero_access_token": "tok-valid",
        "xero_refresh_token": "refresh-valid",
        "xero_tenant_id": "tenant-abc",
        "xero_token_expiry": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "xero_sales_account_code": "200",
        "xero_cogs_account_code": "500",
        "xero_inventory_account_code": "630",
        "xero_ap_account_code": "800",
    }
    base.update(overrides)
    return OrgSettings(**base)


def make_expired_settings() -> OrgSettings:
    return make_settings(xero_token_expiry=(datetime.now(UTC) - timedelta(hours=1)).isoformat())


def make_invoice(xero_invoice_id=None) -> dict:
    return {
        "id": "inv-local-1",
        "invoice_number": "INV-00001",
        "billing_entity": "On Point LLC",
        "status": "approved",
        "invoice_date": "2025-03-01T00:00:00Z",
        "due_date": "2025-03-31T00:00:00Z",
        "subtotal": 100.0,
        "tax": 10.0,
        "total": 110.0,
        "currency": "USD",
        "xero_invoice_id": xero_invoice_id,
        "line_items": [
            {
                "description": "2x16 Lumber",
                "quantity": 10,
                "unit_price": 10.0,
                "amount": 100.0,
                "cost": 6.0,
                "product_id": "prod-1",
                "job_id": "JOB-42",
            }
        ],
    }


def make_po(xero_bill_id=None) -> dict:
    return {
        "id": "po-local-1",
        "vendor_name": "Lumberyard Inc",
        "document_date": "2025-03-01",
        "xero_bill_id": xero_bill_id,
        "items": [
            {"name": "2x4 Pine", "delivered_qty": 50, "ordered_qty": 50, "cost": 4.0},
            {"name": "Drywall Sheet", "delivered_qty": 20, "ordered_qty": 20, "cost": 8.50},
        ],
    }


def make_credit_note() -> dict:
    return {
        "id": "cn-local-1",
        "credit_note_number": "CN-00001",
        "billing_entity": "On Point LLC",
        "status": "applied",
        "created_at": "2025-03-05T00:00:00Z",
        "xero_credit_note_id": None,
        "line_items": [
            {
                "description": "Returned lumber",
                "quantity": 3,
                "unit_price": 10.0,
                "amount": 30.0,
                "cost": 6.0,
            }
        ],
    }


def mock_response(response_json: dict):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = response_json
    return resp


def mock_http_client(response_json: dict, journal_json: dict | None = None):
    """Return a patched httpx.AsyncClient.

    If journal_json is given, put() will return response_json on the first
    call and journal_json on the second (for the COGS ManualJournals call).
    Otherwise put() always returns response_json.
    """
    inv_resp = mock_response(response_json)
    jnl_resp = mock_response(journal_json or {"ManualJournals": []})

    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.put = AsyncMock(side_effect=[inv_resp, jnl_resp])
    client.post = AsyncMock(side_effect=[inv_resp, jnl_resp])
    client.get = AsyncMock(return_value=inv_resp)
    return client
