"""Tests for GET /api/catalog/skus/by-barcode structured error responses."""


def test_by_barcode_found_returns_product(db, client, auth_headers):
    """Happy path: scanning a known barcode returns the product."""
    resp = client.post(
        "/api/catalog/skus",
        json={
            "name": "Test Pipe",
            "barcode": "042100005264",
            "category_id": "dept-1",
            "price": 10.0,
            "cost": 5.0,
            "quantity": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    product = resp.json()

    resp = client.get("/api/catalog/skus/by-barcode?barcode=042100005264", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == product["id"]
    assert data["barcode"] == "042100005264"


def test_by_barcode_not_found_returns_structured_error(db, client, auth_headers):
    """Scanning a barcode with no matching product returns 404 with code: not_found."""
    resp = client.get("/api/catalog/skus/by-barcode?barcode=HDW-ITM-999999", headers=auth_headers)
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "not_found"
    assert detail["barcode"] == "HDW-ITM-999999"


def test_by_barcode_invalid_upc_check_digit_returns_structured_error(db, client, auth_headers):
    """Scanning a 12-digit UPC with a wrong check digit returns 422 with code: invalid_check_digit."""
    resp = client.get("/api/catalog/skus/by-barcode?barcode=042100005265", headers=auth_headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "invalid_check_digit"
    assert detail["barcode"] == "042100005265"


def test_by_barcode_invalid_ean13_check_digit_returns_structured_error(db, client, auth_headers):
    """Scanning a 13-digit EAN-13 with a wrong check digit returns 422 with code: invalid_check_digit."""
    resp = client.get("/api/catalog/skus/by-barcode?barcode=5901234123458", headers=auth_headers)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "invalid_check_digit"
    assert detail["barcode"] == "5901234123458"


def test_by_barcode_requires_auth(client):
    """Endpoint must reject unauthenticated requests."""
    resp = client.get("/api/catalog/skus/by-barcode?barcode=HDW-ITM-000001")
    assert resp.status_code in (401, 403)
