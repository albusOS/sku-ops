"""Jobs API - list, search, get, create, update."""
import pytest
from tests.helpers.auth import SEEDED_JOB_ID

class TestJobsList:

    def test_requires_auth(self, client):
        r = client.get('/api/beta/jobs')
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures('_db')
    def test_list_includes_seeded_job(self, client, auth_headers):
        r = client.get('/api/beta/jobs', headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        codes = {j['code'] for j in data}
        assert 'RR-2026-001' in codes

    @pytest.mark.usefixtures('_db')
    def test_list_filter_by_status(self, client, auth_headers):
        r = client.get('/api/beta/jobs', params={'status': 'active'}, headers=auth_headers)
        assert r.status_code == 200
        for row in r.json():
            assert row['status'] == 'active'

    @pytest.mark.usefixtures('_db')
    def test_list_search_by_code(self, client, auth_headers):
        r = client.get('/api/beta/jobs', params={'q': 'RR-2026'}, headers=auth_headers)
        assert r.status_code == 200
        assert any((j['code'] == 'RR-2026-001' for j in r.json()))

class TestJobsSearch:

    def test_requires_auth(self, client):
        r = client.get('/api/beta/jobs/search')
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures('_db')
    def test_contractor_can_search(self, client, contractor_auth_headers):
        r = client.get('/api/beta/jobs/search', params={'q': 'RR'}, headers=contractor_auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.usefixtures('_db')
    def test_empty_query_returns_active_jobs(self, client, contractor_auth_headers):
        r = client.get('/api/beta/jobs/search', headers=contractor_auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all((j.get('status') == 'active' for j in data))

class TestJobsGet:

    def test_requires_auth(self, client):
        r = client.get(f'/api/beta/jobs/{SEEDED_JOB_ID}')
        assert r.status_code in (401, 403)

    @pytest.mark.usefixtures('_db')
    def test_get_by_uuid(self, client, contractor_auth_headers):
        r = client.get(f'/api/beta/jobs/{SEEDED_JOB_ID}', headers=contractor_auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body['id'] == SEEDED_JOB_ID
        assert body['code'] == 'RR-2026-001'

    @pytest.mark.usefixtures('_db')
    def test_get_by_code(self, client, contractor_auth_headers):
        r = client.get('/api/beta/jobs/RR-2026-001', headers=contractor_auth_headers)
        assert r.status_code == 200
        assert r.json()['code'] == 'RR-2026-001'

    @pytest.mark.usefixtures('_db')
    def test_not_found(self, client, auth_headers):
        r = client.get('/api/beta/jobs/019a0000-0000-7000-8000-000000000001', headers=auth_headers)
        assert r.status_code == 404

class TestJobsCreate:

    @pytest.mark.usefixtures('_db')
    def test_requires_code(self, client, auth_headers):
        r = client.post('/api/beta/jobs', headers=auth_headers, json={'name': 'x'})
        assert r.status_code == 422

    @pytest.mark.usefixtures('_db')
    def test_rejects_blank_code(self, client, auth_headers):
        r = client.post('/api/beta/jobs', headers=auth_headers, json={'code': '   ', 'name': 'x'})
        assert r.status_code == 400

    @pytest.mark.usefixtures('_db')
    def test_conflict_duplicate_code(self, client, auth_headers):
        r = client.post('/api/beta/jobs', headers=auth_headers, json={'code': 'RR-2026-001', 'name': 'dup'})
        assert r.status_code == 409

    @pytest.mark.usefixtures('_db')
    def test_create_success(self, client, auth_headers):
        code = f'PYTEST-JOB-{SEEDED_JOB_ID[:8]}'
        r = client.post('/api/beta/jobs', headers=auth_headers, json={'code': code, 'name': 'API test job', 'service_address': '1 Test Ln', 'notes': 'note'})
        assert r.status_code == 200
        body = r.json()
        assert body['code'] == code
        assert body['name'] == 'API test job'
        assert 'id' in body

class TestJobsUpdate:

    @pytest.mark.usefixtures('_db')
    def test_not_found(self, client, auth_headers):
        r = client.put('/api/beta/jobs/019a0000-0000-7000-8000-000000000002', headers=auth_headers, json={'name': 'nope'})
        assert r.status_code == 404

    @pytest.mark.usefixtures('_db')
    def test_invalid_status(self, client, auth_headers):
        r = client.put(f'/api/beta/jobs/{SEEDED_JOB_ID}', headers=auth_headers, json={'status': 'not-a-status'})
        assert r.status_code in (400, 422)

    @pytest.mark.usefixtures('_db')
    def test_update_name_and_status(self, client, auth_headers):
        r = client.put(f'/api/beta/jobs/{SEEDED_JOB_ID}', headers=auth_headers, json={'name': 'Updated pytest job', 'status': 'completed'})
        assert r.status_code == 200
        body = r.json()
        assert body['name'] == 'Updated pytest job'
        assert body['status'] == 'completed'
        r2 = client.put(f'/api/beta/jobs/{SEEDED_JOB_ID}', headers=auth_headers, json={'status': 'active'})
        assert r2.status_code == 200
        assert r2.json()['status'] == 'active'
