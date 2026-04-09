"""Auth HTTP surface - backend-owned profile hydration for Supabase sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from shared.api.deps import CurrentUserOnboardingDep
from shared.application.onboarding_completion import (
    CompleteOnboardingCommand,
    complete_onboarding,
)
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


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
    needs_onboarding: bool = False


class OrganizationOption(BaseModel):
    id: str
    name: str


class CompleteProfileBody(BaseModel):
    company: str = Field(
        "",
        description="Company name (required for contractors, optional for admins)",
    )
    phone: str = ""
    organization_name: str | None = Field(
        None,
        description="New org name (admin: create new org)",
    )
    organization_id: str | None = Field(
        None,
        description="Existing org id (admin: join existing, contractor: required)",
    )


def _row_to_user(row) -> UserResponse:
    oid_raw = row.get("organization_id") or ""
    oid = str(oid_raw).strip() if oid_raw else ""
    needs = not bool(oid)
    return UserResponse(
        id=str(row["id"]),
        email=row["email"],
        name=row["name"],
        role=row["role"],
        organization_id="" if needs else oid,
        company=row["company"] or "",
        billing_entity=row.get("billing_entity") or "",
        billing_entity_id=row.get("billing_entity_id"),
        phone=row["phone"] or "",
        needs_onboarding=needs,
    )


def _user_from_claims(current_user, *, needs_onboarding: bool = False) -> UserResponse:
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
        needs_onboarding=needs_onboarding,
    )


@router.get("/me")
async def me(current_user: CurrentUserOnboardingDep) -> UserResponse:
    """Return the enriched user profile for the authenticated caller."""
    shared_svc = _db_shared()
    try:
        row = await shared_svc.fetch_user_safe_by_id(current_user.id)
        if not row and current_user.email:
            row = await shared_svc.fetch_user_by_email(current_user.email)
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Database temporarily unavailable - please try again",
        ) from None
    if not row:
        raise HTTPException(
            status_code=401,
            detail="User profile not found - please log out and sign up again",
        )
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return _row_to_user(row)


@router.get("/organizations", response_model=list[OrganizationOption])
async def list_organization_options(_current_user: CurrentUserOnboardingDep):
    """Organizations visible during contractor onboarding (name/id for dropdown)."""
    orgs = await _db_shared().list_organizations()
    return [OrganizationOption(id=o.id, name=o.name) for o in orgs]


@router.post("/complete-profile", response_model=UserResponse)
async def complete_profile_route(
    body: CompleteProfileBody,
    current_user: CurrentUserOnboardingDep,
):
    try:
        result = await complete_onboarding(
            CompleteOnboardingCommand(
                user_id=current_user.id,
                company=body.company,
                phone=body.phone,
                organization_name=body.organization_name,
                join_organization_id=body.organization_id,
            )
        )
    except ValueError as e:
        detail = str(e)
        if detail == "Organization not found":
            raise HTTPException(status_code=404, detail=detail) from e
        if detail == "already_onboarded":
            raise HTTPException(status_code=409, detail="Profile is already onboarded") from e
        raise HTTPException(status_code=422, detail=detail) from e
    except RuntimeError as e:
        logger.exception("complete_profile_failed", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=str(e)) from e

    return UserResponse(
        id=result.id,
        email=result.email,
        name=result.name,
        role=result.role,
        organization_id=result.organization_id,
        company=result.company,
        billing_entity=result.billing_entity,
        billing_entity_id=result.billing_entity_id,
        phone=result.phone,
        needs_onboarding=result.needs_onboarding,
    )
