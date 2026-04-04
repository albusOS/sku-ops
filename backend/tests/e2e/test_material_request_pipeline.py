"""E2E: Material request pipeline — contractor creates, admin processes into withdrawal.

Verifies: contractor can create requests, admin processes into withdrawal,
stock reduced, WS events, role guards enforced.
"""
import pytest

from tests.e2e.helpers import (
    create_material_request,
    create_product,
    e2e_job_id,
    process_material_request,
)
from tests.helpers.auth import CONTRACTOR_USER_ID, SEEDED_JOB_ID, admin_headers, contractor_headers


@pytest.mark.timeout(30)
class TestMaterialRequestPipeline:
    """Full material request lifecycle through the live HTTP API."""

    def test_create_and_process_material_request(self, client, ws_events, seed_dept_id, seed_contractor_id):
        headers = admin_headers()
        c_headers = contractor_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="MR-Pipeline")
        ws_events.clear()
        mr = create_material_request(client, c_headers, product, quantity=5)
        assert mr.get("status") == "pending"
        assert mr.get("contractor_id") == CONTRACTOR_USER_ID
        ws_mr_created = ws_events.wait_for("material_request.created", timeout=3)
        assert ws_mr_created is not None, "material_request.created not received"
        ws_events.clear()
        mr_id = mr["id"]
        withdrawal = process_material_request(client, headers, mr_id)
        assert withdrawal.get("id")
        resp = client.get(f"/api/beta/operations/material-requests/{mr_id}", headers=headers)
        assert resp.status_code == 200
        updated_mr = resp.json()
        assert updated_mr["status"] == "processed"
        assert updated_mr["withdrawal_id"] == withdrawal["id"]
        resp = client.get(f"/api/beta/catalog/skus/{product['id']}", headers=headers)
        assert resp.json()["quantity"] == 45
        ws_mr_processed = ws_events.wait_for("material_request.processed", timeout=3)
        assert ws_mr_processed is not None, "material_request.processed not received"

    def test_contractor_cannot_process(self, client, seed_dept_id, seed_contractor_id):
        """Contractor role should not be allowed to process a request."""
        headers = admin_headers()
        c_headers = contractor_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="MR-RoleGuard")
        mr = create_material_request(client, c_headers, product, quantity=2)
        resp = client.post(f"/api/beta/operations/material-requests/{mr['id']}/process", json={"job_id": SEEDED_JOB_ID, "service_address": "Fail St"}, headers=c_headers)
        assert resp.status_code in (401, 403), f"Contractor should not be able to process, got {resp.status_code}"

    def test_admin_cannot_create_as_contractor(self, client, seed_dept_id):
        """Admin role should not be allowed to create material requests."""
        headers = admin_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="MR-AdminGuard")
        resp = client.post("/api/beta/operations/material-requests", json={"items": [{"sku_id": product["id"], "sku": product["sku"], "name": product["name"], "quantity": 1, "unit_price": product["price"], "cost": product["cost"]}]}, headers=headers)
        assert resp.status_code in (400, 403), f"Admin should not create material requests, got {resp.status_code}"

    def test_double_process_rejected(self, client, seed_dept_id, seed_contractor_id):
        """Cannot process the same material request twice."""
        headers = admin_headers()
        c_headers = contractor_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="MR-DoubleProcess")
        mr = create_material_request(client, c_headers, product, quantity=2)
        process_material_request(client, headers, mr["id"])
        resp = client.post(f"/api/beta/operations/material-requests/{mr['id']}/process", json={"job_id": e2e_job_id("DOUBLE"), "service_address": "Double St"}, headers=headers)
        assert resp.status_code == 400, "Double process should be rejected"

    def test_material_requests_listed(self, client, seed_dept_id, seed_contractor_id):
        """Contractor's own requests appear in GET /api/beta/operations/material-requests."""
        headers = admin_headers()
        c_headers = contractor_headers()
        product = create_product(client, headers, dept_id=seed_dept_id, quantity=50, name="MR-List")
        mr = create_material_request(client, c_headers, product, quantity=1)
        resp = client.get("/api/beta/operations/material-requests", headers=c_headers)
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert mr["id"] in ids
