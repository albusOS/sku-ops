"""Billing entity master data routes."""

from fastapi import APIRouter, HTTPException

from finance.application.queries import get_billing_entity_by_id
from finance.application.queries import list_billing_entities as query_list
from finance.application.queries import search_billing_entities as query_search
from finance.domain.billing_entity import (
    BillingEntity,
    BillingEntityCreate,
    BillingEntityUpdate,
)
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _db_finance():
    return get_database_manager().finance


router = APIRouter(prefix="/billing-entities", tags=["billing-entities"])


@router.get("")
async def list_billing_entities(
    current_user: AdminDep,
    is_active: bool | None = None,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    return await query_list(
        is_active=is_active,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.get("/search")
async def search_billing_entities(
    current_user: AdminDep,
    q: str = "",
    limit: int = 20,
):
    """Autocomplete endpoint for billing entity pickers."""
    if not q.strip():
        return await query_list(
            is_active=True,
            limit=limit,
        )
    return await query_search(q, limit=limit)


@router.get("/{entity_id}")
async def get_billing_entity(entity_id: str, current_user: AdminDep):
    entity = await get_billing_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Billing entity not found")
    return entity


@router.post("")
async def create_billing_entity(
    data: BillingEntityCreate,
    current_user: AdminDep,
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    oid = get_org_id()
    existing = await _db_finance().billing_entity_get_by_name(oid, name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Billing entity '{name}' already exists")

    entity = BillingEntity(
        name=name,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        billing_address=data.billing_address,
        payment_terms=data.payment_terms,
        organization_id=oid,
    )
    await _db_finance().billing_entity_insert(oid, entity)
    return entity.model_dump()


@router.put("/{entity_id}")
async def update_billing_entity(
    entity_id: str,
    data: BillingEntityUpdate,
    current_user: AdminDep,
):
    existing = await get_billing_entity_by_id(entity_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Billing entity not found")

    oid = get_org_id()
    return await _db_finance().billing_entity_update(oid, entity_id, data.model_dump(exclude_none=True))
