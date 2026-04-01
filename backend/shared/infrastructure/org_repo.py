"""Organization (tenant) repository — delegates to SharedDatabaseService."""

from datetime import datetime

from pydantic import BaseModel

from shared.infrastructure.db.base import get_database_manager


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime | str | None = None


async def get_by_id(org_id: str) -> Organization | None:
    db = get_database_manager()
    row = await db.shared.get_organization_by_id(org_id)
    if row is None:
        return None
    return Organization.model_validate(row.model_dump())


async def list_all() -> list[Organization]:
    db = get_database_manager()
    rows = await db.shared.list_organizations()
    return [Organization.model_validate(r.model_dump()) for r in rows]
