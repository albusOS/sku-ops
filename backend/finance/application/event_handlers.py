"""Finance domain event handlers — post-commit, best-effort side effects.

Ledger entries, invoice status updates, and payment recording are now written
inside the owning service's transaction (atomic, reliable).

These handlers handle genuinely optional side effects that can fail without
corrupting core data:
  - Auto-invoice creation on withdrawal (opt-in via org setting, default off)

WithdrawalPaid is dispatched for WS notification only — invoice/ledger writes
happen in the transaction inside withdrawal_service.
"""

from __future__ import annotations

import logging

from finance.application.invoice_service import create_invoice_from_withdrawals
from finance.application.org_settings_service import get_org_settings
from shared.infrastructure.domain_events import idempotent, on, retryable
from shared.kernel.domain_events import WithdrawalCreated

logger = logging.getLogger(__name__)


# ── Auto-invoice on withdrawal creation (opt-in) ──────────────────────────────


@on(WithdrawalCreated)
@idempotent
@retryable(max_retries=2, base_delay=0.1)
async def auto_invoice_withdrawal(event: WithdrawalCreated) -> None:
    """Attempt to create an invoice for the new withdrawal if org has auto_invoice enabled.

    Failure is logged and swallowed — the withdrawal and ledger are already
    committed. The invoice can always be created manually.
    """
    settings = await get_org_settings()
    if not settings.auto_invoice:
        return
    try:
        await create_invoice_from_withdrawals(withdrawal_ids=[event.withdrawal_id])
    except (ValueError, RuntimeError, OSError):
        logger.warning(
            "Auto-invoice failed for withdrawal %s, continuing without invoice",
            event.withdrawal_id,
            exc_info=True,
        )
