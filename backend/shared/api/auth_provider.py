"""Auth provider abstraction — claim extraction from decoded JWT payloads.

Handles both Supabase-issued JWTs (role in app_metadata, user id in sub) and
internal dev/test JWTs (flat top-level claims) with a single extraction path.

Supabase tokens carry nested app_metadata/user_metadata; internal tokens don't.
The fallback chain handles both: try nested first, fall through to top-level.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.helpers.uuid import parse_uuid_str


@dataclass(frozen=True)
class ResolvedClaims:
    user_id: str
    email: str
    name: str
    role: str
    organization_id: str | None


def resolve_claims(payload: dict) -> ResolvedClaims:
    """Extract standardised claims from a decoded JWT payload.

    Works for both Supabase and internal JWTs. Supabase nests role/org in
    app_metadata and name in user_metadata; internal tokens use top-level
    claims. The fallback chain tries nested paths first, then top-level.

    Returns ResolvedClaims with organization_id=None when the token has no
    org claim — callers decide whether to reject or apply the dev fallback.

    Raises ValueError if a required claim (role, user_id) is missing.
    """
    app_meta = payload.get("app_metadata") or {}
    user_meta = payload.get("user_metadata") or {}

    # User ID: Supabase uses 'sub', internal uses 'user_id' (accept both)
    raw_user_id = payload.get("sub") or payload.get("user_id") or ""
    if not raw_user_id:
        raise ValueError("missing user id")
    user_id = parse_uuid_str("user id", str(raw_user_id))

    # Role: prefer app_metadata.role (Supabase custom claim), fall back to top-level.
    # Supabase sets a system role "authenticated" on every token — filter it out.
    role = app_meta.get("role") or payload.get("role") or ""
    if role == "authenticated":
        role = ""
    if not role:
        raise ValueError("missing role claim")

    email = payload.get("email") or ""
    name = payload.get("name") or user_meta.get("name") or ""
    org_id = (
        app_meta.get("organization_id")
        or payload.get("organization_id")
        or None
    )

    return ResolvedClaims(
        user_id=user_id,
        email=email,
        name=name,
        role=role,
        organization_id=org_id,
    )
