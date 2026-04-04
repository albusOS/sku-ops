"""Auth endpoint tests — Supabase-only auth plus backend profile hydration."""
import time
import jwt
import pytest
from shared.infrastructure.config import JWT_ALGORITHM, JWT_SECRET

class TestMe:
    """GET /api/beta/shared/auth/me"""

    def test_me_requires_auth(self, client):
        r = client.get('/api/beta/shared/auth/me')
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures('_db')
    def test_me_returns_user_profile(self, client, auth_headers):
        r = client.get('/api/beta/shared/auth/me', headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data['email'] == 'admin@supplyyard.com'
        assert data['role'] == 'admin'
        assert 'password' not in data

    def test_me_with_invalid_token_returns_401(self, client):
        r = client.get('/api/beta/shared/auth/me', headers={'Authorization': 'Bearer invalid.token'})
        assert r.status_code == 401

    def test_me_rejects_non_uuid_sub_claim(self, client):
        """Invalid JWT sub must 401, not 500 (asyncpg UUID bind fails otherwise)."""
        token = jwt.encode({'sub': 'legacy-text-user-id', 'email': 'x@test.com', 'role': 'authenticated', 'app_metadata': {'role': 'admin', 'organization_id': '0195f2c0-89aa-7d6d-bb34-7f3b3f69c001'}, 'user_metadata': {'name': 'X'}, 'exp': int(time.time()) + 3600}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        r = client.get('/api/beta/shared/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 401
        assert 'Invalid token' in (r.json().get('detail') or '')

class TestSupabaseOnlyAuthSurface:
    """The backend should no longer expose credential auth endpoints."""

    def test_login_endpoint_not_mounted(self, client):
        r = client.post('/api/beta/shared/auth/login', json={'email': 'nobody@nowhere.com', 'password': 'x'})
        assert r.status_code == 404

    def test_register_endpoint_not_mounted(self, client):
        r = client.post('/api/beta/shared/auth/register', json={'email': 'new@test.com', 'password': 'pass123', 'name': 'New User'})
        assert r.status_code == 404

    def test_refresh_endpoint_not_mounted(self, client):
        r = client.post('/api/beta/shared/auth/refresh', headers={'Authorization': 'Bearer anything'})
        assert r.status_code == 404
