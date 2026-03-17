"""Report math regression tests."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from reports.application.inventory_reports import product_performance_report


@pytest.mark.asyncio
async def test_product_performance_report_handles_mixed_numeric_types(monkeypatch):
    async def _product_margins(*, start_date=None, end_date=None, limit=200):
        return [
            {
                "sku_id": "sku-1",
                "revenue": Decimal("120.00"),
                "cost": Decimal("45.50"),
                "profit": Decimal("74.50"),
                "margin_pct": Decimal("62.1"),
            }
        ]

    async def _list_skus():
        return [
            SimpleNamespace(
                id="sku-1",
                name="Widget",
                sku="W-1",
                category_name="Hardware",
                quantity=3.5,
                cost=4.25,
            )
        ]

    async def _units_sold_by_product(*, start_date=None, end_date=None):
        return {"sku-1": 2.0}

    monkeypatch.setattr(
        "reports.application.inventory_reports.ledger_repo.product_margins",
        _product_margins,
    )
    monkeypatch.setattr("reports.application.inventory_reports.list_skus", _list_skus)
    monkeypatch.setattr(
        "reports.application.inventory_reports.ledger_repo.units_sold_by_product",
        _units_sold_by_product,
    )

    report = await product_performance_report()

    assert report.total == 1
    row = report.products[0]
    assert row["revenue"] == pytest.approx(120.0)
    assert row["cogs"] == pytest.approx(45.5)
    assert row["gross_profit"] == pytest.approx(74.5)
    assert row["avg_cost_per_unit"] == pytest.approx(22.75)
    assert row["sell_through_pct"] == pytest.approx(36.4, abs=0.1)
