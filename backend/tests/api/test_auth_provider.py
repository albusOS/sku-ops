"""Tests for JWT claim resolution — both internal and Supabase JWT shapes.

Validates that resolve_claims() correctly extracts user_id, role, email,
name, and organization_id from both token formats, and rejects malformed
tokens with clear errors.
"""

import pytest

from shared.api.auth_provider import ResolvedClaims, resolve_claims

# ── Internal (dev/test) JWT shape ────────────────────────────────────────────


class TestInternalClaims:
    """Internal JWT: flat top-level claims (user_id, role, name, email)."""

    def test_full_claims(self):
        payload = {
            "user_id": "u-1",
            "role": "admin",
            "name": "Alice",
            "email": "alice@test.com",
            "organization_id": "org-1",
        }
        c = resolve_claims(payload)
        assert c == ResolvedClaims(
            user_id="u-1",
            email="alice@test.com",
            name="Alice",
            role="admin",
            organization_id="org-1",
        )

    def test_sub_fallback_for_user_id(self):
        """user_id missing → falls back to sub."""
        payload = {"sub": "u-2", "role": "contractor"}
        c = resolve_claims(payload)
        assert c.user_id == "u-2"

    def test_missing_user_id_raises(self):
        with pytest.raises(ValueError, match="missing user id"):
            resolve_claims({"role": "admin"})

    def test_missing_role_raises(self):
        with pytest.raises(ValueError, match="missing role"):
            resolve_claims({"user_id": "u-1"})

    def test_empty_role_raises(self):
        with pytest.raises(ValueError, match="missing role"):
            resolve_claims({"user_id": "u-1", "role": ""})

    def test_no_org_id_returns_none(self):
        payload = {"user_id": "u-1", "role": "admin"}
        c = resolve_claims(payload)
        assert c.organization_id is None

    def test_optional_fields_default_empty(self):
        payload = {"user_id": "u-1", "role": "admin"}
        c = resolve_claims(payload)
        assert c.email == ""
        assert c.name == ""


# ── Supabase JWT shape ──────────────────────────────────────────────────────


class TestSupabaseClaims:
    """Supabase JWT: role in app_metadata, user id in sub, name in user_metadata."""

    @pytest.fixture(autouse=True)
    def _force_production(self, monkeypatch):
        monkeypatch.setattr("shared.api.auth_provider.is_production", True)

    def test_full_supabase_claims(self):
        payload = {
            "sub": "sb-user-1",
            "email": "bob@example.com",
            "role": "authenticated",
            "app_metadata": {"role": "admin", "organization_id": "org-sb"},
            "user_metadata": {"name": "Bob"},
        }
        c = resolve_claims(payload)
        assert c.user_id == "sb-user-1"
        assert c.role == "admin"
        assert c.name == "Bob"
        assert c.email == "bob@example.com"
        assert c.organization_id == "org-sb"

    def test_authenticated_role_ignored(self):
        """Supabase system role 'authenticated' should not be used as the app role."""
        payload = {
            "sub": "sb-user-2",
            "role": "authenticated",
            "app_metadata": {"role": "contractor"},
        }
        c = resolve_claims(payload)
        assert c.role == "contractor"

    def test_top_level_role_fallback(self):
        """If app_metadata.role is absent, use top-level role (unless 'authenticated')."""
        payload = {
            "sub": "sb-user-3",
            "role": "admin",
            "app_metadata": {},
        }
        c = resolve_claims(payload)
        assert c.role == "admin"

    def test_no_role_anywhere_raises(self):
        payload = {
            "sub": "sb-user-4",
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
            "sub": "u-1",
            "app_metadata": {"role": "admin", "organization_id": "org-from-meta"},
        }
        c = resolve_claims(payload)
        assert c.organization_id == "org-from-meta"

    def test_org_id_top_level_fallback(self):
        payload = {
            "sub": "u-1",
            "app_metadata": {"role": "admin"},
            "organization_id": "org-top",
        }
        c = resolve_claims(payload)
        assert c.organization_id == "org-top"

    def test_no_org_id_returns_none(self):
        payload = {"sub": "u-1", "app_metadata": {"role": "admin"}}
        c = resolve_claims(payload)
        assert c.organization_id is None
