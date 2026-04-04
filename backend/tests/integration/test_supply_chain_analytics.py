"""Integration tests for supply chain analytics: demand normalization,
vendor lead time, carrying cost, and smart reorder points.

Each test seeds its own data via raw SQL to stay self-contained. The `call`
fixture from conftest.py runs everything inside the ASGI event loop with
org context pre-set.
"""

import uuid

from shared.infrastructure.db import get_org_id, sql_execute
from shared.infrastructure.db.base import get_database_manager
from shared.kernel.constants import DEFAULT_ORG_ID
from tests.helpers.auth import ADMIN_USER_ID, SEEDED_DEPT_ID, SEEDED_VENDOR_ID


async def _seed_sku(
    sku_id: str = "0195f2c0-89af-7000-8000-000000000101",
    sku_code: str = "HDW-TEST-01",
    name: str = "Test Widget",
    quantity: float = 50.0,
    cost: float = 10.0,
    price: float = 15.0,
    min_stock: int = 10,
    dept_id: str = SEEDED_DEPT_ID,
):
    pf_id = str(uuid.uuid4())
    await sql_execute(
        "INSERT INTO products\n           (id, name, category_id, category_name, organization_id, created_at, updated_at)\n           VALUES ($1, $2, $3, 'Hardware', $4, NOW(), NOW())\n           ON CONFLICT (id) DO NOTHING",
        (pf_id, name, dept_id, DEFAULT_ORG_ID),
    )
    await sql_execute(
        "INSERT INTO skus\n           (id, sku, product_family_id, name, quantity, cost, price, min_stock,\n            category_id, category_name,\n            base_unit, sell_uom, pack_qty, purchase_uom, purchase_pack_qty,\n            organization_id, created_at, updated_at)\n           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'Hardware','each','each',1,'each',1,$10,NOW(),NOW())\n           ON CONFLICT (id) DO UPDATE SET quantity=EXCLUDED.quantity, cost=EXCLUDED.cost",
        (sku_id, sku_code, pf_id, name, quantity, cost, price, min_stock, dept_id, DEFAULT_ORG_ID),
    )
    return sku_id


async def _seed_withdrawal_txns(sku_id: str, daily_qtys: list[float], start_days_ago: int = 30):
    """Seed stock_transactions (WITHDRAWAL type) over consecutive days."""
    for i, qty in enumerate(daily_qtys):
        if qty <= 0:
            continue
        await sql_execute(
            "INSERT INTO stock_transactions\n               (id, sku_id, sku, product_name, quantity_delta,\n                quantity_before, quantity_after, unit,\n                transaction_type, reference_type, reference_id,\n                user_id, user_name, organization_id, created_at)\n               VALUES (gen_random_uuid(), $1, 'HDW-TEST-01', 'Test Widget', $2,\n                       50, 50, 'each',\n                       'WITHDRAWAL', 'withdrawal', gen_random_uuid(),\n                       $4, 'Test', $5,\n                       NOW() - make_interval(days => $3))",
            (sku_id, -qty, start_days_ago - i, ADMIN_USER_ID, DEFAULT_ORG_ID),
        )


async def _seed_receiving_txn(sku_id: str, qty: float, days_ago: int = 10):
    await sql_execute(
        "INSERT INTO stock_transactions\n           (id, sku_id, sku, product_name, quantity_delta,\n            quantity_before, quantity_after, unit,\n            transaction_type, reference_type, reference_id,\n            user_id, user_name, organization_id, created_at)\n           VALUES (gen_random_uuid(), $1, 'HDW-TEST-01', 'Test Widget', $2,\n                   0, $2, 'each',\n                   'receiving', 'purchase_order', gen_random_uuid(),\n                   $4, 'Test', $5,\n                   NOW() - make_interval(days => $3))",
        (sku_id, qty, days_ago, ADMIN_USER_ID, DEFAULT_ORG_ID),
    )


async def _seed_vendor(vendor_id: str = SEEDED_VENDOR_ID, name: str = "Acme Supplies"):
    await sql_execute(
        "INSERT INTO vendors (id, name, organization_id, created_at)\n           VALUES ($1, $2, $3, NOW())\n           ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
        (vendor_id, name, DEFAULT_ORG_ID),
    )
    return vendor_id


async def _seed_received_po(
    vendor_id: str, created_days_ago: int, received_days_ago: int, sku_id: str = "0195f2c0-89af-7000-8000-000000000101"
):
    po_id = str(uuid.uuid4())
    await sql_execute(
        "INSERT INTO purchase_orders\n           (id, vendor_id, vendor_name, status, created_by_id, created_by_name,\n            organization_id, created_at, received_at)\n           VALUES ($1, $2, 'Acme', 'received', $3, 'Test',\n                   $4,\n                   NOW() - make_interval(days => $5),\n                   NOW() - make_interval(days => $6))\n           ON CONFLICT (id) DO UPDATE SET received_at = EXCLUDED.received_at",
        (po_id, vendor_id, ADMIN_USER_ID, DEFAULT_ORG_ID, created_days_ago, received_days_ago),
    )
    await sql_execute(
        "INSERT INTO purchase_order_items\n           (id, po_id, name, ordered_qty, delivered_qty, unit_price, cost,\n            base_unit, sell_uom, pack_qty, suggested_department, status, sku_id,\n            organization_id)\n           VALUES (gen_random_uuid(), $1, 'Widget', 50, 50, 10.0, 10.0,\n                   'each', 'each', 1, 'HDW', 'received', $2, $3)\n           ON CONFLICT DO NOTHING",
        (po_id, sku_id, DEFAULT_ORG_ID),
    )
    return po_id


class TestDemandNormalizedVelocity:
    """IQR outlier stripping returns clean velocity metrics."""

    def test_basic_velocity_with_outliers(self, call):

        async def _body():
            sku_id = await _seed_sku()
            daily = [5.0] * 15 + [200.0]
            await _seed_withdrawal_txns(sku_id, daily, start_days_ago=20)
            result = await get_database_manager().inventory.demand_normalized_velocity(get_org_id(), [sku_id], days=30)
            assert sku_id in result
            vel = result[sku_id]
            assert vel["raw_total"] == 275.0
            assert vel["normalized_total"] < vel["raw_total"]
            assert vel["outlier_days"] >= 1
            assert vel["normalized_daily"] > 0
            assert vel["median_daily"] <= 5.0

        call(_body)

    def test_empty_returns_empty(self, call):

        async def _body():
            result = await get_database_manager().inventory.demand_normalized_velocity(get_org_id(), [], days=30)
            assert result == {}

        call(_body)

    def test_no_activity_returns_empty(self, call):

        async def _body():
            sku_id = await _seed_sku()
            result = await get_database_manager().inventory.demand_normalized_velocity(get_org_id(), [sku_id], days=30)
            assert sku_id not in result

        call(_body)

    def test_uniform_demand_no_outliers(self, call):

        async def _body():
            sku_id = await _seed_sku()
            daily = [5.0] * 15
            await _seed_withdrawal_txns(sku_id, daily, start_days_ago=20)
            result = await get_database_manager().inventory.demand_normalized_velocity(get_org_id(), [sku_id], days=30)
            assert sku_id in result
            vel = result[sku_id]
            assert vel["outlier_days"] == 0
            assert vel["raw_total"] == vel["normalized_total"]

        call(_body)


class TestSkuDemandProfile:
    """Per-SKU demand profile with outlier flags and project buy detection."""

    def test_profile_with_spike(self, call):

        async def _body():
            sku_id = await _seed_sku()
            daily = [2.0, 3.0, 4.0, 5.0, 3.0, 4.0, 2.0, 3.0, 5.0, 4.0, 150.0]
            await _seed_withdrawal_txns(sku_id, daily, start_days_ago=15)
            profile = await get_database_manager().inventory.sku_demand_profile(get_org_id(), sku_id, days=30)
            assert profile["sku_id"] == sku_id
            assert profile["total_days_active"] == 11
            assert profile["raw_total"] == 185.0
            assert profile["baseline_total"] < profile["raw_total"]
            assert profile["stats"]["outlier_days"] >= 1
            assert len(profile["daily"]) == 11
            outlier_days = [d for d in profile["daily"] if d["outlier"]]
            assert len(outlier_days) >= 1

        call(_body)

    def test_empty_profile(self, call):

        async def _body():
            sku_id = await _seed_sku()
            profile = await get_database_manager().inventory.sku_demand_profile(get_org_id(), sku_id, days=30)
            assert profile["total_days_active"] == 0
            assert profile["raw_total"] == 0
            assert profile["daily"] == []
            assert profile["stats"] is None

        call(_body)


class TestVendorLeadTimeActual:
    """Actual lead time from PO created_at vs received_at."""

    def test_basic_lead_time(self, call):

        async def _body():
            from purchasing.application.analytics import vendor_lead_time_actual

            vendor_id = await _seed_vendor()
            await _seed_received_po(vendor_id, created_days_ago=90, received_days_ago=83)
            await _seed_received_po(vendor_id, created_days_ago=60, received_days_ago=50)
            await _seed_received_po(vendor_id, created_days_ago=30, received_days_ago=22)
            result = await vendor_lead_time_actual(vendor_id, days=180)
            assert result["po_count"] == 3
            assert result["actual_median_days"] is not None
            assert 7 <= result["actual_median_days"] <= 10
            assert result["actual_p90_days"] >= result["actual_median_days"]
            assert result["trend"] in ("improving", "stable", "degrading")

        call(_body)

    def test_no_pos_returns_no_data(self, call):

        async def _body():
            from purchasing.application.analytics import vendor_lead_time_actual

            vendor_id = await _seed_vendor(str(uuid.uuid4()), "Empty Vendor")
            result = await vendor_lead_time_actual(vendor_id, days=180)
            assert result["po_count"] == 0
            assert result["actual_median_days"] is None
            assert result["trend"] == "no_data"

        call(_body)

    def test_degrading_trend_detected(self, call):

        async def _body():
            from purchasing.application.analytics import vendor_lead_time_actual

            vendor_id = await _seed_vendor(str(uuid.uuid4()), "Slow Vendor")
            await _seed_received_po(vendor_id, created_days_ago=120, received_days_ago=117)
            await _seed_received_po(vendor_id, created_days_ago=100, received_days_ago=97)
            await _seed_received_po(vendor_id, created_days_ago=80, received_days_ago=77)
            await _seed_received_po(vendor_id, created_days_ago=30, received_days_ago=15)
            await _seed_received_po(vendor_id, created_days_ago=25, received_days_ago=10)
            await _seed_received_po(vendor_id, created_days_ago=20, received_days_ago=5)
            result = await vendor_lead_time_actual(vendor_id, days=180)
            assert result["po_count"] == 6
            assert result["trend"] == "degrading"

        call(_body)


class TestInventoryCarryingCost:
    """Estimated holding cost based on inventory value and days held."""

    def test_basic_carrying_cost(self, call):

        async def _body():
            from shared.infrastructure.db import get_org_id
            from shared.infrastructure.db.base import get_database_manager

            sku_id = await _seed_sku(quantity=100.0, cost=20.0)
            await _seed_receiving_txn(sku_id, qty=100, days_ago=30)
            fin = get_database_manager().finance
            results = await fin.analytics_inventory_carrying_cost(get_org_id(), holding_rate_pct=25.0)
            assert len(results) >= 1
            match = [r for r in results if r["sku_id"] == sku_id]
            assert len(match) == 1
            item = match[0]
            assert item["inventory_value"] == 2000.0
            assert item["carrying_cost"] > 0
            assert 30 < item["carrying_cost"] < 60

        call(_body)

    def test_zero_cost_excluded(self, call):

        async def _body():
            from shared.infrastructure.db import get_org_id
            from shared.infrastructure.db.base import get_database_manager

            sku_id = str(uuid.uuid4())
            await _seed_sku(sku_id=sku_id, sku_code="HDW-FREE-01", quantity=100, cost=0)
            fin = get_database_manager().finance
            results = await fin.analytics_inventory_carrying_cost(get_org_id())
            free_matches = [r for r in results if r["sku_id"] == sku_id]
            assert len(free_matches) == 0

        call(_body)

    def test_zero_stock_excluded(self, call):

        async def _body():
            from shared.infrastructure.db import get_org_id
            from shared.infrastructure.db.base import get_database_manager

            sku_id = str(uuid.uuid4())
            await _seed_sku(sku_id=sku_id, sku_code="HDW-EMPTY-01", quantity=0, cost=10)
            fin = get_database_manager().finance
            results = await fin.analytics_inventory_carrying_cost(get_org_id())
            empty_matches = [r for r in results if r["sku_id"] == sku_id]
            assert len(empty_matches) == 0

        call(_body)


class TestReorderPointSmart:
    """Velocity-based reorder points compared to static min_stock."""

    def test_recommends_higher_min_for_fast_mover(self, call):

        async def _body():
            from purchasing.application.analytics import reorder_point_smart

            sku_id = await _seed_sku(quantity=8, min_stock=5, cost=10.0)
            daily = [20.0] * 10
            await _seed_withdrawal_txns(sku_id, daily, start_days_ago=15)
            results = await reorder_point_smart(limit=50, velocity_days=30)
            match = [r for r in results if r["sku_id"] == sku_id]
            if match:
                item = match[0]
                assert item["recommended_min_stock"] > item["current_min_stock"]
                assert item["risk"] == "under_stocked"

        call(_body)

    def test_no_low_stock_returns_empty(self, call):

        async def _body():
            from purchasing.application.analytics import reorder_point_smart

            sku_id = str(uuid.uuid4())
            await _seed_sku(sku_id=sku_id, sku_code="HDW-FULL-01", quantity=1000, min_stock=5)
            results = await reorder_point_smart(limit=10)
            plenty_matches = [r for r in results if r["sku_id"] == sku_id]
            assert len(plenty_matches) == 0

        call(_body)


class TestForecastStockoutNormalized:
    """forecast_stockout uses normalized velocity, not raw."""

    def test_spike_does_not_inflate_forecast(self, call):

        async def _body():
            from assistant.agents.inventory.tools import _forecast_stockout

            sku_id = await _seed_sku(quantity=30)
            daily = [2.0] * 15 + [500.0]
            await _seed_withdrawal_txns(sku_id, daily, start_days_ago=20)
            import json

            raw = await _forecast_stockout(limit=50)
            data = json.loads(raw)
            match = [f for f in data["forecast"] if f["sku"] == "HDW-TEST-01"]
            if match:
                assert match[0]["days_until_stockout"] > 5

        call(_body)
