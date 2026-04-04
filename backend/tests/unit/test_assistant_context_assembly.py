from unittest.mock import AsyncMock, patch
import pytest
from assistant.application.context_assembly import assemble_context
from tests.helpers.auth import ADMIN_USER_ID

@pytest.mark.asyncio
async def test_assemble_context_skips_vector_search_when_disabled():
    with patch('assistant.application.context_assembly._vector_search', new=AsyncMock(return_value=[{'entity_type': 'sku', 'entity_id': 'sku-1'}])) as vector_search:
        ctx = await assemble_context(query='what should I order', user_id=ADMIN_USER_ID, include_graph=False, include_memory=False, max_entity_hits=0)
    assert ctx.entity_hits == []
    vector_search.assert_not_awaited()
