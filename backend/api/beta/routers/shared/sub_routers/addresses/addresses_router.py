"""Address book routes — CRUD and autocomplete for saved addresses."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.api.deps import AdminDep, CurrentUserDep
from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.services.shared import StoredAddress

router = APIRouter(prefix="/addresses", tags=["addresses"])


class AddressCreate(BaseModel):
    label: str = ""
    line1: str
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    billing_entity_id: str | None = None
    job_id: str | None = None


@router.get("")
async def list_addresses(
    current_user: AdminDep,
    billing_entity_id: str | None = None,
    job_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    return await get_database_manager().shared.list_addresses(
        current_user.organization_id,
        billing_entity_id=billing_entity_id,
        job_id=job_id,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/search")
async def search_addresses(
    current_user: CurrentUserDep,
    q: str = "",
    limit: int = 20,
):
    """Autocomplete endpoint for address pickers."""
    oid = current_user.organization_id
    if not q.strip():
        return await get_database_manager().shared.list_addresses(
            oid, limit=limit
        )
    return await get_database_manager().shared.search_addresses(
        oid, q, limit=limit
    )


@router.get("/{address_id}")
async def get_address(address_id: str, current_user: AdminDep):
    addr = await get_database_manager().shared.get_address_by_id(
        address_id, current_user.organization_id
    )
    if not addr:
        raise HTTPException(status_code=404, detail="Address not found")
    return addr


@router.post("")
async def create_address(
    data: AddressCreate,
    current_user: AdminDep,
):
    if not data.line1.strip():
        raise HTTPException(
            status_code=400, detail="Address line 1 is required"
        )

    address = StoredAddress(
        id=new_uuid7_str(),
        label=data.label or data.line1[:80],
        line1=data.line1,
        line2=data.line2,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        country=data.country,
        billing_entity_id=data.billing_entity_id,
        job_id=data.job_id,
        organization_id=current_user.organization_id,
        created_at=datetime.now(UTC),
    )
    await get_database_manager().shared.insert_address(address)
    return address
