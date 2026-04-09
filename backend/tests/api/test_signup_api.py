"""Tests for self-serve signup onboarding HTTP surface."""

from __future__ import annotations

import time

import jwt
import pytest

from shared.application import onboarding_completion
from shared.infrastructure.config import config
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import (
    ONBOARDING_ADMIN_USER_ID,
    admin_headers,
    make_token,
    onboarding_admin_headers,
    onboarding_contractor_headers,
)


@pytest.fixture
def _no_supabase_sync(monkeypatch):
    async def _noop(**_kwargs):
        return None

    monkeypatch.setattr(
        onboarding_completion,
        "sync_supabase_app_metadata_for_onboarding",
        _noop,
    )


@pytest.mark.usefixtures("_no_supabase_sync")
class TestCompleteProfile:
    """POST /api/beta/shared/auth/complete-profile"""

    def test_complete_profile_requires_auth(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            json={"company": "Acme", "phone": "555"},
        )
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_admin_creates_new_org(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_admin_headers(),
            json={
                "phone": "555-0001",
                "organization_name": "Fresh Org From Test",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["needs_onboarding"] is False
        assert data["organization_id"]
        assert data["organization_id"] != ""

    @pytest.mark.usefixtures("_db")
    def test_admin_joins_existing_org(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_admin_headers(),
            json={
                "phone": "555-0001",
                "organization_id": DEFAULT_ORG_ID,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["needs_onboarding"] is False
        assert data["organization_id"] == DEFAULT_ORG_ID

    @pytest.mark.usefixtures("_db")
    def test_contractor_joins_existing_org(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_contractor_headers(),
            json={
                "company": "Contractor Co",
                "phone": "555-0002",
                "organization_id": DEFAULT_ORG_ID,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["needs_onboarding"] is False
        assert data["organization_id"] == DEFAULT_ORG_ID
        assert data.get("billing_entity_id")

    @pytest.mark.usefixtures("_db")
    def test_contractor_rejects_nonexistent_org(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_contractor_headers(),
            json={
                "company": "X",
                "phone": "",
                "organization_id": "0195f2c0-89aa-7d6d-bb34-7f3b3f69c099",
            },
        )
        assert r.status_code == 404

    @pytest.mark.usefixtures("_db")
    def test_complete_profile_rejects_already_onboarded(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=admin_headers(),
            json={"company": "Nope", "phone": "", "organization_name": "Nope Org"},
        )
        assert r.status_code == 409

    @pytest.mark.usefixtures("_db")
    def test_admin_missing_org_field(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_admin_headers(),
            json={"phone": "555"},
        )
        assert r.status_code == 422

    @pytest.mark.usefixtures("_db")
    def test_contractor_missing_company(self, client):
        r = client.post(
            "/api/beta/shared/auth/complete-profile",
            headers=onboarding_contractor_headers(),
            json={"phone": "555", "organization_id": DEFAULT_ORG_ID},
        )
        assert r.status_code == 422


class TestListOrganizations:
    """GET /api/beta/shared/auth/organizations"""

    def test_organizations_requires_auth(self, client):
        r = client.get("/api/beta/shared/auth/organizations")
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_organizations_returns_list(self, client):
        r = client.get("/api/beta/shared/auth/organizations", headers=admin_headers())
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        ids = {o["id"] for o in data}
        assert DEFAULT_ORG_ID in ids

    @pytest.mark.usefixtures("_db")
    def test_organizations_works_without_org_claim(self, client):
        r = client.get(
            "/api/beta/shared/auth/organizations",
            headers=onboarding_contractor_headers(),
        )
        assert r.status_code == 200
        data = r.json()
        assert any(o["id"] == DEFAULT_ORG_ID for o in data)


class TestMeOnboarding:
    """GET /api/beta/shared/auth/me — needs_onboarding flag."""

    @pytest.mark.usefixtures("_db")
    def test_me_needs_onboarding_true_when_no_org(self, client):
        r = client.get("/api/beta/shared/auth/me", headers=onboarding_admin_headers())
        assert r.status_code == 200
        assert r.json()["needs_onboarding"] is True

    @pytest.mark.usefixtures("_db")
    def test_me_needs_onboarding_false_when_org_set(self, client):
        r = client.get("/api/beta/shared/auth/me", headers=admin_headers())
        assert r.status_code == 200
        assert r.json()["needs_onboarding"] is False

    @pytest.mark.usefixtures("_db")
    def test_me_reflects_user_metadata_role_without_app_metadata_role(self, client):
        token = make_token(
            ONBOARDING_ADMIN_USER_ID,
            org_id="",
            role="authenticated",
            name="Onboard Admin",
            email="onboard-admin@test.com",
        )
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        payload["app_metadata"] = {}
        payload["user_metadata"] = {"name": "Onboard Admin", "role": "admin"}
        payload["role"] = "authenticated"
        payload["exp"] = int(time.time()) + 3600
        fixed = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
        r = client.get(
            "/api/beta/shared/auth/me",
            headers={"Authorization": f"Bearer {fixed}"},
        )
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
        assert r.json()["needs_onboarding"] is True
