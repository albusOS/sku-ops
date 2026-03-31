"""Tests for GET /api/beta/catalog/skus/by-barcode structured error responses."""

from tests.helpers.auth import SEEDED_DEPT_ID


def test_by_barcode_found_returns_product(db, client, auth_headers):
    """Happy path: scanning a known barcode returns the product."""
    create_resp = client.post(
        "/api/beta/catalog/skus",
        json={
            "category_id": SEEDED_DEPT_ID,
            "name": "Test Pipe",
            "barcode": "042100005264",  # valid UPC-A
            "price": 0,
            "cost": 0,
            "quantity": 0,
            "min_stock": 5,
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    sku_id = create_resp.json()["id"]

    resp = client.get(
        "/api/beta/catalog/skus/by-barcode?barcode=042100005264",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sku_id
    assert data["barcode"] == "042100005264"


def test_by_barcode_not_found_returns_structured_error(
    db, client, auth_headers
):
    """Scanning a barcode with no matching product returns 404 with code: not_found."""
    resp = client.get(
        "/api/beta/catalog/skus/by-barcode?barcode=HDW-ITM-999999",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert detail["code"] == "not_found"
    assert detail["barcode"] == "HDW-ITM-999999"


def test_by_barcode_invalid_upc_check_digit_returns_structured_error(
    db, client, auth_headers
):
    """Scanning a 12-digit UPC with a wrong check digit returns 422 with code: invalid_check_digit."""
    # 042100005265 has a bad check digit (valid: 042100005264)
    resp = client.get(
        "/api/beta/catalog/skus/by-barcode?barcode=042100005265",
        headers=auth_headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "invalid_check_digit"
    assert detail["barcode"] == "042100005265"


def test_by_barcode_invalid_ean13_check_digit_returns_structured_error(
    db, client, auth_headers
):
    """Scanning a 13-digit EAN-13 with a wrong check digit returns 422 with code: invalid_check_digit."""
    # 5901234123458 has wrong check digit (valid: 5901234123457)
    resp = client.get(
        "/api/beta/catalog/skus/by-barcode?barcode=5901234123458",
        headers=auth_headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["code"] == "invalid_check_digit"
    assert detail["barcode"] == "5901234123458"


def test_by_barcode_requires_auth(client):
    """Endpoint must reject unauthenticated requests."""
    resp = client.get(
        "/api/beta/catalog/skus/by-barcode?barcode=HDW-ITM-000001"
    )
    assert resp.status_code in (401, 403)
