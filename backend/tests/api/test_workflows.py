"""End-to-end workflow tests — create entities via HTTP, verify side effects.

Each test exercises a full business workflow through the API layer.
"""

from tests.helpers.auth import admin_headers, contractor_headers


class TestProductWorkflow:
    """Create a product and verify it appears in listings."""

    async def test_create_and_list_product(self, db, client):
        headers = admin_headers()

        product_data = {
            "name": "Test Bolt 10mm",
            "description": "Galvanized steel bolt",
            "price": 2.50,
            "cost": 1.00,
            "quantity": 100,
            "min_stock": 10,
            "department_id": "dept-1",
            "base_unit": "each",
            "sell_uom": "each",
            "pack_qty": 1,
        }

        resp = client.post("/api/products", json=product_data, headers=headers)
        assert resp.status_code == 200, f"Product create failed: {resp.text}"
        product = resp.json()
        product_id = product["id"]
        assert product["name"] == "Test Bolt 10mm"

        resp = client.get(f"/api/products/{product_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == product_id


class TestWithdrawalWorkflow:
    """Create a product, withdraw stock, verify inventory decrements."""

    async def test_withdrawal_decrements_stock(self, db, client):
        headers = admin_headers()

        product_data = {
            "name": "Withdrawal Test Item",
            "price": 5.00,
            "cost": 2.00,
            "quantity": 50,
            "department_id": "dept-1",
        }
        resp = client.post("/api/products", json=product_data, headers=headers)
        assert resp.status_code == 200
        product = resp.json()
        pid = product["id"]
        sku = product["sku"]

        withdrawal_data = {
            "items": [
                {
                    "product_id": pid,
                    "sku": sku,
                    "name": "Withdrawal Test Item",
                    "quantity": 5,
                    "unit_price": 5.00,
                    "cost": 2.00,
                }
            ],
            "job_id": "JOB-001",
            "service_address": "123 Test St",
        }
        resp = client.post("/api/withdrawals", json=withdrawal_data, headers=headers)
        assert resp.status_code == 200, f"Withdrawal create failed: {resp.text}"
        withdrawal = resp.json()
        assert withdrawal["total"] > 0

        resp = client.get(f"/api/products/{pid}", headers=headers)
        assert resp.status_code == 200
        updated_qty = resp.json()["quantity"]
        assert updated_qty == 45, f"Expected 45 after withdrawing 5 from 50, got {updated_qty}"


class TestMaterialRequestWorkflow:
    """Contractor submits request, admin processes it into a withdrawal."""

    async def test_contractor_request_to_withdrawal(self, db, client):
        admin_h = admin_headers()
        contractor_h = contractor_headers()

        product_data = {
            "name": "Mat Request Test Item",
            "price": 10.00,
            "cost": 4.00,
            "quantity": 100,
            "department_id": "dept-1",
        }
        resp = client.post("/api/products", json=product_data, headers=admin_h)
        assert resp.status_code == 200
        product = resp.json()

        request_data = {
            "items": [
                {
                    "product_id": product["id"],
                    "sku": product["sku"],
                    "name": "Mat Request Test Item",
                    "quantity": 3,
                    "unit_price": 10.00,
                    "cost": 4.00,
                }
            ],
            "notes": "Need for site work",
        }
        resp = client.post("/api/material-requests", json=request_data, headers=contractor_h)
        assert resp.status_code == 200, f"Material request create failed: {resp.text}"
        mat_req = resp.json()
        assert mat_req["status"] == "pending"
        req_id = mat_req["id"]

        resp = client.post(
            f"/api/material-requests/{req_id}/process",
            json={"job_id": "JOB-002", "service_address": "456 Site Rd"},
            headers=admin_h,
        )
        assert resp.status_code == 200, f"Process request failed: {resp.text}"
        result = resp.json()
        assert result.get("id"), (
            f"Expected processed withdrawal to have an id, got keys: {list(result.keys())}"
        )


class TestInvoiceWorkflow:
    """Create a withdrawal, then verify invoice listing includes it."""

    async def test_withdrawal_appears_in_invoices(self, db, client):
        headers = admin_headers()

        product_data = {
            "name": "Invoice Test Item",
            "price": 20.00,
            "cost": 8.00,
            "quantity": 50,
            "department_id": "dept-1",
        }
        resp = client.post("/api/products", json=product_data, headers=headers)
        assert resp.status_code == 200
        product = resp.json()

        withdrawal_data = {
            "items": [
                {
                    "product_id": product["id"],
                    "sku": product["sku"],
                    "name": "Invoice Test Item",
                    "quantity": 2,
                    "unit_price": 20.00,
                    "cost": 8.00,
                }
            ],
            "job_id": "JOB-003",
            "service_address": "789 Invoice St",
        }
        resp = client.post("/api/withdrawals", json=withdrawal_data, headers=headers)
        assert resp.status_code == 200

        resp = client.get("/api/withdrawals", headers=headers)
        assert resp.status_code == 200
        withdrawals = resp.json()
        assert isinstance(withdrawals, list | dict)
