"""Integration tests: CRUD operations using generated SQLModel classes against local Postgres."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from backend.shared.infrastructure.types.public_sql_model_models import (
    Departments,
    Organizations,
    Products,
)
from sqlmodel import select

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and running local Supabase",
)


ORG_ID = f"test-org-{uuid.uuid4().hex[:8]}"
NOW = datetime.now(tz=UTC)


class TestOrganizationCRUD:
    async def test_insert_and_select(self, session):
        org = Organizations(
            id=ORG_ID,
            name="Test Org",
            slug=f"test-org-{uuid.uuid4().hex[:8]}",
            created_at=NOW,
        )
        session.add(org)
        await session.flush()

        result = await session.exec(
            select(Organizations).where(Organizations.id == ORG_ID)
        )
        loaded = result.first()
        assert loaded is not None
        assert loaded.name == "Test Org"
        assert loaded.id == ORG_ID

    async def test_update(self, session):
        org = Organizations(
            id=ORG_ID,
            name="Original Name",
            slug=f"slug-{uuid.uuid4().hex[:8]}",
            created_at=NOW,
        )
        session.add(org)
        await session.flush()

        org.name = "Updated Name"
        session.add(org)
        await session.flush()

        result = await session.exec(
            select(Organizations).where(Organizations.id == ORG_ID)
        )
        loaded = result.first()
        assert loaded is not None
        assert loaded.name == "Updated Name"


class TestParentChildInsert:
    async def test_insert_department_and_product(self, session):
        dept_id = f"dept-{uuid.uuid4().hex[:8]}"
        prod_id = f"prod-{uuid.uuid4().hex[:8]}"

        dept = Departments(
            id=dept_id,
            name="Test Department",
            code=f"TST-{uuid.uuid4().hex[:4]}",
            created_at=NOW,
        )
        session.add(dept)
        await session.flush()

        product = Products(
            id=prod_id,
            name="Test Product",
            category_id=dept_id,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(product)
        await session.flush()

        result = await session.exec(
            select(Products).where(Products.id == prod_id)
        )
        loaded = result.first()
        assert loaded is not None
        assert loaded.category_id == dept_id
