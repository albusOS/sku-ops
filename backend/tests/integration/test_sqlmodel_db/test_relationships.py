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
    Users,
    Withdrawals,
)
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

pytestmark = pytest.mark.skipif(
    "not config.getoption('--run-integration', default=False)",
    reason="Integration tests require --run-integration flag and running local Supabase",
)

NOW = datetime.now(tz=UTC)
SEEDED_ORG_ID = uuid.UUID("0195f2c0-89aa-7d6d-bb34-7f3b3f69c001")
SEEDED_BILLING_ENTITY_NAME = "Riva Ridge Property Mgmt"
SEEDED_CONTRACTOR_NAME = "Dev Contractor"
SEEDED_CONTRACTOR_COMPANY = "Dev Contractor Co"
SEEDED_ADMIN_NAME = "Dev Admin"


class TestFKConstraintEnforcement:
    async def test_child_with_invalid_fk_raises(self, session):
        """Inserting a product with a non-existent category_id should fail."""
        product = Products(
            id=uuid.uuid4(),
            name="Orphan Product",
            category_id=uuid.uuid4(),
            category_name="Missing Department",
            created_at=NOW,
            description="Product fixture for FK enforcement",
            sku_count=0,
            updated_at=NOW,
        )
        session.add(product)
        with pytest.raises(IntegrityError):
            await session.flush()

    async def test_valid_fk_succeeds(self, session):
        """Inserting a product with a valid category_id should succeed."""
        dept_id = uuid.uuid4()
        dept = Departments(
            id=dept_id,
            name="Valid Dept",
            code=f"VLD-{uuid.uuid4().hex[:4]}",
            description="Department fixture for FK success path",
            created_at=NOW,
            organization_id=SEEDED_ORG_ID,
            sku_count=0,
        )
        session.add(dept)
        await session.flush()

        product = Products(
            id=uuid.uuid4(),
            name="Valid Product",
            category_id=dept_id,
            category_name="Valid Dept",
            created_at=NOW,
            description="Product fixture for valid FK path",
            sku_count=0,
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
        inv_id = uuid.uuid4()
        wd_id = uuid.uuid4()
        contractor_id = uuid.uuid4()
        admin_id = uuid.uuid4()

        contractor = Users(
            id=contractor_id,
            email=f"{contractor_id}@example.com",
            password="hash",
            name=SEEDED_CONTRACTOR_NAME,
            role="contractor",
            company=SEEDED_CONTRACTOR_COMPANY,
            billing_entity=SEEDED_BILLING_ENTITY_NAME,
            is_active=True,
            organization_id=SEEDED_ORG_ID,
            created_at=NOW,
        )
        admin = Users(
            id=admin_id,
            email=f"{admin_id}@example.com",
            password="hash",
            name=SEEDED_ADMIN_NAME,
            role="admin",
            is_active=True,
            organization_id=SEEDED_ORG_ID,
            created_at=NOW,
        )
        session.add(contractor)
        session.add(admin)

        invoice = Invoices(
            id=inv_id,
            invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
            amount_credited=0.0,
            billing_address="1200 Mountain View Dr, Ste 400, Vail CO 81657",
            billing_entity=SEEDED_BILLING_ENTITY_NAME,
            contact_email="mike@rivridge.com",
            contact_name="Mike Torres",
            subtotal=100.0,
            currency="USD",
            tax=10.0,
            tax_rate=0.1,
            total=110.0,
            created_at=NOW,
            organization_id=SEEDED_ORG_ID,
            payment_terms="net_30",
            po_reference="TEST-PO",
            status="draft",
            updated_at=NOW,
            xero_sync_status="pending",
        )
        session.add(invoice)

        withdrawal = Withdrawals(
            id=wd_id,
            billing_entity=SEEDED_BILLING_ENTITY_NAME,
            contractor_company=SEEDED_CONTRACTOR_COMPANY,
            job_id=uuid.uuid4(),
            service_address="123 Test St",
            subtotal=100.0,
            tax=10.0,
            tax_rate=0.1,
            total=110.0,
            cost_total=80.0,
            contractor_id=contractor_id,
            contractor_name=SEEDED_CONTRACTOR_NAME,
            organization_id=SEEDED_ORG_ID,
            payment_status="pending",
            processed_by_id=admin_id,
            processed_by_name=SEEDED_ADMIN_NAME,
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
