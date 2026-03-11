"""Xero API adapter — real Xero API v2 via OAuth 2.0.

Composed from mixins for maintainability. Public API is ``XeroAdapter``
and the standalone helper ``_xero_status``.
"""

from finance.adapters.xero._base import XeroBaseMixin, _xero_status
from finance.adapters.xero._credit_note_sync import XeroCreditNoteSyncMixin
from finance.adapters.xero._invoice_sync import XeroInvoiceSyncMixin
from finance.adapters.xero._journal_sync import XeroJournalSyncMixin
from finance.adapters.xero._oauth import XeroOAuthMixin
from finance.adapters.xero._reconcile import XeroReconcileMixin

__all__ = ["XeroAdapter", "_xero_status"]


class XeroAdapter(
    XeroBaseMixin,
    XeroOAuthMixin,
    XeroInvoiceSyncMixin,
    XeroJournalSyncMixin,
    XeroCreditNoteSyncMixin,
    XeroReconcileMixin,
):
    pass
