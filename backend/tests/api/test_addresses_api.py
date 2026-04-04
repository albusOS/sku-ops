"""Shared addresses API - list, search, get, create."""
import time
import pytest

def _uniq_line1() -> str:
    return f'{time.time_ns()} Pytest Addr Ln'

class TestAddressesAuth:

    def test_list_requires_auth(self, client):
        r = client.get('/api/beta/shared/addresses')
        assert r.status_code in (401, 403)

    def test_create_requires_auth(self, client):
        r = client.post('/api/beta/shared/addresses', json={'line1': '1 Main St'})
        assert r.status_code in (401, 403)

class TestAddressesCrud:

    @pytest.mark.usefixtures('_db')
    def test_list_empty_ok(self, client, auth_headers):
        r = client.get('/api/beta/shared/addresses', headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.usefixtures('_db')
    def test_create_rejects_blank_line1(self, client, auth_headers):
        r = client.post('/api/beta/shared/addresses', headers=auth_headers, json={'line1': '   '})
        assert r.status_code == 400

    @pytest.mark.usefixtures('_db')
    def test_create_list_get_search(self, client, auth_headers):
        line1 = _uniq_line1()
        r = client.post('/api/beta/shared/addresses', headers=auth_headers, json={'label': 'Yard', 'line1': line1, 'city': 'Denver', 'state': 'CO', 'postal_code': '80202'})
        assert r.status_code == 200
        created = r.json()
        aid = created['id']
        assert created['line1'] == line1
        r2 = client.get(f'/api/beta/shared/addresses/{aid}', headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()['line1'] == line1
        r3 = client.get('/api/beta/shared/addresses', headers=auth_headers)
        assert r3.status_code == 200
        assert any((a['id'] == aid for a in r3.json()))

    @pytest.mark.usefixtures('_db')
    def test_get_not_found(self, client, auth_headers):
        r = client.get('/api/beta/shared/addresses/019a0000-0000-7000-8000-000000000088', headers=auth_headers)
        assert r.status_code == 404

class TestAddressesSearch:

    @pytest.mark.usefixtures('_db')
    def test_contractor_can_search(self, client, contractor_auth_headers):
        r = client.get('/api/beta/shared/addresses/search', params={'q': 'Main'}, headers=contractor_auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.usefixtures('_db')
    def test_contractor_search_empty_query(self, client, contractor_auth_headers):
        r = client.get('/api/beta/shared/addresses/search', headers=contractor_auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
