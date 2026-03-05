"""Credit note routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from kernel.types import CurrentUser
from identity.application.auth_service import require_role
from finance.infrastructure.credit_note_repo import credit_note_repo

router = APIRouter(prefix="/credit-notes", tags=["credit-notes"])


@router.get("")
async def list_credit_notes(
    invoice_id: Optional[str] = None,
    billing_entity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    org_id = current_user.organization_id
    return await credit_note_repo.list_credit_notes(
        invoice_id=invoice_id,
        billing_entity=billing_entity,
        status=status,
        start_date=start_date,
        end_date=end_date,
        organization_id=org_id,
    )


@router.get("/{credit_note_id}")
async def get_credit_note(
    credit_note_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
):
    org_id = current_user.organization_id
    cn = await credit_note_repo.get_by_id(credit_note_id, org_id)
    if not cn:
        raise HTTPException(status_code=404, detail="Credit note not found")
    return cn
