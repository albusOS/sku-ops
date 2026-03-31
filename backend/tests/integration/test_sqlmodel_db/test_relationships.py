"""Integration tests: Relationship loading and FK enforcement against local Postgres."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from backend.shared.infrastructure.types.public_sql_model_models import (
    Departments,
    Invoices,
    InvoiceWithdrawals,
    Products,
    Withdrawals,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and running local Supabase",
)

NOW = datetime.now(tz=UTC)


class TestFKConstraintEnforcement:
    async def test_child_with_invalid_fk_raises(self, session):
        """Inserting a product with a non-existent category_id should fail."""
        product = Products(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            name="Orphan Product",
            category_id="nonexistent-dept-id",
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(product)
        with pytest.raises(IntegrityError):
            await session.flush()

    async def test_valid_fk_succeeds(self, session):
        """Inserting a product with a valid category_id should succeed."""
        dept_id = f"dept-{uuid.uuid4().hex[:8]}"
        dept = Departments(
            id=dept_id,
            name="Valid Dept",
            code=f"VLD-{uuid.uuid4().hex[:4]}",
            created_at=NOW,
        )
        session.add(dept)
        await session.flush()

        product = Products(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            name="Valid Product",
            category_id=dept_id,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(product)
        await session.flush()

        result = await session.exec(
            select(Products).where(Products.category_id == dept_id)
        )
        assert result.first() is not None


class TestM2MRelationship:
    async def test_invoice_withdrawal_link(self, session):
        """Test M2M link between invoices and withdrawals via junction table."""
        inv_id = f"inv-{uuid.uuid4().hex[:8]}"
        wd_id = f"wd-{uuid.uuid4().hex[:8]}"

        invoice = Invoices(
            id=inv_id,
            invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
            subtotal=100.0,
            tax=10.0,
            total=110.0,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(invoice)

        withdrawal = Withdrawals(
            id=wd_id,
            job_id="test-job",
            service_address="123 Test St",
            subtotal=100.0,
            tax=10.0,
            tax_rate=0.1,
            total=110.0,
            cost_total=80.0,
            contractor_id="test-user",
            processed_by_id="test-admin",
            created_at=NOW,
        )
        session.add(withdrawal)
        await session.flush()

        link = InvoiceWithdrawals(
            invoice_id=inv_id,
            withdrawal_id=wd_id,
        )
        session.add(link)
        await session.flush()

        result = await session.exec(
            select(InvoiceWithdrawals).where(
                InvoiceWithdrawals.invoice_id == inv_id
            )
        )
        loaded = result.first()
        assert loaded is not None
        assert loaded.withdrawal_id == wd_id
