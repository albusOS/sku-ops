"""Tests for the units of measure CRUD API."""

import uuid

from tests.helpers.auth import SEEDED_DEPT_ID


class TestListUnits:
    def test_returns_seeded_units(self, client, auth_headers):
        resp = client.get("/api/beta/catalog/units", headers=auth_headers)
        assert resp.status_code == 200
        units = resp.json()
        assert isinstance(units, list)
        assert len(units) > 0
        codes = {u["code"] for u in units}
        assert "each" in codes
        assert "roll" in codes
        assert "gallon" in codes

    def test_units_have_expected_fields(self, client, auth_headers):
        resp = client.get("/api/beta/catalog/units", headers=auth_headers)
        unit = resp.json()[0]
        assert "id" in unit
        assert "code" in unit
        assert "name" in unit
        assert "family" in unit

    def test_seeded_families_correct(self, client, auth_headers):
        resp = client.get("/api/beta/catalog/units", headers=auth_headers)
        by_code = {u["code"]: u for u in resp.json()}
        assert by_code["gallon"]["family"] == "volume"
        assert by_code["pound"]["family"] == "weight"
        assert by_code["foot"]["family"] == "length"
        assert by_code["sqft"]["family"] == "area"
        assert by_code["each"]["family"] == "discrete"

    def test_new_units_seeded(self, client, auth_headers):
        """bundle, pallet, slab were added as part of the UOM redesign."""
        resp = client.get("/api/beta/catalog/units", headers=auth_headers)
        codes = {u["code"] for u in resp.json()}
        assert "bundle" in codes
        assert "pallet" in codes
        assert "slab" in codes


class TestCreateUnit:
    def test_create_custom_unit(self, client, auth_headers):
        resp = client.post(
            "/api/beta/catalog/units", json={"code": "pail", "name": "Pail", "family": "discrete"}, headers=auth_headers
        )
        assert resp.status_code == 200
        unit = resp.json()
        assert unit["code"] == "pail"
        assert unit["name"] == "Pail"
        assert unit["family"] == "discrete"
        units = client.get("/api/beta/catalog/units", headers=auth_headers).json()
        assert any(u["code"] == "pail" for u in units)

    def test_duplicate_code_rejected(self, client, auth_headers):
        client.post("/api/beta/catalog/units", json={"code": "tray", "name": "Tray"}, headers=auth_headers)
        resp = client.post("/api/beta/catalog/units", json={"code": "tray", "name": "Tray 2"}, headers=auth_headers)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    def test_code_normalised_to_lowercase(self, client, auth_headers):
        resp = client.post("/api/beta/catalog/units", json={"code": "DRUM", "name": "Drum"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == "drum"

    def test_empty_code_rejected(self, client, auth_headers):
        resp = client.post("/api/beta/catalog/units", json={"code": "", "name": "Empty"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_family_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/beta/catalog/units",
            json={"code": "bucket", "name": "Bucket", "family": "imaginary"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_contractor_cannot_create(self, client, contractor_auth_headers):
        resp = client.post(
            "/api/beta/catalog/units", json={"code": "bucket", "name": "Bucket"}, headers=contractor_auth_headers
        )
        assert resp.status_code == 403


class TestDeleteUnit:
    def test_delete_custom_unit(self, client, auth_headers):
        create = client.post("/api/beta/catalog/units", json={"code": "carton", "name": "Carton"}, headers=auth_headers)
        uom_id = create.json()["id"]
        resp = client.delete(f"/api/beta/catalog/units/{uom_id}", headers=auth_headers)
        assert resp.status_code == 200
        units = client.get("/api/beta/catalog/units", headers=auth_headers).json()
        assert not any(u["id"] == uom_id for u in units)

    def test_delete_nonexistent_returns_404(self, client, auth_headers):
        resp = client.delete(f"/api/beta/catalog/units/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_contractor_cannot_delete(self, client, contractor_auth_headers):
        resp = client.delete("/api/beta/catalog/units/uom-each", headers=contractor_auth_headers)
        assert resp.status_code == 403


class TestSkuAcceptsCustomUnits:
    """After the validation relaxation, SKUs accept any unit string."""

    def test_create_sku_with_custom_unit(self, client, auth_headers):
        resp = client.post(
            "/api/beta/catalog/skus",
            json={
                "name": "Custom Unit Widget",
                "category_id": SEEDED_DEPT_ID,
                "price": 5.0,
                "quantity": 10,
                "base_unit": "pallet",
                "sell_uom": "pallet",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sku = resp.json()
        assert sku["base_unit"] == "pallet"
        assert sku["sell_uom"] == "pallet"

    def test_update_sku_with_custom_unit(self, client, auth_headers):
        create = client.post(
            "/api/beta/catalog/skus",
            json={"name": "Unit Update Widget", "category_id": SEEDED_DEPT_ID, "price": 5.0, "quantity": 10},
            headers=auth_headers,
        )
        sku_id = create.json()["id"]
        resp = client.put(f"/api/beta/catalog/skus/{sku_id}", json={"sell_uom": "slab"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["sell_uom"] == "slab"

    def test_unit_normalised_to_lowercase(self, client, auth_headers):
        resp = client.post(
            "/api/beta/catalog/skus",
            json={
                "name": "Case Widget",
                "category_id": SEEDED_DEPT_ID,
                "price": 5.0,
                "quantity": 10,
                "base_unit": "PALLET",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["base_unit"] == "pallet"


class TestSkuRename:
    """SKU code can be updated via PUT when the user accepts a re-suggestion."""

    def test_rename_sku_code(self, client, auth_headers):
        create = client.post(
            "/api/beta/catalog/skus",
            json={"name": "Rename Widget", "category_id": SEEDED_DEPT_ID, "price": 5.0, "quantity": 10},
            headers=auth_headers,
        )
        assert create.status_code == 200
        sku_id = create.json()["id"]
        old_sku = create.json()["sku"]
        resp = client.put(f"/api/beta/catalog/skus/{sku_id}", json={"sku": "CUSTOM-NEW-01"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["sku"] == "CUSTOM-NEW-01"
        assert resp.json()["sku"] != old_sku
        get_resp = client.get(f"/api/beta/catalog/skus/{sku_id}", headers=auth_headers)
        assert get_resp.json()["sku"] == "CUSTOM-NEW-01"

    def test_rename_to_duplicate_rejected(self, client, auth_headers):
        resp1 = client.post(
            "/api/beta/catalog/skus",
            json={"name": "First Widget", "category_id": SEEDED_DEPT_ID, "price": 5, "quantity": 1},
            headers=auth_headers,
        )
        resp2 = client.post(
            "/api/beta/catalog/skus",
            json={"name": "Second Widget", "category_id": SEEDED_DEPT_ID, "price": 5, "quantity": 1},
            headers=auth_headers,
        )
        first_sku = resp1.json()["sku"]
        second_id = resp2.json()["id"]
        resp = client.put(f"/api/beta/catalog/skus/{second_id}", json={"sku": first_sku}, headers=auth_headers)
        assert resp.status_code == 409
        assert "already used" in resp.json()["detail"].lower()

    def test_rename_to_same_sku_is_noop(self, client, auth_headers):
        create = client.post(
            "/api/beta/catalog/skus",
            json={"name": "Noop Widget", "category_id": SEEDED_DEPT_ID, "price": 5, "quantity": 1},
            headers=auth_headers,
        )
        sku_id = create.json()["id"]
        current_sku = create.json()["sku"]
        resp = client.put(f"/api/beta/catalog/skus/{sku_id}", json={"sku": current_sku}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["sku"] == current_sku

    def test_rename_with_empty_string_is_noop(self, client, auth_headers):
        create = client.post(
            "/api/beta/catalog/skus",
            json={"name": "Empty SKU Widget", "category_id": SEEDED_DEPT_ID, "price": 5, "quantity": 1},
            headers=auth_headers,
        )
        sku_id = create.json()["id"]
        current_sku = create.json()["sku"]
        resp = client.put(f"/api/beta/catalog/skus/{sku_id}", json={"sku": "  "}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["sku"] == current_sku
