"""Shared helper functions for E2E tests."""

import uuid


def _unique_suffix() -> str:
    return uuid.uuid4().hex[:8]


def create_product(client, headers, *, dept_id: str, **overrides) -> dict:
    """Create a product via the API. Returns the JSON body.

    Appends a random suffix to the name so SKU slugs and barcodes
    never collide across tests in the session-scoped e2e suite.
    """
    suffix = _unique_suffix()
    base_name = overrides.pop("name", "E2E Test Widget")
    data = {
        "name": f"{base_name} {suffix}",
        "barcode": f"E2E-{suffix}",
        "price": 10.00,
        "cost": 5.00,
        "quantity": 100,
        "min_stock": 5,
        "category_id": dept_id,
        **overrides,
    }
    resp = client.post("/api/beta/catalog/skus", json=data, headers=headers)
    assert resp.status_code == 200, f"Product create failed: {resp.text}"
    return resp.json()


def create_withdrawal(
    client,
    headers,
    product,
    *,
    quantity=5,
    unit=None,
    job_id="JOB-E2E",
    contractor_id="contractor-1",
) -> dict:
    """Create a withdrawal via the API (admin creates for contractor). Returns the JSON body."""
    item = {
        "sku_id": product["id"],
        "sku": product["sku"],
        "name": product["name"],
        "quantity": quantity,
        "unit": unit or product.get("sell_uom", "each"),
        "unit_price": product["price"],
        "cost": product["cost"],
    }
    resp = client.post(
        f"/api/beta/operations/withdrawals/for-contractor?contractor_id={contractor_id}",
        json={
            "items": [item],
            "job_id": job_id,
            "service_address": "100 E2E Test Lane",
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"Withdrawal failed: {resp.text}"
    return resp.json()


def create_po(
    client,
    headers,
    product,
    *,
    quantity=10,
    vendor_name="E2E Vendor",
    purchase_uom=None,
    purchase_pack_qty=None,
) -> dict:
    """Create a purchase order via the API. Returns the PO JSON body.

    Sets ai_parsed=True and suggested_department to bypass LLM enrichment.
    """
    po_item = {
        "name": product["name"],
        "sku_id": product["id"],
        "quantity": quantity,
        "cost": product["cost"],
        "price": product["cost"],
        "base_unit": product.get("base_unit", "box"),
        "sell_uom": product.get("sell_uom", "box"),
        "suggested_department": "HDW",
        "ai_parsed": True,
    }
    if purchase_uom is not None:
        po_item["purchase_uom"] = purchase_uom
    if purchase_pack_qty is not None:
        po_item["purchase_pack_qty"] = purchase_pack_qty
    resp = client.post(
        "/api/beta/purchasing/purchase-orders",
        json={
            "vendor_name": vendor_name,
            "create_vendor_if_missing": True,
            "products": [po_item],
        },
        headers=headers,
    )
    assert resp.status_code == 200, f"PO create failed: {resp.text}"
    return resp.json()


def receive_po(client, headers, po_id: str) -> dict:
    """Mark delivery on all items and then receive them. Returns the receive result."""
    po_resp = client.get(f"/api/beta/purchasing/purchase-orders/{po_id}", headers=headers)
    assert po_resp.status_code == 200
    po = po_resp.json()
    items = po.get("items", [])

    ordered_ids = [i["id"] for i in items if i.get("status") == "ordered"]
    if ordered_ids:
        resp = client.post(
            f"/api/beta/purchasing/purchase-orders/{po_id}/delivery",
            json={"item_ids": ordered_ids},
            headers=headers,
        )
        assert resp.status_code == 200, f"Delivery mark failed: {resp.text}"

    po_resp = client.get(f"/api/beta/purchasing/purchase-orders/{po_id}", headers=headers)
    items = po_resp.json().get("items", [])
    pending_items = [
        {
            "id": i["id"],
            "delivered_qty": i.get("ordered_qty") or i.get("quantity", 0),
        }
        for i in items
        if i.get("status") == "pending"
    ]
    resp = client.post(
        f"/api/beta/purchasing/purchase-orders/{po_id}/receive",
        json={"items": pending_items},
        headers=headers,
    )
    assert resp.status_code == 200, f"PO receive failed: {resp.text}"
    return resp.json()


def open_cycle_count(client, headers, *, scope: str | None = None) -> dict:
    """Open a cycle count session. Returns the count JSON."""
    resp = client.post(
        "/api/beta/inventory/cycle-counts",
        json={"scope": scope},
        headers=headers,
    )
    assert resp.status_code == 201, f"Cycle count open failed: {resp.text}"
    return resp.json()


def update_cycle_count_item(
    client, headers, count_id: str, item_id: str, counted_qty: float
) -> dict:
    """Update a single cycle count item's counted quantity."""
    resp = client.patch(
        f"/api/beta/inventory/cycle-counts/{count_id}/items/{item_id}",
        json={"counted_qty": counted_qty},
        headers=headers,
    )
    assert resp.status_code == 200, f"Cycle count item update failed: {resp.text}"
    return resp.json()


def commit_cycle_count(client, headers, count_id: str) -> dict:
    """Commit a cycle count, applying all variances."""
    resp = client.post(
        f"/api/beta/inventory/cycle-counts/{count_id}/commit",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200, f"Cycle count commit failed: {resp.text}"
    return resp.json()


def create_material_request(client, contractor_headers, product, *, quantity=3) -> dict:
    """Create a material request as a contractor. Returns the request JSON."""
    resp = client.post(
        "/api/beta/operations/material-requests",
        json={
            "items": [
                {
                    "sku_id": product["id"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": quantity,
                    "unit_price": product["price"],
                    "cost": product["cost"],
                }
            ],
        },
        headers=contractor_headers,
    )
    assert resp.status_code == 200, f"Material request create failed: {resp.text}"
    return resp.json()


def process_material_request(
    client,
    admin_headers,
    request_id: str,
    *,
    job_id="JOB-MR",
    service_address="200 MR Lane",
) -> dict:
    """Process a material request as admin (converts to withdrawal)."""
    resp = client.post(
        f"/api/beta/operations/material-requests/{request_id}/process",
        json={"job_id": job_id, "service_address": service_address},
        headers=admin_headers,
    )
    assert resp.status_code == 200, f"Material request process failed: {resp.text}"
    return resp.json()
