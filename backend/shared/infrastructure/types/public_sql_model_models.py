"""
Auto-generated SQLModel models for schema "public".

DO NOT EDIT - regenerate with:
  python -m backend.scripts.supabase_type_generation.supabase_db_to_sql_models
"""

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


class InvoiceWithdrawals(SQLModel, table=True):
    __tablename__ = "invoice_withdrawals"
    __table_args__ = {"schema": "public", "extend_existing": True}

    invoice_id: str = Field(primary_key=True, foreign_key="public.invoices.id")
    withdrawal_id: str = Field(
        primary_key=True, foreign_key="public.withdrawals.id"
    )


class PaymentWithdrawals(SQLModel, table=True):
    __tablename__ = "payment_withdrawals"
    __table_args__ = {"schema": "public", "extend_existing": True}

    payment_id: str = Field(primary_key=True, foreign_key="public.payments.id")
    withdrawal_id: str = Field(
        primary_key=True, foreign_key="public.withdrawals.id"
    )


class Organizations(SQLModel, table=True):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    name: str
    slug: str

    addresses: list["Addresses"] = Relationship(back_populates="organization")
    agent_runs: list["AgentRuns"] = Relationship(back_populates="org")
    audit_logs: list["AuditLog"] = Relationship(back_populates="organization")
    billing_entities: list["BillingEntities"] = Relationship(
        back_populates="organization"
    )
    credit_notes: list["CreditNotes"] = Relationship(
        back_populates="organization"
    )
    cycle_counts: list["CycleCounts"] = Relationship(
        back_populates="organization"
    )
    departments: list["Departments"] = Relationship(
        back_populates="organization"
    )
    documents: list["Documents"] = Relationship(back_populates="organization")
    embeddings: list["Embeddings"] = Relationship(back_populates="org")
    fiscal_periods: list["FiscalPeriods"] = Relationship(
        back_populates="organization"
    )
    invoices: list["Invoices"] = Relationship(back_populates="organization")
    jobs: list["Jobs"] = Relationship(back_populates="organization")
    material_requests: list["MaterialRequests"] = Relationship(
        back_populates="organization"
    )
    memory_artifacts: list["MemoryArtifacts"] = Relationship(
        back_populates="org"
    )
    oauth_states: list["OauthStates"] = Relationship(back_populates="org")
    org_settings: Optional["OrgSettings"] = Relationship(
        back_populates="organization"
    )
    payments: list["Payments"] = Relationship(back_populates="organization")
    products: list["Products"] = Relationship(back_populates="organization")
    purchase_order_items: list["PurchaseOrderItems"] = Relationship(
        back_populates="organization"
    )
    purchase_orders: list["PurchaseOrders"] = Relationship(
        back_populates="organization"
    )
    returns: list["Returns"] = Relationship(back_populates="organization")
    skus: list["Skus"] = Relationship(back_populates="organization")
    stock_transactions: list["StockTransactions"] = Relationship(
        back_populates="organization"
    )
    units_of_measures: list["UnitsOfMeasure"] = Relationship(
        back_populates="organization"
    )
    users: list["Users"] = Relationship(back_populates="organization")
    vendor_items: list["VendorItems"] = Relationship(
        back_populates="organization"
    )
    vendors: list["Vendors"] = Relationship(back_populates="organization")
    withdrawals: list["Withdrawals"] = Relationship(
        back_populates="organization"
    )


class BillingEntities(SQLModel, table=True):
    __tablename__ = "billing_entities"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_address: str
    contact_email: str
    contact_name: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    is_active: bool
    name: str
    organization_id: str = Field(foreign_key="public.organizations.id")
    payment_terms: str
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    xero_contact_id: str | None = Field(default=None)

    organization: Optional["Organizations"] = Relationship(
        back_populates="billing_entities"
    )
    addresses: list["Addresses"] = Relationship(back_populates="billing_entity")
    credit_notes: list["CreditNotes"] = Relationship(
        back_populates="billing_entity_rel"
    )
    invoices: list["Invoices"] = Relationship(
        back_populates="billing_entity_rel"
    )
    jobs: list["Jobs"] = Relationship(back_populates="billing_entity")
    payments: list["Payments"] = Relationship(back_populates="billing_entity")
    returns: list["Returns"] = Relationship(back_populates="billing_entity_rel")
    users: list["Users"] = Relationship(back_populates="billing_entity_rel")
    withdrawals: list["Withdrawals"] = Relationship(
        back_populates="billing_entity_rel"
    )


class Users(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity: str | None = Field(default=None)
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    company: str | None = Field(default=None)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    email: str
    id: str = Field(primary_key=True)
    is_active: bool
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    password: str
    phone: str | None = Field(default=None)
    role: str

    billing_entity_rel: Optional["BillingEntities"] = Relationship(
        back_populates="users"
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="users"
    )
    agent_runs: list["AgentRuns"] = Relationship(back_populates="user")
    audit_logs: list["AuditLog"] = Relationship(back_populates="user")
    cycle_counts: list["CycleCounts"] = Relationship(
        back_populates="committed_by",
        sa_relationship_kwargs={"foreign_keys": "CycleCounts.committed_by_id"},
    )
    created_by_cycle_counts: list["CycleCounts"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"foreign_keys": "CycleCounts.created_by_id"},
    )
    documents: list["Documents"] = Relationship(back_populates="uploaded_by")
    fiscal_periods: list["FiscalPeriods"] = Relationship(
        back_populates="closed_by"
    )
    invoices: list["Invoices"] = Relationship(back_populates="approved_by")
    material_requests: list["MaterialRequests"] = Relationship(
        back_populates="contractor",
        sa_relationship_kwargs={
            "foreign_keys": "MaterialRequests.contractor_id"
        },
    )
    processed_by_material_requests: list["MaterialRequests"] = Relationship(
        back_populates="processed_by",
        sa_relationship_kwargs={
            "foreign_keys": "MaterialRequests.processed_by_id"
        },
    )
    memory_artifacts: list["MemoryArtifacts"] = Relationship(
        back_populates="user"
    )
    payments: list["Payments"] = Relationship(back_populates="recorded_by")
    refresh_tokens: list["RefreshTokens"] = Relationship(back_populates="user")
    returns: list["Returns"] = Relationship(back_populates="contractor")
    stock_transactions: list["StockTransactions"] = Relationship(
        back_populates="user"
    )
    withdrawals: list["Withdrawals"] = Relationship(
        back_populates="contractor",
        sa_relationship_kwargs={"foreign_keys": "Withdrawals.contractor_id"},
    )
    processed_by_withdrawals: list["Withdrawals"] = Relationship(
        back_populates="processed_by",
        sa_relationship_kwargs={"foreign_keys": "Withdrawals.processed_by_id"},
    )


class OrgSettings(SQLModel, table=True):
    __tablename__ = "org_settings"
    __table_args__ = {"schema": "public", "extend_existing": True}

    auto_invoice: bool
    default_tax_rate: float = Field(sa_type=Float)
    organization_id: str = Field(
        primary_key=True, foreign_key="public.organizations.id"
    )
    updated_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    xero_access_token: str | None = Field(default=None)
    xero_ap_account_code: str
    xero_cogs_account_code: str
    xero_inventory_account_code: str
    xero_refresh_token: str | None = Field(default=None)
    xero_sales_account_code: str
    xero_tax_type: str
    xero_tenant_id: str | None = Field(default=None)
    xero_token_expiry: str | None = Field(default=None)
    xero_tracking_category_id: str | None = Field(default=None)

    organization: Optional["Organizations"] = Relationship(
        back_populates="org_settings"
    )


class RefreshTokens(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    expires_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    revoked: bool
    token_hash: str
    user_id: str = Field(foreign_key="public.users.id")

    user: Optional["Users"] = Relationship(back_populates="refresh_tokens")


class OauthStates(SQLModel, table=True):
    __tablename__ = "oauth_states"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    org_id: str = Field(foreign_key="public.organizations.id")
    state: str = Field(primary_key=True)

    org: Optional["Organizations"] = Relationship(back_populates="oauth_states")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "public", "extend_existing": True}

    action: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    details: str | None = Field(default=None)
    id: str = Field(primary_key=True)
    ip_address: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    resource_id: str | None = Field(default=None)
    resource_type: str | None = Field(default=None)
    user_id: str | None = Field(foreign_key="public.users.id", default=None)

    organization: Optional["Organizations"] = Relationship(
        back_populates="audit_logs"
    )
    user: Optional["Users"] = Relationship(back_populates="audit_logs")


class Addresses(SQLModel, table=True):
    __tablename__ = "addresses"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    city: str
    country: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    job_id: str | None = Field(default=None)
    label: str
    line1: str
    line2: str
    organization_id: str = Field(foreign_key="public.organizations.id")
    postal_code: str
    state: str

    billing_entity: Optional["BillingEntities"] = Relationship(
        back_populates="addresses"
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="addresses"
    )


class FiscalPeriods(SQLModel, table=True):
    __tablename__ = "fiscal_periods"
    __table_args__ = {"schema": "public", "extend_existing": True}

    closed_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    closed_by_id: str | None = Field(
        foreign_key="public.users.id", default=None
    )
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    end_date: datetime.date = Field(sa_type=Date)
    id: str = Field(primary_key=True)
    name: str
    organization_id: str = Field(foreign_key="public.organizations.id")
    start_date: datetime.date = Field(sa_type=Date)
    status: str

    closed_by: Optional["Users"] = Relationship(back_populates="fiscal_periods")
    organization: Optional["Organizations"] = Relationship(
        back_populates="fiscal_periods"
    )


class ProcessedEvents(SQLModel, table=True):
    __tablename__ = "processed_events"
    __table_args__ = {"schema": "public", "extend_existing": True}

    event_id: str = Field(primary_key=True)
    event_type: str
    handler_name: str = Field(primary_key=True)
    processed_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))


class Departments(SQLModel, table=True):
    __tablename__ = "departments"
    __table_args__ = {"schema": "public", "extend_existing": True}

    code: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    description: str
    id: str = Field(primary_key=True)
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    sku_count: int

    organization: Optional["Organizations"] = Relationship(
        back_populates="departments"
    )
    products: list["Products"] = Relationship(back_populates="category")
    skus: list["Skus"] = Relationship(back_populates="category")


class UnitsOfMeasure(SQLModel, table=True):
    __tablename__ = "units_of_measure"
    __table_args__ = {"schema": "public", "extend_existing": True}

    code: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    family: str
    id: str = Field(primary_key=True)
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )

    organization: Optional["Organizations"] = Relationship(
        back_populates="units_of_measures"
    )


class Vendors(SQLModel, table=True):
    __tablename__ = "vendors"
    __table_args__ = {"schema": "public", "extend_existing": True}

    address: str
    contact_name: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    email: str
    id: str = Field(primary_key=True)
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    phone: str

    organization: Optional["Organizations"] = Relationship(
        back_populates="vendors"
    )
    purchase_orders: list["PurchaseOrders"] = Relationship(
        back_populates="vendor"
    )
    vendor_items: list["VendorItems"] = Relationship(back_populates="vendor")


class Products(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = {"schema": "public", "extend_existing": True}

    category_id: str = Field(foreign_key="public.departments.id")
    category_name: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    description: str
    id: str = Field(primary_key=True)
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    sku_count: int
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))

    category: Optional["Departments"] = Relationship(back_populates="products")
    organization: Optional["Organizations"] = Relationship(
        back_populates="products"
    )
    skus: list["Skus"] = Relationship(back_populates="product_family")


class Skus(SQLModel, table=True):
    __tablename__ = "skus"
    __table_args__ = {"schema": "public", "extend_existing": True}

    barcode: str | None = Field(default=None)
    base_unit: str
    category_id: str = Field(foreign_key="public.departments.id")
    category_name: str
    cost: float = Field(sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    description: str
    grade: str
    id: str = Field(primary_key=True)
    min_stock: int
    name: str
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    pack_qty: int
    price: float = Field(sa_type=Float)
    product_family_id: str = Field(foreign_key="public.products.id")
    purchase_pack_qty: int
    purchase_uom: str
    quantity: float = Field(sa_type=Float)
    sell_uom: str
    sku: str
    spec: str
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    variant_attrs: str
    variant_label: str
    vendor_barcode: str | None = Field(default=None)

    category: Optional["Departments"] = Relationship(back_populates="skus")
    organization: Optional["Organizations"] = Relationship(
        back_populates="skus"
    )
    product_family: Optional["Products"] = Relationship(back_populates="skus")
    cycle_count_items: list["CycleCountItems"] = Relationship(
        back_populates="sku_rel"
    )
    stock_transactions: list["StockTransactions"] = Relationship(
        back_populates="sku_rel"
    )
    vendor_items: list["VendorItems"] = Relationship(back_populates="sku")


class VendorItems(SQLModel, table=True):
    __tablename__ = "vendor_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    cost: float = Field(sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    id: str = Field(primary_key=True)
    is_preferred: bool
    lead_time_days: int | None = Field(default=None)
    moq: float | None = Field(default=None, sa_type=Float)
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    purchase_pack_qty: int
    purchase_uom: str
    sku_id: str = Field(foreign_key="public.skus.id")
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    vendor_id: str = Field(foreign_key="public.vendors.id")
    vendor_name: str
    vendor_sku: str | None = Field(default=None)

    organization: Optional["Organizations"] = Relationship(
        back_populates="vendor_items"
    )
    sku: Optional["Skus"] = Relationship(back_populates="vendor_items")
    vendor: Optional["Vendors"] = Relationship(back_populates="vendor_items")


class SkuCounters(SQLModel, table=True):
    __tablename__ = "sku_counters"
    __table_args__ = {"schema": "public", "extend_existing": True}

    counter: int
    department_code: str = Field(primary_key=True)


class StockTransactions(SQLModel, table=True):
    __tablename__ = "stock_transactions"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    organization_id: str = Field(foreign_key="public.organizations.id")
    original_quantity: float | None = Field(default=None, sa_type=Float)
    original_unit: str | None = Field(default=None)
    product_name: str
    quantity_after: float = Field(sa_type=Float)
    quantity_before: float = Field(sa_type=Float)
    quantity_delta: float = Field(sa_type=Float)
    reason: str | None = Field(default=None)
    reference_id: str | None = Field(default=None)
    reference_type: str | None = Field(default=None)
    sku: str
    sku_id: str = Field(foreign_key="public.skus.id")
    transaction_type: str
    unit: str
    user_id: str = Field(foreign_key="public.users.id")
    user_name: str

    organization: Optional["Organizations"] = Relationship(
        back_populates="stock_transactions"
    )
    sku_rel: Optional["Skus"] = Relationship(
        back_populates="stock_transactions"
    )
    user: Optional["Users"] = Relationship(back_populates="stock_transactions")


class CycleCounts(SQLModel, table=True):
    __tablename__ = "cycle_counts"
    __table_args__ = {"schema": "public", "extend_existing": True}

    committed_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    committed_by_id: str | None = Field(
        foreign_key="public.users.id", default=None
    )
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    created_by_id: str = Field(foreign_key="public.users.id")
    created_by_name: str
    id: str = Field(primary_key=True)
    organization_id: str = Field(foreign_key="public.organizations.id")
    scope: str | None = Field(default=None)
    status: str

    committed_by: Optional["Users"] = Relationship(
        back_populates="cycle_counts",
        sa_relationship_kwargs={"foreign_keys": "CycleCounts.committed_by_id"},
    )
    created_by: Optional["Users"] = Relationship(
        back_populates="created_by_cycle_counts",
        sa_relationship_kwargs={"foreign_keys": "CycleCounts.created_by_id"},
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="cycle_counts"
    )
    cycle_count_items: list["CycleCountItems"] = Relationship(
        back_populates="cycle_count"
    )


class CycleCountItems(SQLModel, table=True):
    __tablename__ = "cycle_count_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    counted_qty: float | None = Field(default=None, sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    cycle_count_id: str = Field(foreign_key="public.cycle_counts.id")
    id: str = Field(primary_key=True)
    notes: str | None = Field(default=None)
    product_name: str
    sku: str
    sku_id: str = Field(foreign_key="public.skus.id")
    snapshot_qty: float = Field(sa_type=Float)
    unit: str
    variance: float | None = Field(default=None, sa_type=Float)

    cycle_count: Optional["CycleCounts"] = Relationship(
        back_populates="cycle_count_items"
    )
    sku_rel: Optional["Skus"] = Relationship(back_populates="cycle_count_items")


class Invoices(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount_credited: float = Field(sa_type=Float)
    approved_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    approved_by_id: str | None = Field(
        foreign_key="public.users.id", default=None
    )
    billing_address: str
    billing_entity: str
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    contact_email: str
    contact_name: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    currency: str
    deleted_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    due_date: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    id: str = Field(primary_key=True)
    invoice_date: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    invoice_number: str
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    payment_terms: str
    po_reference: str
    status: str
    subtotal: float = Field(sa_type=Float)
    tax: float = Field(sa_type=Float)
    tax_rate: float = Field(sa_type=Float)
    total: float = Field(sa_type=Float)
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    xero_cogs_journal_id: str | None = Field(default=None)
    xero_invoice_id: str | None = Field(default=None)
    xero_sync_status: str

    approved_by: Optional["Users"] = Relationship(back_populates="invoices")
    billing_entity_rel: Optional["BillingEntities"] = Relationship(
        back_populates="invoices"
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="invoices"
    )
    credit_notes: list["CreditNotes"] = Relationship(back_populates="invoice")
    invoice_line_items: list["InvoiceLineItems"] = Relationship(
        back_populates="invoice"
    )
    withdrawals: list["Withdrawals"] = Relationship(
        back_populates="invoices", link_model=InvoiceWithdrawals
    )
    payments: list["Payments"] = Relationship(back_populates="invoice")
    withdrawals: list["Withdrawals"] = Relationship(back_populates="invoice")


class Withdrawals(SQLModel, table=True):
    __tablename__ = "withdrawals"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity: str
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    contractor_company: str
    contractor_id: str = Field(foreign_key="public.users.id")
    contractor_name: str
    cost_total: float = Field(sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    invoice_id: str | None = Field(
        foreign_key="public.invoices.id", default=None
    )
    items: str | None = Field(default=None)
    job_id: str
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    paid_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    payment_status: str
    processed_by_id: str = Field(foreign_key="public.users.id")
    processed_by_name: str
    service_address: str
    subtotal: float = Field(sa_type=Float)
    tax: float = Field(sa_type=Float)
    tax_rate: float = Field(sa_type=Float)
    total: float = Field(sa_type=Float)

    billing_entity_rel: Optional["BillingEntities"] = Relationship(
        back_populates="withdrawals"
    )
    contractor: Optional["Users"] = Relationship(
        back_populates="withdrawals",
        sa_relationship_kwargs={"foreign_keys": "Withdrawals.contractor_id"},
    )
    invoice: Optional["Invoices"] = Relationship(back_populates="withdrawals")
    organization: Optional["Organizations"] = Relationship(
        back_populates="withdrawals"
    )
    processed_by: Optional["Users"] = Relationship(
        back_populates="processed_by_withdrawals",
        sa_relationship_kwargs={"foreign_keys": "Withdrawals.processed_by_id"},
    )
    invoices: list["Invoices"] = Relationship(
        back_populates="withdrawals", link_model=InvoiceWithdrawals
    )
    material_requests: list["MaterialRequests"] = Relationship(
        back_populates="withdrawal"
    )
    payments: list["Payments"] = Relationship(
        back_populates="withdrawals", link_model=PaymentWithdrawals
    )
    returns: list["Returns"] = Relationship(back_populates="withdrawal")
    withdrawal_items: list["WithdrawalItems"] = Relationship(
        back_populates="withdrawal"
    )


class MaterialRequests(SQLModel, table=True):
    __tablename__ = "material_requests"
    __table_args__ = {"schema": "public", "extend_existing": True}

    contractor_id: str = Field(foreign_key="public.users.id")
    contractor_name: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    job_id: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    organization_id: str = Field(foreign_key="public.organizations.id")
    processed_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    processed_by_id: str | None = Field(
        foreign_key="public.users.id", default=None
    )
    service_address: str | None = Field(default=None)
    status: str
    withdrawal_id: str | None = Field(
        foreign_key="public.withdrawals.id", default=None
    )

    contractor: Optional["Users"] = Relationship(
        back_populates="material_requests",
        sa_relationship_kwargs={
            "foreign_keys": "MaterialRequests.contractor_id"
        },
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="material_requests"
    )
    processed_by: Optional["Users"] = Relationship(
        back_populates="processed_by_material_requests",
        sa_relationship_kwargs={
            "foreign_keys": "MaterialRequests.processed_by_id"
        },
    )
    withdrawal: Optional["Withdrawals"] = Relationship(
        back_populates="material_requests"
    )
    material_request_items: list["MaterialRequestItems"] = Relationship(
        back_populates="material_request"
    )


class MaterialRequestItems(SQLModel, table=True):
    __tablename__ = "material_request_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    cost: float = Field(sa_type=Float)
    id: str = Field(primary_key=True)
    material_request_id: str = Field(foreign_key="public.material_requests.id")
    name: str
    quantity: float = Field(sa_type=Float)
    sku: str
    sku_id: str
    unit: str
    unit_price: float = Field(sa_type=Float)

    material_request: Optional["MaterialRequests"] = Relationship(
        back_populates="material_request_items"
    )


class Returns(SQLModel, table=True):
    __tablename__ = "returns"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity: str
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    contractor_id: str = Field(foreign_key="public.users.id")
    contractor_name: str
    cost_total: float = Field(sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    credit_note_id: str | None = Field(default=None)
    id: str = Field(primary_key=True)
    job_id: str
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    processed_by_id: str
    processed_by_name: str
    reason: str
    subtotal: float = Field(sa_type=Float)
    tax: float = Field(sa_type=Float)
    total: float = Field(sa_type=Float)
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    withdrawal_id: str = Field(foreign_key="public.withdrawals.id")

    billing_entity_rel: Optional["BillingEntities"] = Relationship(
        back_populates="returns"
    )
    contractor: Optional["Users"] = Relationship(back_populates="returns")
    organization: Optional["Organizations"] = Relationship(
        back_populates="returns"
    )
    withdrawal: Optional["Withdrawals"] = Relationship(back_populates="returns")
    return_items: list["ReturnItems"] = Relationship(
        back_populates="return_ref"
    )


class WithdrawalItems(SQLModel, table=True):
    __tablename__ = "withdrawal_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount: float = Field(sa_type=Float)
    cost: float = Field(sa_type=Float)
    cost_total: float = Field(sa_type=Float)
    id: str = Field(primary_key=True)
    name: str
    quantity: float = Field(sa_type=Float)
    sell_cost: float = Field(sa_type=Float)
    sell_uom: str
    sku: str
    sku_id: str
    unit: str
    unit_price: float = Field(sa_type=Float)
    withdrawal_id: str = Field(foreign_key="public.withdrawals.id")

    withdrawal: Optional["Withdrawals"] = Relationship(
        back_populates="withdrawal_items"
    )


class ReturnItems(SQLModel, table=True):
    __tablename__ = "return_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount: float = Field(sa_type=Float)
    cost: float = Field(sa_type=Float)
    cost_total: float = Field(sa_type=Float)
    id: str = Field(primary_key=True)
    name: str
    quantity: float = Field(sa_type=Float)
    return_id: str = Field(foreign_key="public.returns.id")
    sell_cost: float = Field(sa_type=Float)
    sell_uom: str
    sku: str
    sku_id: str
    unit: str
    unit_price: float = Field(sa_type=Float)

    return_ref: Optional["Returns"] = Relationship(
        back_populates="return_items"
    )


class InvoiceLineItems(SQLModel, table=True):
    __tablename__ = "invoice_line_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount: float = Field(sa_type=Float)
    cost: float = Field(sa_type=Float)
    description: str
    id: str = Field(primary_key=True)
    invoice_id: str = Field(foreign_key="public.invoices.id")
    job_id: str | None = Field(default=None)
    quantity: float = Field(sa_type=Float)
    sell_cost: float = Field(sa_type=Float)
    sku_id: str | None = Field(default=None)
    unit: str
    unit_price: float = Field(sa_type=Float)

    invoice: Optional["Invoices"] = Relationship(
        back_populates="invoice_line_items"
    )


class InvoiceCounters(SQLModel, table=True):
    __tablename__ = "invoice_counters"
    __table_args__ = {"schema": "public", "extend_existing": True}

    counter: int
    key: str = Field(primary_key=True)


class CreditNotes(SQLModel, table=True):
    __tablename__ = "credit_notes"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity: str
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    credit_note_number: str
    id: str = Field(primary_key=True)
    invoice_id: str | None = Field(
        foreign_key="public.invoices.id", default=None
    )
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    return_id: str | None = Field(default=None)
    status: str
    subtotal: float = Field(sa_type=Float)
    tax: float = Field(sa_type=Float)
    total: float = Field(sa_type=Float)
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    xero_credit_note_id: str | None = Field(default=None)
    xero_sync_status: str

    billing_entity_rel: Optional["BillingEntities"] = Relationship(
        back_populates="credit_notes"
    )
    invoice: Optional["Invoices"] = Relationship(back_populates="credit_notes")
    organization: Optional["Organizations"] = Relationship(
        back_populates="credit_notes"
    )
    credit_note_line_items: list["CreditNoteLineItems"] = Relationship(
        back_populates="credit_note"
    )


class CreditNoteLineItems(SQLModel, table=True):
    __tablename__ = "credit_note_line_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount: float = Field(sa_type=Float)
    cost: float = Field(sa_type=Float)
    credit_note_id: str = Field(foreign_key="public.credit_notes.id")
    description: str
    id: str = Field(primary_key=True)
    quantity: float = Field(sa_type=Float)
    sell_cost: float = Field(sa_type=Float)
    sku_id: str | None = Field(default=None)
    unit: str
    unit_price: float = Field(sa_type=Float)

    credit_note: Optional["CreditNotes"] = Relationship(
        back_populates="credit_note_line_items"
    )


class Payments(SQLModel, table=True):
    __tablename__ = "payments"
    __table_args__ = {"schema": "public", "extend_existing": True}

    amount: float = Field(sa_type=Float)
    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    invoice_id: str | None = Field(
        foreign_key="public.invoices.id", default=None
    )
    method: str
    notes: str | None = Field(default=None)
    organization_id: str = Field(foreign_key="public.organizations.id")
    payment_date: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    recorded_by_id: str = Field(foreign_key="public.users.id")
    reference: str
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    xero_payment_id: str | None = Field(default=None)

    billing_entity: Optional["BillingEntities"] = Relationship(
        back_populates="payments"
    )
    invoice: Optional["Invoices"] = Relationship(back_populates="payments")
    organization: Optional["Organizations"] = Relationship(
        back_populates="payments"
    )
    recorded_by: Optional["Users"] = Relationship(back_populates="payments")
    withdrawals: list["Withdrawals"] = Relationship(
        back_populates="payments", link_model=PaymentWithdrawals
    )


class FinancialLedger(SQLModel, table=True):
    __tablename__ = "financial_ledger"
    __table_args__ = {"schema": "public", "extend_existing": True}

    account: str
    amount: float = Field(sa_type=Float)
    billing_entity: str | None = Field(default=None)
    billing_entity_id: str | None = Field(default=None)
    contractor_id: str | None = Field(default=None)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    department: str | None = Field(default=None)
    id: str = Field(primary_key=True)
    job_id: str | None = Field(default=None)
    journal_id: str | None = Field(default=None)
    organization_id: str | None = Field(default=None)
    performed_by_user_id: str | None = Field(default=None)
    quantity: float | None = Field(default=None, sa_type=Float)
    reference_id: str
    reference_type: str
    sku_id: str | None = Field(default=None)
    unit: str | None = Field(default=None)
    unit_cost: float | None = Field(default=None, sa_type=Float)
    vendor_name: str | None = Field(default=None)


class PurchaseOrders(SQLModel, table=True):
    __tablename__ = "purchase_orders"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    created_by_id: str
    created_by_name: str
    document_date: str | None = Field(default=None)
    document_id: str | None = Field(default=None)
    id: str = Field(primary_key=True)
    notes: str | None = Field(default=None)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    received_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    received_by_id: str | None = Field(default=None)
    received_by_name: str | None = Field(default=None)
    status: str
    total: float | None = Field(default=None, sa_type=Float)
    updated_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    vendor_id: str | None = Field(foreign_key="public.vendors.id", default=None)
    vendor_name: str
    xero_bill_id: str | None = Field(default=None)
    xero_sync_status: str

    organization: Optional["Organizations"] = Relationship(
        back_populates="purchase_orders"
    )
    vendor: Optional["Vendors"] = Relationship(back_populates="purchase_orders")
    documents: list["Documents"] = Relationship(back_populates="po")
    purchase_order_items: list["PurchaseOrderItems"] = Relationship(
        back_populates="po"
    )


class PurchaseOrderItems(SQLModel, table=True):
    __tablename__ = "purchase_order_items"
    __table_args__ = {"schema": "public", "extend_existing": True}

    base_unit: str
    cost: float = Field(sa_type=Float)
    delivered_qty: float | None = Field(default=None, sa_type=Float)
    id: str = Field(primary_key=True)
    name: str
    ordered_qty: float = Field(sa_type=Float)
    organization_id: str | None = Field(
        foreign_key="public.organizations.id", default=None
    )
    original_sku: str | None = Field(default=None)
    pack_qty: int
    po_id: str = Field(foreign_key="public.purchase_orders.id")
    purchase_pack_qty: int
    purchase_uom: str
    sell_uom: str
    sku_id: str | None = Field(default=None)
    status: str
    suggested_department: str
    unit_price: float = Field(sa_type=Float)

    organization: Optional["Organizations"] = Relationship(
        back_populates="purchase_order_items"
    )
    po: Optional["PurchaseOrders"] = Relationship(
        back_populates="purchase_order_items"
    )


class Documents(SQLModel, table=True):
    __tablename__ = "documents"
    __table_args__ = {"schema": "public", "extend_existing": True}

    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    document_type: str
    file_hash: str
    file_size: int
    filename: str
    id: str = Field(primary_key=True)
    mime_type: str
    organization_id: str = Field(foreign_key="public.organizations.id")
    parsed_data: str | None = Field(default=None)
    po_id: str | None = Field(
        foreign_key="public.purchase_orders.id", default=None
    )
    status: str
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    uploaded_by_id: str = Field(foreign_key="public.users.id")
    vendor_name: str | None = Field(default=None)

    organization: Optional["Organizations"] = Relationship(
        back_populates="documents"
    )
    po: Optional["PurchaseOrders"] = Relationship(back_populates="documents")
    uploaded_by: Optional["Users"] = Relationship(back_populates="documents")


class Jobs(SQLModel, table=True):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "public", "extend_existing": True}

    billing_entity_id: str | None = Field(
        foreign_key="public.billing_entities.id", default=None
    )
    code: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    id: str = Field(primary_key=True)
    name: str
    notes: str | None = Field(default=None)
    organization_id: str = Field(foreign_key="public.organizations.id")
    service_address: str
    status: str
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))

    billing_entity: Optional["BillingEntities"] = Relationship(
        back_populates="jobs"
    )
    organization: Optional["Organizations"] = Relationship(
        back_populates="jobs"
    )


class MemoryArtifacts(SQLModel, table=True):
    __tablename__ = "memory_artifacts"
    __table_args__ = {"schema": "public", "extend_existing": True}

    content: str
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    expires_at: datetime.datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True)
    )
    id: str = Field(primary_key=True)
    org_id: str = Field(foreign_key="public.organizations.id")
    session_id: str
    subject: str
    tags: str
    type: str
    user_id: str = Field(foreign_key="public.users.id")

    org: Optional["Organizations"] = Relationship(
        back_populates="memory_artifacts"
    )
    user: Optional["Users"] = Relationship(back_populates="memory_artifacts")


class AgentRuns(SQLModel, table=True):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "public", "extend_existing": True}

    agent_name: str
    attempts: int
    cost_usd: float = Field(sa_type=Float)
    created_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))
    duration_ms: int
    error: str | None = Field(default=None)
    error_kind: str | None = Field(default=None)
    handoff_from: str | None = Field(default=None)
    id: str = Field(primary_key=True)
    input_tokens: int
    mode: str | None = Field(default=None)
    model: str
    org_id: str = Field(foreign_key="public.organizations.id")
    output_tokens: int
    parent_run_id: str | None = Field(
        foreign_key="public.agent_runs.id", default=None
    )
    response_text: str | None = Field(default=None)
    session_id: str
    tool_calls: str
    user_id: str | None = Field(foreign_key="public.users.id", default=None)
    user_message: str | None = Field(default=None)
    validation_failures: str
    validation_passed: bool | None = Field(default=None)
    validation_scores: str

    org: Optional["Organizations"] = Relationship(back_populates="agent_runs")
    parent_run: Optional["AgentRuns"] = Relationship(
        back_populates="agent_runs",
        sa_relationship_kwargs={
            "foreign_keys": "AgentRuns.parent_run_id",
            "remote_side": "AgentRuns.id",
        },
    )
    user: Optional["Users"] = Relationship(back_populates="agent_runs")
    agent_runs: list["AgentRuns"] = Relationship(back_populates="parent_run")


class Embeddings(SQLModel, table=True):
    __tablename__ = "embeddings"
    __table_args__ = {"schema": "public", "extend_existing": True}

    content: str
    content_hash: str
    embedding: list = Field(sa_type=JSONB)
    entity_id: str
    entity_type: str
    id: str = Field(primary_key=True)
    org_id: str = Field(foreign_key="public.organizations.id")
    updated_at: datetime.datetime = Field(sa_type=DateTime(timezone=True))

    org: Optional["Organizations"] = Relationship(back_populates="embeddings")
