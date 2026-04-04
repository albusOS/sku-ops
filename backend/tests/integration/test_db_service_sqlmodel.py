"""Integration tests for the SQLModel-backed shared DB service layer."""
from sqlalchemy import text

def test_get_session_outside_transaction_opens_working_session(call):
    from shared.infrastructure.db import get_session

    async def _body():
        async with get_session() as session:
            result = await session.execute(text('SELECT 1'))
            assert result.scalar_one() == 1
    call(_body)

def test_get_session_inside_transaction_reuses_shared_session(call):
    from shared.infrastructure.db import get_session, transaction

    async def _body():
        async with transaction(), get_session() as session_one:
            async with get_session() as session_two:
                assert session_one is session_two
                result = await session_one.execute(text('SELECT 1'))
                assert result.scalar_one() == 1
    call(_body)
