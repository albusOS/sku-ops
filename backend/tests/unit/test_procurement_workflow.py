from unittest.mock import AsyncMock, patch

import pytest

from assistant.application.workflows.procurement_overview import run_procurement_overview


@pytest.mark.asyncio
async def test_procurement_overview_shapes_snapshot_and_po_summary():
    fetched = {"procurement_snapshot_raw": {"items": [{"sku": "ABC-123", "name": "PVC Pipe", "preferred_vendor": "Acme Supply", "days_until_stockout": 2.5}]}, "po_summary": {"total_pos": 3, "by_status": {"draft": {"count": 1, "total": 100.0}}}}
    with patch("assistant.application.workflows.procurement_overview.run_parallel_fetch", new=AsyncMock(return_value=fetched)):
        result = await run_procurement_overview()
    assert result.procurement_snapshot[0]["sku"] == "ABC-123"
    assert result.po_summary["total_pos"] == 3
    assert "Procurement Overview" in result.synthesized_markdown
