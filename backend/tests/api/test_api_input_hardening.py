"""Guardrails for odd client input - must not 500 or bypass auth."""
import pytest
from tests.helpers.auth import SEEDED_JOB_ID

@pytest.mark.usefixtures('_db')
def test_jobs_list_negative_limit_validation_error(client, auth_headers):
    r = client.get('/api/beta/jobs', params={'limit': -1}, headers=auth_headers)
    assert r.status_code == 422

@pytest.mark.usefixtures('_db')
def test_jobs_search_limit_above_max_validation_error(client, auth_headers):
    r = client.get('/api/beta/jobs/search', params={'limit': 999999}, headers=auth_headers)
    assert r.status_code == 422

@pytest.mark.usefixtures('_db')
def test_billing_entity_name_with_sql_fragments_stored_as_literal(client, auth_headers):
    name = "Acme'; DELETE FROM users WHERE '1'='1"
    r = client.post('/api/beta/finance/billing-entities', headers=auth_headers, json={'name': name})
    assert r.status_code == 200
    be_id = r.json()['id']
    r2 = client.get(f'/api/beta/finance/billing-entities/{be_id}', headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()['name'] == name

@pytest.mark.usefixtures('_db')
def test_addresses_line1_unicode_and_whitespace_trimmed(client, auth_headers):
    r = client.post('/api/beta/shared/addresses', headers=auth_headers, json={'line1': '  Café Résumé 日本語  ', 'city': 'Québec'})
    assert r.status_code == 200
    assert '日本語' in r.json()['line1']

@pytest.mark.usefixtures('_db')
def test_job_update_empty_body_succeeds_no_field_changes(client, auth_headers):
    r = client.put(f'/api/beta/jobs/{SEEDED_JOB_ID}', headers=auth_headers, json={})
    assert r.status_code == 200
    assert r.json()['id'] == SEEDED_JOB_ID

@pytest.mark.usefixtures('_db')
def test_reports_product_margins_negative_limit_validation_error(client, auth_headers):
    r = client.get('/api/beta/reports/product-margins', params={'limit': -5}, headers=auth_headers)
    assert r.status_code == 422
