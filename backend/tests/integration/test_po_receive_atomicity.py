"""Tests for PO receive atomicity, UOM conversion, and WAC with pack_qty.

These tests target bugs that would silently corrupt stock, costs, or ledger
entries without producing any visible error at the API layer.
"""

from unittest.mock import AsyncMock, patch

import pytest

from catalog.application.sku_lifecycle import create_product_with_sku
from catalog.domain.sku import SkuUpdate
from catalog.domain.vendor import Vendor
from inventory.application.inventory_service import (
    process_import_stock_changes,
    process_receiving_stock_changes,
)
from purchasing.application.purchase_order_service import (
    PurchasingDeps,
    receive_po_items,
)
from purchasing.domain.purchase_order import (
    POItemStatus,
    POStatus,
    PurchaseOrder,
    PurchaseOrderItem,
    ReceiveItemUpdate,
)
from shared.infrastructure.db import transaction
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.constants import DEFAULT_ORG_ID
from shared.kernel.types import CurrentUser
from tests.helpers.auth import ADMIN_USER_ID, SEEDED_DEPT_ID


def _user():
    return CurrentUser(
        id=ADMIN_USER_ID,
        email="test@test.com",
        name="Test User",
        role="admin",
        organization_id=DEFAULT_ORG_ID,
    )


async def _create_test_product(
    name="Widget",
    quantity=100.0,
    cost=8.0,
    price=10.0,
    dept_id=SEEDED_DEPT_ID,
    base_unit="each",
    purchase_uom="each",
    purchase_pack_qty=1,
):
    return await create_product_with_sku(
        category_id=dept_id,
        category_name="Hardware",
        name=name,
        quantity=quantity,
        price=price,
        cost=cost,
        user_id=ADMIN_USER_ID,
        user_name="Test",
        base_unit=base_unit,
        purchase_uom=purchase_uom,
        purchase_pack_qty=purchase_pack_qty,
        on_stock_import=process_import_stock_changes,
    )


async def _create_po_with_item(
    sku_id=None,
    cost=None,
    unit_price=10.0,
    ordered_qty=50.0,
    name="Widget",
    status=POItemStatus.PENDING,
    purchase_uom="each",
    purchase_pack_qty=1,
):
    from shared.infrastructure.db import sql_execute

    await sql_execute(
        """INSERT INTO vendors (id, name, organization_id, created_at)
           VALUES ($1, $2, $3, NOW())
           ON CONFLICT (id) DO NOTHING""",
        ("0195f2c0-89af-7000-8000-000000000051", "Acme Corp", DEFAULT_ORG_ID),
    )
    po = PurchaseOrder(
        vendor_id="0195f2c0-89af-7000-8000-000000000051",
        vendor_name="Acme Corp",
        status=POStatus.ORDERED,
        created_by_id=ADMIN_USER_ID,
        created_by_name="Test",
        organization_id=DEFAULT_ORG_ID,
    )
    await get_database_manager().purchasing.insert_po(DEFAULT_ORG_ID, po)

    item = PurchaseOrderItem(
        po_id=po.id,
        name=name,
        ordered_qty=ordered_qty,
        delivered_qty=0,
        unit_price=unit_price,
        cost=cost or 0,
        base_unit="each",
        sell_uom="each",
        pack_qty=1,
        purchase_uom=purchase_uom,
        purchase_pack_qty=purchase_pack_qty,
        suggested_department="HDW",
        status=status,
        sku_id=sku_id,
        organization_id=DEFAULT_ORG_ID,
    )
    await get_database_manager().purchasing.insert_po_items(
        DEFAULT_ORG_ID, [item]
    )
    return po, item


def _stub_deps(**overrides):

    async def _list_departments():
        return await get_database_manager().catalog.list_departments(
            DEFAULT_ORG_ID
        )

    async def _get_department_by_code(code: str):
        return await get_database_manager().catalog.get_department_by_code(
            code, DEFAULT_ORG_ID
        )

    async def _find_vendor_by_name(name: str):
        return await get_database_manager().catalog.find_vendor_by_name(
            DEFAULT_ORG_ID, name
        )

    async def _get_sku_by_id(sku_id: str):
        return await get_database_manager().catalog.get_sku_by_id(
            sku_id, DEFAULT_ORG_ID
        )

    async def _find_vendor_item(vendor_id: str, vendor_sku: str):
        return await get_database_manager().catalog.find_vendor_item_by_vendor_and_sku(
            DEFAULT_ORG_ID, vendor_id, vendor_sku
        )

    async def _find_sku_by_name_and_vendor(name: str, vendor_id: str):
        return await get_database_manager().catalog.find_sku_by_name_and_vendor(
            DEFAULT_ORG_ID, name, vendor_id
        )

    async def _update_sku(sku_id: str, updates: SkuUpdate):
        async with transaction():
            return await get_database_manager().catalog.update_sku(
                sku_id,
                DEFAULT_ORG_ID,
                updates.model_dump(exclude_none=True),
            )

    async def _noop_create(**kw):
        return await create_product_with_sku(
            **kw, on_stock_import=process_receiving_stock_changes
        )

    async def _add_vendor_item(**kw):
        return await get_database_manager().catalog.add_vendor_item(
            DEFAULT_ORG_ID, **kw
        )

    async def _insert_vendor(vendor: Vendor | dict) -> None:
        v = (
            Vendor.model_validate(vendor)
            if isinstance(vendor, dict)
            else vendor
        )
        async with transaction():
            await get_database_manager().catalog.insert_vendor(v)

    defaults = {
        "list_departments": _list_departments,
        "get_department_by_code": _get_department_by_code,
        "find_vendor_by_name": _find_vendor_by_name,
        "insert_vendor": _insert_vendor,
        "get_sku_by_id": _get_sku_by_id,
        "find_vendor_item_by_vendor_and_sku_code": _find_vendor_item,
        "find_sku_by_name_and_vendor": _find_sku_by_name_and_vendor,
        "update_sku": _update_sku,
        "create_product_with_sku": _noop_create,
        "add_vendor_item": _add_vendor_item,
        "process_receiving_stock_changes": process_receiving_stock_changes,
    }
    defaults.update(overrides)
    return PurchasingDeps(**defaults)


# ── Atomicity: stock + ledger + PO item stay consistent ──────────────────────


def test_po_receive_rolls_back_stock_on_ledger_failure(call):
    """If ledger recording raises, stock must NOT have increased."""
    with patch(
        "purchasing.application.po_receiving_service._record_po_receipt_ledger",
        side_effect=RuntimeError("Simulated ledger failure"),
    ):

        async def _body():
            product = await _create_test_product(quantity=100.0)
            po, item = await _create_po_with_item(
                sku_id=product.id, cost=7.0, ordered_qty=50
            )

            with pytest.raises(RuntimeError, match="Simulated ledger failure"):
                await receive_po_items(
                    po_id=po.id,
                    item_updates=[
                        ReceiveItemUpdate(id=item.id, delivered_qty=50)
                    ],
                    deps=_stub_deps(),
                    current_user=_user(),
                )

            updated = await get_database_manager().catalog.get_sku_by_id(
                product.id, DEFAULT_ORG_ID
            )
            assert updated.quantity == pytest.approx(100.0), (
                "Stock should NOT have increased"
            )

            po_items = await get_database_manager().purchasing.get_po_items(
                DEFAULT_ORG_ID, po.id
            )
            assert po_items[0].status == POItemStatus.PENDING.value, (
                "PO item should still be PENDING"
            )

        call(_body)


def test_po_receive_vendor_item_failure_reports_error_item_stays_pending(call):
    """If add_vendor_item raises, the item error is reported and the PO item stays pending.

    The original_sku must be set on the PO item (not via ReceiveItemUpdate which
    doesn't carry that field) so that the vendor_item branch is reached.
    """

    async def _body():
        from shared.infrastructure.db import sql_execute

        await sql_execute(
            """INSERT INTO vendors (id, name, organization_id, created_at)
               VALUES ($1, $2, $3, NOW())
               ON CONFLICT (id) DO NOTHING""",
            (
                "0195f2c0-89af-7000-8000-000000000052",
                "Acme Corp",
                DEFAULT_ORG_ID,
            ),
        )
        po = PurchaseOrder(
            vendor_id="0195f2c0-89af-7000-8000-000000000052",
            vendor_name="Acme Corp",
            status=POStatus.ORDERED,
            created_by_id=ADMIN_USER_ID,
            created_by_name="Test",
            organization_id=DEFAULT_ORG_ID,
        )
        await get_database_manager().purchasing.insert_po(DEFAULT_ORG_ID, po)
        item = PurchaseOrderItem(
            po_id=po.id,
            name="Atomicity Widget",
            original_sku="VENDOR-SKU-123",
            ordered_qty=10,
            delivered_qty=0,
            unit_price=10.0,
            cost=5.0,
            base_unit="each",
            sell_uom="each",
            pack_qty=1,
            suggested_department="HDW",
            status=POItemStatus.PENDING,
            sku_id=None,
            organization_id=DEFAULT_ORG_ID,
        )
        await get_database_manager().purchasing.insert_po_items(
            DEFAULT_ORG_ID, [item]
        )

        failing_add = AsyncMock(
            side_effect=RuntimeError("Simulated vendor item failure")
        )
        deps = _stub_deps(add_vendor_item=failing_add)

        result = await receive_po_items(
            po_id=po.id,
            item_updates=[
                ReceiveItemUpdate(
                    id=item.id,
                    delivered_qty=10,
                    suggested_department="HDW",
                )
            ],
            deps=deps,
            current_user=_user(),
        )

        assert result.errors == 1, (
            "Error should be reported for the failed item"
        )

        po_items = await get_database_manager().purchasing.get_po_items(
            DEFAULT_ORG_ID, po.id
        )
        assert po_items[0].status != POItemStatus.ARRIVED.value, (
            "PO item should NOT be ARRIVED when add_vendor_item failed"
        )

    call(_body)


# ── UOM conversion: case/each with purchase_pack_qty ─────────────────────────


def test_po_receive_case_uom_converts_to_base_units(call):
    """Receiving 5 cases with purchase_pack_qty=12 should add 60 each to stock."""

    async def _body():
        product = await _create_test_product(
            quantity=100.0,
            cost=1.0,
            purchase_uom="case",
            purchase_pack_qty=12,
        )
        po, item = await _create_po_with_item(
            sku_id=product.id,
            cost=24.0,
            ordered_qty=5,
            purchase_uom="case",
            purchase_pack_qty=12,
        )

        result = await receive_po_items(
            po_id=po.id,
            item_updates=[ReceiveItemUpdate(id=item.id, delivered_qty=5)],
            deps=_stub_deps(),
            current_user=_user(),
        )

        assert result.errors == 0
        updated = await get_database_manager().catalog.get_sku_by_id(
            product.id, DEFAULT_ORG_ID
        )
        assert updated.quantity == pytest.approx(160.0), (
            f"Expected 100 + 60, got {updated.quantity}"
        )

    call(_body)


def test_po_receive_wac_correct_with_uom_conversion(call):
    """WAC must use per-base-unit cost, not per-case cost.

    Existing: qty=100, cost=$1/each
    Receive: 5 cases @ $24/case (12 per case) = 60 each @ $2/each
    Expected WAC: (100*1 + 60*2) / 160 = 220/160 = 1.375
    """

    async def _body():
        product = await _create_test_product(
            quantity=100.0,
            cost=1.0,
            purchase_uom="case",
            purchase_pack_qty=12,
        )
        po, item = await _create_po_with_item(
            sku_id=product.id,
            cost=24.0,
            ordered_qty=5,
            purchase_uom="case",
            purchase_pack_qty=12,
        )

        await receive_po_items(
            po_id=po.id,
            item_updates=[ReceiveItemUpdate(id=item.id, delivered_qty=5)],
            deps=_stub_deps(),
            current_user=_user(),
        )

        updated = await get_database_manager().catalog.get_sku_by_id(
            product.id, DEFAULT_ORG_ID
        )
        expected_wac = round((100 * 1 + 60 * 2) / 160, 4)
        assert updated.cost == pytest.approx(expected_wac, abs=0.01), (
            f"Expected WAC {expected_wac}, got {updated.cost}"
        )

    call(_body)


def test_po_receive_same_uom_no_multiplication(call):
    """When purchase_uom == base_unit, no pack_qty multiplication should happen."""

    async def _body():
        product = await _create_test_product(quantity=50.0, cost=5.0)
        po, item = await _create_po_with_item(
            sku_id=product.id, cost=6.0, ordered_qty=20
        )

        await receive_po_items(
            po_id=po.id,
            item_updates=[ReceiveItemUpdate(id=item.id, delivered_qty=20)],
            deps=_stub_deps(),
            current_user=_user(),
        )

        updated = await get_database_manager().catalog.get_sku_by_id(
            product.id, DEFAULT_ORG_ID
        )
        assert updated.quantity == pytest.approx(70.0), (
            "Stock should be 50 + 20"
        )

    call(_body)
