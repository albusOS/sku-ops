from unittest.mock import AsyncMock, patch
import pytest
from assistant.application.workflows.trend_overview import run_trend_overview

@pytest.mark.asyncio
async def test_trend_overview_shapes_core_trend_sections():
    fetched = {'trend_series': {'series': [{'period': '2026-03-01', 'revenue': 1000}]}, 'top_skus_raw': {'skus': [{'sku': 'ABC-123', 'name': 'PVC Pipe', 'total_revenue': 500.0}]}, 'department_profitability_raw': {'departments': [{'name': 'Plumbing', 'profit': 250.0}]}, 'daily_withdrawal_activity_raw': {'activity': [{'date': '2026-03-01', 'count': 12}]}}
    with patch('assistant.application.workflows.trend_overview.run_parallel_fetch', new=AsyncMock(return_value=fetched)):
        result = await run_trend_overview(days=30)
    assert result.trend_series['series'][0]['revenue'] == 1000
    assert result.top_skus[0]['sku'] == 'ABC-123'
    assert result.department_profitability[0]['name'] == 'Plumbing'
    assert result.daily_withdrawal_activity[0]['count'] == 12
    assert 'Trend Overview' in result.synthesized_markdown
