"""Operations application queries — safe for cross-context import.

Other bounded contexts import from here, never from operations.infrastructure directly.
All functions take ``org_id`` explicitly (no ambient repo scoping).
"""

from datetime import datetime

from operations.domain.material_request import MaterialRequest
from operations.domain.returns import MaterialReturn
from operations.domain.withdrawal import MaterialWithdrawal
from shared.infrastructure.db.base import get_database_manager


def _ops():
    return get_database_manager().operations


async def list_withdrawals(
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
    return await _ops().list_withdrawals(
        org_id,
        contractor_id=contractor_id,
        payment_status=payment_status,
        billing_entity=billing_entity,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


async def get_withdrawal_by_id(
    org_id: str,
    withdrawal_id: str,
) -> MaterialWithdrawal | None:
    return await _ops().get_withdrawal_by_id(org_id, withdrawal_id)


async def mark_withdrawal_paid(
    org_id: str,
    withdrawal_id: str,
    paid_at: datetime,
) -> MaterialWithdrawal | None:
    result, _changed = await _ops().mark_withdrawal_paid(
        org_id, withdrawal_id, paid_at
    )
    return result


async def list_returns(
    org_id: str,
    *,
    contractor_id: str | None = None,
    withdrawal_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 500,
) -> list[MaterialReturn]:
    return await _ops().list_returns(
        org_id,
        contractor_id=contractor_id,
        withdrawal_id=withdrawal_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


async def get_return_by_id(
    org_id: str, return_id: str
) -> MaterialReturn | None:
    return await _ops().get_return_by_id(org_id, return_id)


async def link_withdrawal_to_invoice(
    org_id: str, withdrawal_id: str, invoice_id: str
) -> bool:
    return await _ops().link_withdrawal_to_invoice(
        org_id, withdrawal_id, invoice_id
    )


async def unlink_withdrawals_from_invoice(
    org_id: str, withdrawal_ids: list[str]
) -> None:
    await _ops().unlink_withdrawals_from_invoice(org_id, withdrawal_ids)


async def mark_withdrawals_paid_by_invoice(
    org_id: str, invoice_id: str, paid_at: datetime
) -> None:
    await _ops().mark_withdrawals_paid_by_invoice(org_id, invoice_id, paid_at)


async def link_credit_note_to_return(
    org_id: str, return_id: str, credit_note_id: str
) -> None:
    await _ops().link_return_credit_note(org_id, return_id, credit_note_id)


async def units_sold_by_product(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    return await _ops().units_sold_by_product(
        org_id, start_date=start_date, end_date=end_date
    )


async def payment_status_breakdown(
    org_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, float]:
    return await _ops().payment_status_breakdown(
        org_id, start_date=start_date, end_date=end_date
    )


# --- Material request re-exports ---


async def insert_material_request(
    org_id: str, request: MaterialRequest
) -> None:
    await _ops().insert_material_request(org_id, request)


async def get_material_request_by_id(
    org_id: str,
    request_id: str,
) -> MaterialRequest | None:
    return await _ops().get_material_request_by_id(org_id, request_id)


async def list_material_requests_by_contractor(
    org_id: str,
    contractor_id: str,
    limit: int = 100,
) -> list[MaterialRequest]:
    return await _ops().list_material_requests_by_contractor(
        org_id, contractor_id, limit=limit
    )


async def list_pending_material_requests(
    org_id: str,
    limit: int = 100,
) -> list[MaterialRequest]:
    return await _ops().list_pending_material_requests(org_id, limit=limit)


async def mark_material_request_processed(
    org_id: str,
    request_id: str,
    withdrawal_id: str,
    processed_by_id: str,
    processed_at: datetime,
) -> bool:
    return await _ops().mark_material_request_processed(
        org_id,
        request_id,
        withdrawal_id,
        processed_by_id,
        processed_at,
    )
