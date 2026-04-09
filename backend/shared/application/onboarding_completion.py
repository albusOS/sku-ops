"""Complete self-serve signup onboarding: org assignment + Supabase app_metadata."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from shared.helpers.uuid import new_uuid7_str, parse_uuid_str
from shared.infrastructure.db import sql_execute, transaction
from shared.infrastructure.db.base import get_database_manager


def _manager():
    return get_database_manager()


def _db_finance():
    return _manager().finance


logger = logging.getLogger(__name__)


async def sync_supabase_app_metadata_for_onboarding(
    *, user_id: str, role: str, organization_id: str
) -> None:
    """Push role + organization_id into Supabase Auth app_metadata for JWT claims."""
    sb = await _manager().db_service.get_async_supabase_admin()
    if sb is None:
        logger.error(
            "onboarding_completed_without_supabase_admin",
            extra={"user_id": user_id},
        )
        msg = "Supabase admin is not configured (PRIVATE_SUPABASE_SECRET_KEY)"
        raise RuntimeError(msg)
    meta: dict = {"role": role, "organization_id": organization_id}
    await sb.auth.admin.update_user_by_id(user_id, {"app_metadata": meta})


@dataclass(frozen=True)
class CompleteOnboardingCommand:
    user_id: str
    company: str
    phone: str
    organization_name: str | None
    join_organization_id: str | None


@dataclass(frozen=True)
class CompleteOnboardingResult:
    id: str
    email: str
    name: str
    role: str
    organization_id: str
    company: str
    billing_entity: str
    billing_entity_id: str | None
    phone: str
    needs_onboarding: bool


def _slug_from_name(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-") or "organization"
    return f"{base[:50]}-{new_uuid7_str()[:8]}"


async def complete_onboarding(cmd: CompleteOnboardingCommand) -> CompleteOnboardingResult:
    uid = parse_uuid_str("user id", cmd.user_id)
    company = (cmd.company or "").strip()
    phone = (cmd.phone or "").strip()

    async with transaction():
        cur = await sql_execute(
            "SELECT id, email, name, role, organization_id::text, company, phone, "
            "billing_entity_id::text FROM users WHERE id = $1",
            (uid,),
        )
        if not cur.rows:
            msg = "User profile not found"
            raise ValueError(msg)
        row = cur.rows[0]
        if row.get("organization_id"):
            msg = "already_onboarded"
            raise ValueError(msg)
        role = row["role"]
        email = row["email"]
        name = row["name"]

        org_id: str | None = None
        billing_entity_id: str | None = None

        if role == "admin":
            has_org_name = cmd.organization_name and str(cmd.organization_name).strip()
            has_join_org = cmd.join_organization_id and str(cmd.join_organization_id).strip()
            if has_org_name and has_join_org:
                msg = (
                    "Provide either organization_name (create) or organization_id (join), not both"
                )
                raise ValueError(msg)
            if not has_org_name and not has_join_org:
                msg = "organization_name or organization_id is required for admin onboarding"
                raise ValueError(msg)
            if has_org_name:
                org_name = str(cmd.organization_name).strip()
                org_id = new_uuid7_str()
                slug = _slug_from_name(org_name)
                await sql_execute(
                    "INSERT INTO organizations (id, name, slug, created_at) "
                    "VALUES ($1, $2, $3, NOW())",
                    (org_id, org_name, slug),
                    read_only=False,
                )
                await sql_execute(
                    "INSERT INTO org_settings (organization_id, auto_invoice, default_tax_rate) "
                    "VALUES ($1, FALSE, 0.10)",
                    (org_id,),
                    read_only=False,
                )
            else:
                join_org = parse_uuid_str("organization_id", cmd.join_organization_id)
                ocheck = await sql_execute(
                    "SELECT id FROM organizations WHERE id = $1", (join_org,)
                )
                if not ocheck.rows:
                    msg = "Organization not found"
                    raise ValueError(msg)
                org_id = join_org
        elif role == "contractor":
            if not company:
                msg = "company is required for contractor onboarding"
                raise ValueError(msg)
            if not cmd.join_organization_id:
                msg = "organization_id is required for contractor onboarding"
                raise ValueError(msg)
            join_org = parse_uuid_str("organization_id", cmd.join_organization_id)
            ocheck = await sql_execute("SELECT id FROM organizations WHERE id = $1", (join_org,))
            if not ocheck.rows:
                msg = "Organization not found"
                raise ValueError(msg)
            org_id = join_org
            billing_label = company or "Independent"
            be = await _db_finance().billing_entity_ensure(org_id, billing_label)
            billing_entity_id = be.id if be else None
        else:
            msg = "Unsupported role for onboarding"
            raise ValueError(msg)

        await sql_execute(
            "UPDATE users SET organization_id = $1, company = $2, phone = $3, "
            "billing_entity_id = COALESCE(CAST($4 AS uuid), billing_entity_id) "
            "WHERE id = $5",
            (org_id, company, phone, billing_entity_id, uid),
            read_only=False,
        )

        await sync_supabase_app_metadata_for_onboarding(
            user_id=str(uid),
            role=role,
            organization_id=str(org_id),
        )

    be_name = ""
    if billing_entity_id:
        bec = await sql_execute(
            "SELECT name FROM billing_entities WHERE id = $1",
            (billing_entity_id,),
        )
        if bec.rows:
            be_name = bec.rows[0]["name"] or ""

    return CompleteOnboardingResult(
        id=uid,
        email=email,
        name=name,
        role=role,
        organization_id=str(org_id),
        company=company,
        billing_entity=be_name,
        billing_entity_id=billing_entity_id,
        phone=phone,
        needs_onboarding=False,
    )
