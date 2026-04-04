"""Material request service — creation, listing, and processing use cases."""

import uuid
from datetime import UTC, datetime

from operations.application.contractor_service import get_contractor_by_id
from operations.application.withdrawal_service import create_withdrawal_wired
from operations.domain.enums import MaterialRequestStatus
from operations.domain.material_request import (
    MaterialRequest,
    MaterialRequestCreate,
)
from operations.domain.withdrawal import (
    ContractorContext,
    MaterialWithdrawal,
    MaterialWithdrawalCreate,
)
from shared.infrastructure.db import get_org_id, transaction
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.domain_events import dispatch
from shared.kernel.domain_events import (
    MaterialRequestCreated,
    MaterialRequestProcessed,
)
from shared.kernel.types import CurrentUser


def _db_operations():
    return get_database_manager().operations


def _db_jobs():
    return get_database_manager().jobs


async def _resolve_job_uuid_for_storage(
    job_id: str | None,
    organization_id: str,
) -> str | None:
    """Persisted ``material_requests.job_id`` is a UUID FK; UI sends job code or UUID string."""
    if not job_id or not str(job_id).strip():
        return None
    s = str(job_id).strip()
    try:
        return str(uuid.UUID(s))
    except ValueError:
        job = await _db_jobs().get_job_by_code(s, organization_id)
        if job is None:
            raise MaterialRequestError(f"Unknown job: {s}", 400) from None
        return str(job.id)


class MaterialRequestError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def create_material_request(
    data: MaterialRequestCreate,
    current_user: CurrentUser,
) -> MaterialRequest:
    """Validate and persist a new material request from a contractor.

    Raises MaterialRequestError on validation failure.
    """
    if current_user.role != "contractor":
        raise MaterialRequestError("Only contractors can create material requests", 403)
    if not data.items:
        raise MaterialRequestError("At least one item is required", 400)

    resolved_job_id = await _resolve_job_uuid_for_storage(
        data.job_id,
        current_user.organization_id,
    )
    mat_request = MaterialRequest(
        contractor_id=current_user.id,
        contractor_name=current_user.name,
        items=data.items,
        job_id=resolved_job_id,
        service_address=data.service_address,
        notes=data.notes,
        organization_id=current_user.organization_id,
    )
    await _db_operations().insert_material_request(current_user.organization_id, mat_request)
    fetched = await _db_operations().get_material_request_by_id(current_user.organization_id, mat_request.id)
    result = fetched or mat_request

    await dispatch(
        MaterialRequestCreated(
            org_id=current_user.organization_id,
            request_id=mat_request.id,
            contractor_id=current_user.id,
        )
    )
    return result


async def list_material_requests(current_user: CurrentUser) -> list:
    """Return material requests scoped to the caller's role.

    Contractors see only their own requests; admins see all pending.
    Raises MaterialRequestError(403) for unknown roles.
    """
    if current_user.role == "contractor":
        return await _db_operations().list_material_requests_by_contractor(
            current_user.organization_id, current_user.id
        )
    if current_user.role == "admin":
        return await _db_operations().list_pending_material_requests(current_user.organization_id)
    raise MaterialRequestError("Insufficient permissions", 403)


async def process_material_request(
    request_id: str,
    job_id_override: str | None,
    service_address_override: str | None,
    notes: str | None,
    current_user_id: str,
    current_user_name: str,
) -> MaterialWithdrawal:
    """Validate a pending material request, create a withdrawal, and mark it processed.

    Raises MaterialRequestError on validation failure.
    """
    org_id = get_org_id()
    req = await _db_operations().get_material_request_by_id(org_id, request_id)
    if not req:
        raise MaterialRequestError("Material request not found", 404)
    if req.status != MaterialRequestStatus.PENDING:
        raise MaterialRequestError("Request already processed")

    contractor = await get_contractor_by_id(req.contractor_id)
    if not contractor or contractor.role != "contractor":
        raise MaterialRequestError("Contractor not found")
    if contractor.organization_id and contractor.organization_id != org_id:
        raise MaterialRequestError("Contractor belongs to different organization", 403)

    raw_job = (job_id_override or req.job_id or "").strip()
    service_address = (service_address_override or req.service_address or "").strip()
    if not raw_job:
        raise MaterialRequestError("Job ID is required")
    if not service_address:
        raise MaterialRequestError("Service address is required")

    # Withdrawals persist ``job_id`` as the jobs.id UUID FK, not the human code.
    resolved_job = None
    try:
        uuid.UUID(raw_job)
        resolved_job = await _db_jobs().get_job_by_id(raw_job, org_id)
    except ValueError:
        pass
    if resolved_job is None:
        resolved_job = await _db_jobs().get_job_by_code(raw_job, org_id)
    if resolved_job is None:
        raise MaterialRequestError("Job not found", 404)

    job_uuid_for_withdrawal = str(resolved_job.id)

    withdrawal_data = MaterialWithdrawalCreate(
        items=list(req.items),
        job_id=job_uuid_for_withdrawal,
        service_address=service_address,
        notes=notes,
    )

    current_user = CurrentUser(
        id=current_user_id,
        name=current_user_name,
        email="",
        role="admin",
        organization_id=org_id,
    )

    contractor_ctx = ContractorContext(
        id=contractor.id,
        name=contractor.name,
        company=contractor.company,
        billing_entity=contractor.billing_entity,
        billing_entity_id=contractor.billing_entity_id,
    )

    async with transaction():
        withdrawal = await create_withdrawal_wired(withdrawal_data, contractor_ctx, current_user)
        await _db_operations().mark_material_request_processed(
            org_id,
            request_id=request_id,
            withdrawal_id=withdrawal.id,
            processed_by_id=current_user_id,
            processed_at=datetime.now(UTC),
        )

    await dispatch(
        MaterialRequestProcessed(
            org_id=org_id,
            request_id=request_id,
            withdrawal_id=withdrawal.id,
        )
    )
    return withdrawal
