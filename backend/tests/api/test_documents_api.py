"""Documents API - list, get, parse behavior (no LLM)."""
import pytest

from shared.infrastructure.db import sql_execute
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import ADMIN_USER_ID

DOC_FIXTURE_ID = "019d44b8-c100-757a-9d68-a576ca2044c3"

@pytest.fixture
def portal_client(_app_client):
    """Session TestClient for portal.call(DB helpers)."""
    return _app_client

def _seed_one_document(portal_client):

    async def _go():
        await sql_execute("\n            INSERT INTO documents (\n              id, filename, document_type, file_hash, file_size, mime_type,\n              status, uploaded_by_id, organization_id, created_at, updated_at\n            ) VALUES (\n              $1, 'pytest-doc.pdf', 'other', 'abc', 0, 'application/pdf',\n              'parsed', $2, $3, NOW(), NOW()\n            )\n            ", (DOC_FIXTURE_ID, ADMIN_USER_ID, DEFAULT_ORG_ID), read_only=False)
    portal_client.portal.call(_go)

class TestDocumentsListGet:

    def test_list_requires_auth(self, client):
        r = client.get("/api/beta/documents")
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures("_db")
    def test_list_empty_then_seeded(self, client, auth_headers, portal_client):
        r = client.get("/api/beta/documents", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []
        _seed_one_document(portal_client)
        r2 = client.get("/api/beta/documents", headers=auth_headers)
        assert r2.status_code == 200
        data = r2.json()
        assert len(data) == 1
        assert data[0]["id"] == DOC_FIXTURE_ID
        assert data[0]["filename"] == "pytest-doc.pdf"

    @pytest.mark.usefixtures("_db")
    def test_get_by_id(self, client, auth_headers, portal_client):
        _seed_one_document(portal_client)
        r = client.get(f"/api/beta/documents/{DOC_FIXTURE_ID}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["filename"] == "pytest-doc.pdf"

    @pytest.mark.usefixtures("_db")
    def test_get_not_found(self, client, auth_headers):
        r = client.get("/api/beta/documents/019a0000-0000-7000-8000-000000000099", headers=auth_headers)
        assert r.status_code == 404

class TestDocumentsParse:

    @pytest.mark.usefixtures("_db")
    def test_parse_default_returns_501_without_ocr(self, client, auth_headers):
        r = client.post("/api/beta/documents/parse", headers=auth_headers, files={"file": ("x.txt", b"hello", "text/plain")})
        assert r.status_code == 501

    @pytest.mark.usefixtures("_db")
    def test_parse_use_ai_true_without_key_returns_503(self, client, auth_headers):
        r = client.post("/api/beta/documents/parse?use_ai=true", headers=auth_headers, files={"file": ("x.txt", b"hello", "text/plain")})
        assert r.status_code in (503, 500)

class TestDocumentsContractorBlocked:

    @pytest.mark.usefixtures("_db")
    def test_contractor_cannot_list(self, client, contractor_auth_headers):
        r = client.get("/api/beta/documents", headers=contractor_auth_headers)
        assert r.status_code == 403
