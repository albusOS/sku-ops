"""Tests for JWT claim resolution — both internal and Supabase JWT shapes.

Validates that resolve_claims() correctly extracts user_id, role, email,
name, and organization_id from both token formats, and rejects malformed
tokens with clear errors.

User ids must be valid UUID strings (canonicalized); see parse_uuid_str.
"""

import pytest

from shared.api.auth_provider import ResolvedClaims, resolve_claims

# Valid UUIDs for sub / user_id (Postgres PK + asyncpg bind rules)
_U1 = "00000000-0000-0000-0000-000000000001"
_U2 = "00000000-0000-0000-0000-000000000002"
_SB1 = "00000000-0000-0000-0000-000000000011"
_SB2 = "00000000-0000-0000-0000-000000000012"
_SB3 = "00000000-0000-0000-0000-000000000013"
_SB4 = "00000000-0000-0000-0000-000000000014"

# ── Internal (dev/test) JWT shape ────────────────────────────────────────────


class TestInternalClaims:
    """Internal JWT: flat top-level claims (user_id, role, name, email)."""

    def test_full_claims(self):
        payload = {
            "user_id": _U1,
            "role": "admin",
            "name": "Alice",
            "email": "alice@test.com",
            "organization_id": "org-1",
        }
        c = resolve_claims(payload)
        assert c == ResolvedClaims(
            user_id=_U1,
            email="alice@test.com",
            name="Alice",
            role="admin",
            organization_id="org-1",
        )

    def test_sub_fallback_for_user_id(self):
        """user_id missing → falls back to sub."""
        payload = {"sub": _U2, "role": "contractor"}
        c = resolve_claims(payload)
        assert c.user_id == _U2

    def test_missing_user_id_raises(self):
        with pytest.raises(ValueError, match="missing user id"):
            resolve_claims({"role": "admin"})

    def test_invalid_user_id_uuid_raises(self):
        with pytest.raises(ValueError, match="invalid user id"):
            resolve_claims(
                {"sub": "not-a-valid-uuid", "role": "admin"},
            )

    def test_user_id_whitespace_trimmed_and_canonicalized(self):
        """Uppercase UUID in token is normalized to str(UUID) form."""
        c = resolve_claims(
            {
                "user_id": "  " + _U1.upper() + "  ",
                "role": "admin",
            },
        )
        assert c.user_id == _U1

    def test_missing_role_raises(self):
        with pytest.raises(ValueError, match="missing role"):
            resolve_claims({"user_id": _U1})

    def test_empty_role_raises(self):
        with pytest.raises(ValueError, match="missing role"):
            resolve_claims({"user_id": _U1, "role": ""})

    def test_no_org_id_returns_none(self):
        payload = {"user_id": _U1, "role": "admin"}
        c = resolve_claims(payload)
        assert c.organization_id is None

    def test_optional_fields_default_empty(self):
        payload = {"user_id": _U1, "role": "admin"}
        c = resolve_claims(payload)
        assert c.email == ""
        assert c.name == ""


# ── Supabase JWT shape ──────────────────────────────────────────────────────


class TestSupabaseClaims:
    """Supabase JWT: role in app_metadata, user id in sub, name in user_metadata."""

    def test_full_supabase_claims(self):
        payload = {
            "sub": _SB1,
            "email": "bob@example.com",
            "role": "authenticated",
            "app_metadata": {"role": "admin", "organization_id": "org-sb"},
            "user_metadata": {"name": "Bob"},
        }
        c = resolve_claims(payload)
        assert c.user_id == _SB1
        assert c.role == "admin"
        assert c.name == "Bob"
        assert c.email == "bob@example.com"
        assert c.organization_id == "org-sb"

    def test_authenticated_role_ignored(self):
        """Supabase system role 'authenticated' should not be used as the app role."""
        payload = {
            "sub": _SB2,
            "role": "authenticated",
            "app_metadata": {"role": "contractor"},
        }
        c = resolve_claims(payload)
        assert c.role == "contractor"

    def test_top_level_role_fallback(self):
        """If app_metadata.role is absent, use top-level role (unless 'authenticated')."""
        payload = {
            "sub": _SB3,
            "role": "admin",
            "app_metadata": {},
        }
        c = resolve_claims(payload)
        assert c.role == "admin"

    def test_no_role_anywhere_raises(self):
        payload = {
            "sub": _SB4,
            "role": "authenticated",
            "app_metadata": {},
        }
        with pytest.raises(ValueError, match="missing role"):
            resolve_claims(payload)

    def test_missing_sub_raises(self):
        payload = {"role": "authenticated", "app_metadata": {"role": "admin"}}
        with pytest.raises(ValueError, match="missing user id"):
            resolve_claims(payload)

    def test_org_id_from_app_metadata(self):
        payload = {
            "sub": _U1,
            "app_metadata": {
                "role": "admin",
                "organization_id": "org-from-meta",
            },
        }
        c = resolve_claims(payload)
        assert c.organization_id == "org-from-meta"

    def test_org_id_top_level_fallback(self):
        payload = {
            "sub": _U1,
            "app_metadata": {"role": "admin"},
            "organization_id": "org-top",
        }
        c = resolve_claims(payload)
        assert c.organization_id == "org-top"

    def test_no_org_id_returns_none(self):
        payload = {"sub": _U1, "app_metadata": {"role": "admin"}}
        c = resolve_claims(payload)
        assert c.organization_id is None
