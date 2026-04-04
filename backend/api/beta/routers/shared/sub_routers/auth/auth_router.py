"""Auth HTTP surface - backend-owned profile hydration for Supabase sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.api.deps import CurrentUserDep  # noqa: TC001
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.constants import DEFAULT_ORG_ID


def _db_shared():
    return get_database_manager().shared


router = APIRouter(prefix="/auth", tags=["auth"])


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    organization_id: str
    company: str
    billing_entity: str
    billing_entity_id: str | None = None
    phone: str


def _row_to_user(row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        role=row["role"],
        organization_id=row["organization_id"] or DEFAULT_ORG_ID,
        company=row["company"] or "",
        billing_entity=row["billing_entity"] or "",
        billing_entity_id=row.get("billing_entity_id"),
        phone=row["phone"] or "",
    )


# ── Routes ────────────────────────────────────────────────────────────────────


def _user_from_claims(current_user) -> UserResponse:
    """Build a UserResponse directly from JWT claims (no DB lookup)."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        organization_id=current_user.organization_id,
        company="",
        billing_entity="",
        billing_entity_id=None,
        phone="",
    )


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserResponse:
    """Return the enriched user profile for the authenticated caller.

    Works with both dev-issued JWTs and Supabase-issued JWTs — looks up the
    users table by sub/user_id so profile fields (company, billing_entity, etc.)
    are always populated from the source of truth.

    Falls back to JWT claims if the user row doesn't exist (Supabase-first new
    users not yet in the local profile table) or if the DB is not initialised
    (e.g. smoke-test context).
    """
    shared_svc = _db_shared()
    try:
        row = await shared_svc.fetch_user_safe_by_id(current_user.id)
        if not row and current_user.email:
            row = await shared_svc.fetch_user_by_email(current_user.email)
    except RuntimeError:
        return _user_from_claims(current_user)
    if not row:
        return _user_from_claims(current_user)
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return _row_to_user(row)
