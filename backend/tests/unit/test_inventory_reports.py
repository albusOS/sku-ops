"""Report math regression tests."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from reports.application.inventory_reports import product_performance_report


@pytest.mark.asyncio
async def test_product_performance_report_handles_mixed_numeric_types(monkeypatch):

    async def _product_margins(*, start_date=None, end_date=None, limit=200):
        return [{"sku_id": "sku-1", "revenue": Decimal("120.00"), "cost": Decimal("45.50"), "profit": Decimal("74.50"), "margin_pct": Decimal("62.1")}]

    async def _list_skus():
        return [SimpleNamespace(id="sku-1", name="Widget", sku="W-1", category_name="Hardware", quantity=3.5, cost=4.25, base_unit="each")]

    async def _units_sold_by_product(_org_id: str, *, start_date=None, end_date=None):
        return {"sku-1": 2.0}

    class FakeFinance:

        async def analytics_product_margins(self, _org_id, **kwargs):
            return await _product_margins(**kwargs)

    class FakeCatalog:

        async def list_skus(self, _org_id):
            return await _list_skus()

    class FakeOperations:

        async def units_sold_by_product(self, _org_id, **kwargs):
            return await _units_sold_by_product(_org_id, **kwargs)
    monkeypatch.setattr("reports.application.inventory_reports.get_org_id", lambda: "org-test")
    monkeypatch.setattr("reports.application.inventory_reports._db_finance", FakeFinance)
    monkeypatch.setattr("reports.application.inventory_reports._db_catalog", FakeCatalog)
    monkeypatch.setattr("reports.application.inventory_reports._db_operations", FakeOperations)
    report = await product_performance_report(org_id="org-test")
    assert report.total == 1
    row = report.products[0]
    assert row["revenue"] == pytest.approx(120.0)
    assert row["cogs"] == pytest.approx(45.5)
    assert row["gross_profit"] == pytest.approx(74.5)
    assert row["avg_cost_per_unit"] == pytest.approx(22.75)
    assert row["sell_through_pct"] == pytest.approx(36.4, abs=0.1)
