"""Address repository — delegates to SharedDatabaseService."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


class StoredAddress(BaseModel):
    """Typed model for a persisted address row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str = ""
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"
    billing_entity_id: str | None = None
    job_id: str | None = None
    organization_id: str = ""
    created_at: datetime | None = None


async def insert(address: StoredAddress) -> None:
    db = get_database_manager()
    await db.shared.insert_address(address)


async def get_by_id(address_id: str) -> StoredAddress | None:
    db = get_database_manager()
    row = await db.shared.get_address_by_id(address_id, get_org_id())
    if row is None:
        return None
    return StoredAddress.model_validate(row.model_dump())


async def list_addresses(
    billing_entity_id: str | None = None,
    job_id: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[StoredAddress]:
    db = get_database_manager()
    rows = await db.shared.list_addresses(
        get_org_id(),
        billing_entity_id=billing_entity_id,
        job_id=job_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [StoredAddress.model_validate(r.model_dump()) for r in rows]


async def search(query: str, limit: int = 20) -> list[StoredAddress]:
    db = get_database_manager()
    rows = await db.shared.search_addresses(get_org_id(), query, limit=limit)
    return [StoredAddress.model_validate(r.model_dump()) for r in rows]


class AddressRepo:
    insert = staticmethod(insert)
    get_by_id = staticmethod(get_by_id)
    list_addresses = staticmethod(list_addresses)
    search = staticmethod(search)


address_repo = AddressRepo()
