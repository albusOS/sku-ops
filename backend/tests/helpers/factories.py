"""Shared test factories for creating domain objects."""

from catalog.application.sku_lifecycle import create_product_with_sku
from inventory.application.inventory_service import process_import_stock_changes
from shared.kernel.constants import DEFAULT_ORG_ID
from shared.kernel.types import CurrentUser
from tests.helpers.auth import ADMIN_USER_ID, SEEDED_DEPT_ID


async def make_product(
    name="Test Widget",
    quantity=10.0,
    price=10.0,
    cost=5.0,
    base_unit="each",
    sell_uom=None,
    pack_qty=1,
    category_id=SEEDED_DEPT_ID,
    category_name="Hardware",
    user_id=ADMIN_USER_ID,
    user_name="Test",
    barcode=None,
    on_stock_import=None,
):
    return await create_product_with_sku(
        category_id=category_id,
        category_name=category_name,
        name=name,
        quantity=quantity,
        price=price,
        cost=cost,
        base_unit=base_unit,
        sell_uom=sell_uom or base_unit,
        pack_qty=pack_qty,
        user_id=user_id,
        user_name=user_name,
        barcode=barcode,
        on_stock_import=on_stock_import or process_import_stock_changes,
    )


def make_current_user(user_id=ADMIN_USER_ID, name="Test User", role="admin"):
    return CurrentUser(id=user_id, email="test@test.com", name=name, role=role, organization_id=DEFAULT_ORG_ID)
