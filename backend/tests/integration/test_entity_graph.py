"""Integration tests for entity graph traversal against live Postgres."""

import uuid

from catalog.application.sku_lifecycle import create_product_with_sku
from inventory.application.inventory_service import process_import_stock_changes
from shared.infrastructure.database import get_connection
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import ADMIN_USER_ID, SEEDED_DEPT_ID

VENDOR_ID_1 = "0195f2c0-89af-7000-8000-000000000011"
VENDOR_ITEM_ID_1 = "0195f2c0-89af-7000-8000-000000000012"
VENDOR_ID_2 = "0195f2c0-89af-7000-8000-000000000021"
VENDOR_ITEM_ID_2 = "0195f2c0-89af-7000-8000-000000000022"
VENDOR_ID_FMT = "0195f2c0-89af-7000-8000-000000000031"
VENDOR_ITEM_ID_FMT = "0195f2c0-89af-7000-8000-000000000032"


class TestEntityGraph:
    def test_view_exists(self, call):
        async def _body():
            conn = get_connection()
            cur = await conn.execute(
                "SELECT table_name FROM information_schema.views WHERE table_name = 'entity_edges'"
            )
            row = await cur.fetchone()
            assert row is not None, (
                "entity_edges view should exist after schema bootstrap"
            )

        call(_body)

    def test_sku_to_vendor_traversal(self, call):
        async def _body():
            conn = get_connection()

            # Seed a vendor + sku + vendor_item link
            await conn.execute(
                "INSERT INTO vendors (id, name, contact_name, email, phone, organization_id, created_at) "
                "VALUES ($1, 'Graph Vendor', 'Contact', 'v@test.com', '555', $2, NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ID_1, DEFAULT_ORG_ID),
            )
            await conn.commit()
            sku = await create_product_with_sku(
                category_id=SEEDED_DEPT_ID,
                category_name="Hardware",
                name="Graph Test Bolt",
                quantity=50,
                price=3.00,
                cost=1.50,
                base_unit="each",
                sell_uom="each",
                user_id=ADMIN_USER_ID,
                user_name="Test",
                on_stock_import=process_import_stock_changes,
            )
            await conn.execute(
                "INSERT INTO vendor_items (id, vendor_id, sku_id, vendor_sku, cost, purchase_pack_qty, is_preferred, organization_id, created_at, updated_at) "
                "VALUES ($1, $2, $3, 'VND-BOLT', 1.40, 1, TRUE, $4, NOW(), NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ITEM_ID_1, VENDOR_ID_1, sku.id, DEFAULT_ORG_ID),
            )
            await conn.commit()

            # Reset view cache
            import assistant.application.entity_graph as eg

            eg._view_ok = None

            from assistant.application.entity_graph import neighbors

            ctx = await neighbors("sku", str(sku.id))
            assert ctx is not None, "Should find the SKU"
            assert ctx.center.entity_type == "sku"
            assert "Graph Test Bolt" in ctx.center.label
            assert len(ctx.neighbors) >= 1, (
                "Should have at least the vendor neighbor"
            )

            vendor_neighbors = [
                n for n in ctx.neighbors if n.entity_type == "vendor"
            ]
            assert len(vendor_neighbors) >= 1
            assert any("Graph Vendor" in n.label for n in vendor_neighbors)

            # Check edges
            supplied_by = [e for e in ctx.edges if e.relation == "supplied_by"]
            assert len(supplied_by) >= 1

        call(_body)

    def test_vendor_to_sku_reverse(self, call):
        async def _body():
            conn = get_connection()

            # Seed vendor + sku + link
            await conn.execute(
                "INSERT INTO vendors (id, name, contact_name, email, phone, organization_id, created_at) "
                "VALUES ($1, 'Reverse Vendor', 'C', 'rv@test.com', '555', $2, NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ID_2, DEFAULT_ORG_ID),
            )
            await conn.commit()
            sku = await create_product_with_sku(
                category_id=SEEDED_DEPT_ID,
                category_name="Hardware",
                name="Reverse Test Nut",
                quantity=20,
                price=1.00,
                cost=0.50,
                base_unit="each",
                sell_uom="each",
                user_id=ADMIN_USER_ID,
                user_name="Test",
                on_stock_import=process_import_stock_changes,
            )
            await conn.execute(
                "INSERT INTO vendor_items (id, vendor_id, sku_id, vendor_sku, cost, purchase_pack_qty, is_preferred, organization_id, created_at, updated_at) "
                "VALUES ($1, $2, $3, 'VND-NUT', 0.45, 1, TRUE, $4, NOW(), NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ITEM_ID_2, VENDOR_ID_2, sku.id, DEFAULT_ORG_ID),
            )
            await conn.commit()

            import assistant.application.entity_graph as eg

            eg._view_ok = None
            from assistant.application.entity_graph import neighbors

            ctx = await neighbors("vendor", VENDOR_ID_2)
            assert ctx is not None
            assert ctx.center.entity_type == "vendor"
            assert len(ctx.neighbors) >= 1

            sku_neighbors = [n for n in ctx.neighbors if n.entity_type == "sku"]
            assert len(sku_neighbors) >= 1

        call(_body)

    def test_sku_in_department_edge(self, call):
        async def _body():
            sku = await create_product_with_sku(
                category_id=SEEDED_DEPT_ID,
                category_name="Hardware",
                name="Dept Edge Test",
                quantity=10,
                price=1.00,
                cost=0.50,
                base_unit="each",
                sell_uom="each",
                user_id=ADMIN_USER_ID,
                user_name="Test",
                on_stock_import=process_import_stock_changes,
            )

            import assistant.application.entity_graph as eg

            eg._view_ok = None
            from assistant.application.entity_graph import neighbors

            ctx = await neighbors("sku", str(sku.id))
            assert ctx is not None
            dept_edges = [e for e in ctx.edges if e.relation == "in_department"]
            assert len(dept_edges) >= 1, "SKU should have in_department edge"

        call(_body)

    def test_nonexistent_entity(self, call):
        async def _body():
            import assistant.application.entity_graph as eg

            eg._view_ok = None
            from assistant.application.entity_graph import neighbors

            ctx = await neighbors("sku", str(uuid.uuid4()))
            assert ctx is None

        call(_body)

    def test_format_for_agent(self, call):
        async def _body():
            conn = get_connection()
            await conn.execute(
                "INSERT INTO vendors (id, name, contact_name, email, phone, organization_id, created_at) "
                "VALUES ($1, 'Format Vendor', 'C', 'fmt@test.com', '555', $2, NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ID_FMT, DEFAULT_ORG_ID),
            )
            await conn.commit()
            sku = await create_product_with_sku(
                category_id=SEEDED_DEPT_ID,
                category_name="Hardware",
                name="Format Test Widget",
                quantity=5,
                price=2.00,
                cost=1.00,
                base_unit="each",
                sell_uom="each",
                user_id=ADMIN_USER_ID,
                user_name="Test",
                on_stock_import=process_import_stock_changes,
            )
            await conn.execute(
                "INSERT INTO vendor_items (id, vendor_id, sku_id, vendor_sku, cost, purchase_pack_qty, is_preferred, organization_id, created_at, updated_at) "
                "VALUES ($1, $2, $3, 'VND-FMT', 0.90, 1, TRUE, $4, NOW(), NOW()) "
                "ON CONFLICT DO NOTHING",
                (VENDOR_ITEM_ID_FMT, VENDOR_ID_FMT, sku.id, DEFAULT_ORG_ID),
            )
            await conn.commit()

            import assistant.application.entity_graph as eg

            eg._view_ok = None
            from assistant.application.entity_graph import neighbors

            ctx = await neighbors("sku", str(sku.id))
            assert ctx is not None
            formatted = ctx.format_for_agent()
            assert "[sku]" in formatted
            assert "Format Test Widget" in formatted
            assert "supplied_by:" in formatted

        call(_body)
