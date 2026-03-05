"""Tests for material request creation and processing with fallback logic."""
import pytest

from kernel.types import CurrentUser
from operations.domain.material_request import (
    MaterialRequest,
    MaterialRequestCreate,
    MaterialRequestProcess,
)
from operations.domain.withdrawal import WithdrawalItem
from operations.infrastructure.material_request_repo import material_request_repo
from catalog.application.product_lifecycle import create_product
from inventory.application.inventory_service import process_import_stock_changes


def _admin():
    return CurrentUser(id="user-1", email="test@test.com", name="Test User", role="admin")


def _contractor():
    return CurrentUser(id="contractor-1", email="contractor@test.com", name="Contractor User", role="contractor")


async def _create_test_product(name="Widget", quantity=100.0, cost=5.0, price=10.0):
    return await create_product(
        department_id="dept-1", department_name="Hardware",
        name=name, quantity=quantity, price=price, cost=cost,
        user_id="user-1", user_name="Test",
        on_stock_import=process_import_stock_changes,
    )


async def _create_request_in_db(product, job_id="JOB-001", service_address="123 Main St"):
    """Insert a material request directly into the DB (bypassing API layer)."""
    req = MaterialRequest(
        contractor_id="contractor-1",
        contractor_name="Contractor User",
        items=[WithdrawalItem(
            product_id=product.id, sku=product.sku,
            name=product.name, quantity=3,
            price=10.0, cost=5.0, subtotal=30.0,
        )],
        job_id=job_id,
        service_address=service_address,
        notes="Test request",
    )
    await material_request_repo.insert(req)
    return req


@pytest.mark.asyncio
async def test_material_request_create_model_validation(db):
    """MaterialRequestCreate requires items; job_id/service_address/notes are optional."""
    product = await _create_test_product()
    item = WithdrawalItem(
        product_id=product.id, sku=product.sku,
        name=product.name, quantity=2,
        price=10.0, cost=5.0, subtotal=20.0,
    )

    minimal = MaterialRequestCreate(items=[item])
    assert len(minimal.items) == 1
    assert minimal.job_id is None
    assert minimal.service_address is None
    assert minimal.notes is None

    full = MaterialRequestCreate(
        items=[item], job_id="J-100",
        service_address="789 Pine", notes="Urgent",
    )
    assert full.job_id == "J-100"
    assert full.service_address == "789 Pine"
    assert full.notes == "Urgent"

    with pytest.raises(Exception):
        MaterialRequestCreate()


@pytest.mark.asyncio
async def test_material_request_process_model_allows_empty(db):
    """MaterialRequestProcess should accept empty job_id and service_address."""
    model = MaterialRequestProcess()
    assert model.job_id is None
    assert model.service_address is None

    model_with = MaterialRequestProcess(job_id="J-1", service_address="123 Oak")
    assert model_with.job_id == "J-1"


@pytest.mark.asyncio
async def test_material_request_round_trip(db):
    """Material request persisted and retrieved with correct fields."""
    product = await _create_test_product()
    req = await _create_request_in_db(product)

    fetched = await material_request_repo.get_by_id(req.id)
    assert fetched is not None
    assert fetched["contractor_id"] == "contractor-1"
    assert fetched["job_id"] == "JOB-001"
    assert fetched["service_address"] == "123 Main St"
    assert fetched["status"] == "pending"
    assert len(fetched["items"]) == 1


@pytest.mark.asyncio
async def test_material_request_fallback_fields_preserved(db):
    """When contractor supplies job_id and service_address, they're stored in the request."""
    product = await _create_test_product()
    req = await _create_request_in_db(product, job_id="FALLBACK-JOB", service_address="456 Elm")

    fetched = await material_request_repo.get_by_id(req.id)
    assert fetched["job_id"] == "FALLBACK-JOB"
    assert fetched["service_address"] == "456 Elm"
