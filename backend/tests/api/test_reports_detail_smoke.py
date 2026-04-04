"""Smoke coverage for report endpoints beyond /sales (ledger-backed aggregations)."""
import pytest
REPORT_PATHS = ['/api/beta/reports/trends', '/api/beta/reports/product-margins', '/api/beta/reports/job-pl', '/api/beta/reports/ar-aging', '/api/beta/reports/kpis', '/api/beta/reports/product-performance', '/api/beta/reports/reorder-urgency', '/api/beta/reports/product-activity']

@pytest.mark.parametrize('path', REPORT_PATHS, ids=[p.split('/')[-1] for p in REPORT_PATHS])
@pytest.mark.usefixtures('_db')
def test_report_endpoint_returns_json(client, auth_headers, path):
    r = client.get(path, headers=auth_headers)
    assert r.status_code == 200, f'{path} -> {r.status_code}: {r.text[:500]}'
    body = r.json()
    assert body is not None
    assert isinstance(body, (dict, list))
