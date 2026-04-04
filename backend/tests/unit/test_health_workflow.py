from unittest.mock import AsyncMock, patch

import pytest

from assistant.application.workflows.health_overview import run_health_overview


@pytest.mark.asyncio
async def test_health_overview_shapes_priority_inputs():
    fetched = {"inventory_stats": {"total_skus": 100, "low_stock_count": 8}, "stockout_forecast_raw": {"forecast": [{"sku": "ABC-123", "name": "PVC Pipe", "days_until_stockout": 2.5}]}, "slow_movers_raw": {"slow_movers": [{"sku": "XYZ-999", "name": "Old Valve"}]}, "carrying_cost": {"total_carrying_cost": 1234.5}, "pl_summary": {"revenue": 10000, "gross_profit": 2500}, "outstanding_balances_raw": {"balances": [{"entity": "Acme", "balance": 500.0}]}, "ar_aging": {"buckets": {"current": 1000}}, "payment_status_breakdown": {"paid": {"total": 9000}}, "pending_material_requests_raw": {"pending_requests": [{"id": "req-1", "contractor": "Jane"}]}}
    with patch("assistant.application.workflows.health_overview.run_parallel_fetch", new=AsyncMock(return_value=fetched)):
        result = await run_health_overview(days=30)
    assert result.inventory_stats["total_skus"] == 100
    assert result.stockout_forecast[0]["sku"] == "ABC-123"
    assert result.outstanding_balances[0]["balance"] == 500.0
    assert result.pending_material_requests[0]["id"] == "req-1"
    assert "Health Overview" in result.synthesized_markdown
