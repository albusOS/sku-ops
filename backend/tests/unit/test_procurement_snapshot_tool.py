import json
from unittest.mock import AsyncMock, patch

import pytest

from assistant.agents.purchasing.tools import _get_procurement_snapshot


@pytest.mark.asyncio
async def test_procurement_snapshot_merges_core_procurement_signals():
    reorder = {
        "count": 1,
        "items": [
            {
                "sku_id": "sku-1",
                "sku": "ABC-123",
                "name": "PVC Pipe",
                "department": "Plumbing",
                "quantity": 3,
                "sell_uom": "each",
                "min_stock": 10,
                "deficit": 7,
                "vendor_options": [{"vendor_name": "Acme Supply", "lead_time_days": 5, "is_preferred": True}],
            }
        ],
    }
    smart = {
        "count": 1,
        "items": [
            {
                "sku_id": "sku-1",
                "sku": "ABC-123",
                "name": "PVC Pipe",
                "quantity": 3,
                "sell_uom": "each",
                "current_min_stock": 10,
                "recommended_min_stock": 24,
                "gap": 14,
                "risk": "under_stocked",
                "vendor_lead_days": 6,
                "vendor_name": "Acme Supply",
            }
        ],
    }
    stockout = {"count": 1, "forecast": [{"sku": "ABC-123", "avg_daily_use": 1.2, "days_until_stockout": 2.5}]}
    with (
        patch(
            "assistant.agents.purchasing.tools._get_reorder_with_vendor_context",
            new=AsyncMock(return_value=json.dumps(reorder)),
        ),
        patch(
            "assistant.agents.purchasing.tools._get_smart_reorder_points", new=AsyncMock(return_value=json.dumps(smart))
        ),
        patch("assistant.agents.purchasing.tools._forecast_stockout", new=AsyncMock(return_value=json.dumps(stockout))),
    ):
        raw = await _get_procurement_snapshot(limit=10)
    data = json.loads(raw)
    assert data["count"] == 1
    item = data["items"][0]
    assert item["sku"] == "ABC-123"
    assert item["recommended_min_stock"] == 24
    assert item["min_stock_gap"] == 14
    assert item["days_until_stockout"] == 2.5
    assert item["preferred_vendor"] == "Acme Supply"
