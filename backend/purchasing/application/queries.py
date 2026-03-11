"""Purchasing application queries — safe for cross-context import.

Other bounded contexts import from here, never from purchasing.infrastructure directly.
"""

from purchasing.infrastructure.po_repo import po_repo as _po_repo


async def get_po_with_cost(po_id: str, org_id: str) -> dict | None:
    return await _po_repo.get_po_with_cost(po_id, org_id)


async def list_unsynced_po_bills(org_id: str) -> list[dict]:
    return await _po_repo.list_unsynced_po_bills(org_id)


async def list_failed_po_bills(org_id: str) -> list[dict]:
    return await _po_repo.list_failed_po_bills(org_id)


async def set_xero_sync_status(po_id: str, status: str, updated_at: str) -> None:
    await _po_repo.set_xero_sync_status(po_id, status, updated_at)


async def set_xero_bill_id(po_id: str, xero_bill_id: str, updated_at: str) -> None:
    await _po_repo.set_xero_bill_id(po_id, xero_bill_id, updated_at)


async def po_summary_by_status(org_id: str) -> dict[str, dict]:
    """PO count and total grouped by status. Used by dashboard."""
    return await _po_repo.summary_by_status(org_id)


async def list_pos(org_id: str, status: str | None = None) -> list:
    return await _po_repo.list_pos(org_id, status=status)


async def get_po(po_id: str, org_id: str) -> dict | None:
    return await _po_repo.get_po(po_id, org_id)


async def get_po_items(po_id: str) -> list:
    return await _po_repo.get_po_items(po_id)
