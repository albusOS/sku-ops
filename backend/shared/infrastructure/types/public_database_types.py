from __future__ import annotations

import datetime
import uuid
from typing import (
    Annotated,
    Any,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
)

from pydantic import BaseModel, Field

NetRequestStatus: TypeAlias = Literal["PENDING", "SUCCESS", "ERROR"]

RealtimeEqualityOp: TypeAlias = Literal["eq", "neq", "lt", "lte", "gt", "gte", "in"]

RealtimeAction: TypeAlias = Literal["INSERT", "UPDATE", "DELETE", "TRUNCATE", "ERROR"]

StorageBuckettype: TypeAlias = Literal["STANDARD", "ANALYTICS", "VECTOR"]

AuthFactorType: TypeAlias = Literal["totp", "webauthn", "phone"]

AuthFactorStatus: TypeAlias = Literal["unverified", "verified"]

AuthAalLevel: TypeAlias = Literal["aal1", "aal2", "aal3"]

AuthCodeChallengeMethod: TypeAlias = Literal["s256", "plain"]

AuthOneTimeTokenType: TypeAlias = Literal["confirmation_token", "reauthentication_token", "recovery_token", "email_change_token_new", "email_change_token_current", "phone_change_token"]

AuthOauthRegistrationType: TypeAlias = Literal["dynamic", "manual"]

AuthOauthAuthorizationStatus: TypeAlias = Literal["pending", "approved", "denied", "expired"]

AuthOauthResponseType: TypeAlias = Literal["code"]

AuthOauthClientType: TypeAlias = Literal["public", "confidential"]

class PublicOrganizations(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    slug: str = Field(alias="slug")

class PublicOrganizationsInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    slug: Annotated[str, Field(alias="slug")]

class PublicOrganizationsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    slug: NotRequired[Annotated[str, Field(alias="slug")]]

class PublicUsers(BaseModel):
    billing_entity: str | None = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    company: str | None = Field(alias="company")
    created_at: datetime.datetime = Field(alias="created_at")
    email: str = Field(alias="email")
    id: uuid.UUID = Field(alias="id")
    is_active: bool = Field(alias="is_active")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    password: str = Field(alias="password")
    phone: str | None = Field(alias="phone")
    role: str = Field(alias="role")

class PublicUsersInsert(TypedDict):
    billing_entity: NotRequired[Annotated[str | None, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    company: NotRequired[Annotated[str | None, Field(alias="company")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    email: Annotated[str, Field(alias="email")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    is_active: NotRequired[Annotated[bool, Field(alias="is_active")]]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    password: Annotated[str, Field(alias="password")]
    phone: NotRequired[Annotated[str | None, Field(alias="phone")]]
    role: NotRequired[Annotated[str, Field(alias="role")]]

class PublicUsersUpdate(TypedDict):
    billing_entity: NotRequired[Annotated[str | None, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    company: NotRequired[Annotated[str | None, Field(alias="company")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    email: NotRequired[Annotated[str, Field(alias="email")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    is_active: NotRequired[Annotated[bool, Field(alias="is_active")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    password: NotRequired[Annotated[str, Field(alias="password")]]
    phone: NotRequired[Annotated[str | None, Field(alias="phone")]]
    role: NotRequired[Annotated[str, Field(alias="role")]]

class PublicOrgSettings(BaseModel):
    auto_invoice: bool = Field(alias="auto_invoice")
    default_tax_rate: float = Field(alias="default_tax_rate")
    organization_id: uuid.UUID = Field(alias="organization_id")
    updated_at: datetime.datetime | None = Field(alias="updated_at")
    xero_access_token: str | None = Field(alias="xero_access_token")
    xero_ap_account_code: str = Field(alias="xero_ap_account_code")
    xero_cogs_account_code: str = Field(alias="xero_cogs_account_code")
    xero_inventory_account_code: str = Field(alias="xero_inventory_account_code")
    xero_refresh_token: str | None = Field(alias="xero_refresh_token")
    xero_sales_account_code: str = Field(alias="xero_sales_account_code")
    xero_tax_type: str = Field(alias="xero_tax_type")
    xero_tenant_id: str | None = Field(alias="xero_tenant_id")
    xero_token_expiry: str | None = Field(alias="xero_token_expiry")
    xero_tracking_category_id: str | None = Field(alias="xero_tracking_category_id")

class PublicOrgSettingsInsert(TypedDict):
    auto_invoice: NotRequired[Annotated[bool, Field(alias="auto_invoice")]]
    default_tax_rate: NotRequired[Annotated[float, Field(alias="default_tax_rate")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    updated_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="updated_at")]]
    xero_access_token: NotRequired[Annotated[str | None, Field(alias="xero_access_token")]]
    xero_ap_account_code: NotRequired[Annotated[str, Field(alias="xero_ap_account_code")]]
    xero_cogs_account_code: NotRequired[Annotated[str, Field(alias="xero_cogs_account_code")]]
    xero_inventory_account_code: NotRequired[Annotated[str, Field(alias="xero_inventory_account_code")]]
    xero_refresh_token: NotRequired[Annotated[str | None, Field(alias="xero_refresh_token")]]
    xero_sales_account_code: NotRequired[Annotated[str, Field(alias="xero_sales_account_code")]]
    xero_tax_type: NotRequired[Annotated[str, Field(alias="xero_tax_type")]]
    xero_tenant_id: NotRequired[Annotated[str | None, Field(alias="xero_tenant_id")]]
    xero_token_expiry: NotRequired[Annotated[str | None, Field(alias="xero_token_expiry")]]
    xero_tracking_category_id: NotRequired[Annotated[str | None, Field(alias="xero_tracking_category_id")]]

class PublicOrgSettingsUpdate(TypedDict):
    auto_invoice: NotRequired[Annotated[bool, Field(alias="auto_invoice")]]
    default_tax_rate: NotRequired[Annotated[float, Field(alias="default_tax_rate")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    updated_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="updated_at")]]
    xero_access_token: NotRequired[Annotated[str | None, Field(alias="xero_access_token")]]
    xero_ap_account_code: NotRequired[Annotated[str, Field(alias="xero_ap_account_code")]]
    xero_cogs_account_code: NotRequired[Annotated[str, Field(alias="xero_cogs_account_code")]]
    xero_inventory_account_code: NotRequired[Annotated[str, Field(alias="xero_inventory_account_code")]]
    xero_refresh_token: NotRequired[Annotated[str | None, Field(alias="xero_refresh_token")]]
    xero_sales_account_code: NotRequired[Annotated[str, Field(alias="xero_sales_account_code")]]
    xero_tax_type: NotRequired[Annotated[str, Field(alias="xero_tax_type")]]
    xero_tenant_id: NotRequired[Annotated[str | None, Field(alias="xero_tenant_id")]]
    xero_token_expiry: NotRequired[Annotated[str | None, Field(alias="xero_token_expiry")]]
    xero_tracking_category_id: NotRequired[Annotated[str | None, Field(alias="xero_tracking_category_id")]]

class PublicRefreshTokens(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    expires_at: datetime.datetime = Field(alias="expires_at")
    id: uuid.UUID = Field(alias="id")
    revoked: bool = Field(alias="revoked")
    token_hash: str = Field(alias="token_hash")
    user_id: uuid.UUID = Field(alias="user_id")

class PublicRefreshTokensInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    expires_at: Annotated[datetime.datetime, Field(alias="expires_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    revoked: NotRequired[Annotated[bool, Field(alias="revoked")]]
    token_hash: Annotated[str, Field(alias="token_hash")]
    user_id: Annotated[uuid.UUID, Field(alias="user_id")]

class PublicRefreshTokensUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    expires_at: NotRequired[Annotated[datetime.datetime, Field(alias="expires_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    revoked: NotRequired[Annotated[bool, Field(alias="revoked")]]
    token_hash: NotRequired[Annotated[str, Field(alias="token_hash")]]
    user_id: NotRequired[Annotated[uuid.UUID, Field(alias="user_id")]]

class PublicOauthStates(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    org_id: uuid.UUID = Field(alias="org_id")
    state: str = Field(alias="state")

class PublicOauthStatesInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    org_id: Annotated[uuid.UUID, Field(alias="org_id")]
    state: Annotated[str, Field(alias="state")]

class PublicOauthStatesUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    org_id: NotRequired[Annotated[uuid.UUID, Field(alias="org_id")]]
    state: NotRequired[Annotated[str, Field(alias="state")]]

class PublicAuditLog(BaseModel):
    action: str = Field(alias="action")
    created_at: datetime.datetime = Field(alias="created_at")
    details: str | None = Field(alias="details")
    id: uuid.UUID = Field(alias="id")
    ip_address: str | None = Field(alias="ip_address")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    resource_id: str | None = Field(alias="resource_id")
    resource_type: str | None = Field(alias="resource_type")
    user_id: uuid.UUID | None = Field(alias="user_id")

class PublicAuditLogInsert(TypedDict):
    action: Annotated[str, Field(alias="action")]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    details: NotRequired[Annotated[str | None, Field(alias="details")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    ip_address: NotRequired[Annotated[str | None, Field(alias="ip_address")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    resource_id: NotRequired[Annotated[str | None, Field(alias="resource_id")]]
    resource_type: NotRequired[Annotated[str | None, Field(alias="resource_type")]]
    user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="user_id")]]

class PublicAuditLogUpdate(TypedDict):
    action: NotRequired[Annotated[str, Field(alias="action")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    details: NotRequired[Annotated[str | None, Field(alias="details")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    ip_address: NotRequired[Annotated[str | None, Field(alias="ip_address")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    resource_id: NotRequired[Annotated[str | None, Field(alias="resource_id")]]
    resource_type: NotRequired[Annotated[str | None, Field(alias="resource_type")]]
    user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="user_id")]]

class PublicBillingEntities(BaseModel):
    billing_address: str = Field(alias="billing_address")
    contact_email: str = Field(alias="contact_email")
    contact_name: str = Field(alias="contact_name")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    is_active: bool = Field(alias="is_active")
    name: str = Field(alias="name")
    organization_id: uuid.UUID = Field(alias="organization_id")
    payment_terms: str = Field(alias="payment_terms")
    updated_at: datetime.datetime = Field(alias="updated_at")
    xero_contact_id: str | None = Field(alias="xero_contact_id")

class PublicBillingEntitiesInsert(TypedDict):
    billing_address: NotRequired[Annotated[str, Field(alias="billing_address")]]
    contact_email: NotRequired[Annotated[str, Field(alias="contact_email")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    is_active: NotRequired[Annotated[bool, Field(alias="is_active")]]
    name: Annotated[str, Field(alias="name")]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    payment_terms: NotRequired[Annotated[str, Field(alias="payment_terms")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    xero_contact_id: NotRequired[Annotated[str | None, Field(alias="xero_contact_id")]]

class PublicBillingEntitiesUpdate(TypedDict):
    billing_address: NotRequired[Annotated[str, Field(alias="billing_address")]]
    contact_email: NotRequired[Annotated[str, Field(alias="contact_email")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    is_active: NotRequired[Annotated[bool, Field(alias="is_active")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    payment_terms: NotRequired[Annotated[str, Field(alias="payment_terms")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    xero_contact_id: NotRequired[Annotated[str | None, Field(alias="xero_contact_id")]]

class PublicAddresses(BaseModel):
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    city: str = Field(alias="city")
    country: str = Field(alias="country")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    job_id: uuid.UUID | None = Field(alias="job_id")
    label: str = Field(alias="label")
    line1: str = Field(alias="line1")
    line2: str = Field(alias="line2")
    organization_id: uuid.UUID = Field(alias="organization_id")
    postal_code: str = Field(alias="postal_code")
    state: str = Field(alias="state")

class PublicAddressesInsert(TypedDict):
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    city: NotRequired[Annotated[str, Field(alias="city")]]
    country: NotRequired[Annotated[str, Field(alias="country")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    label: NotRequired[Annotated[str, Field(alias="label")]]
    line1: NotRequired[Annotated[str, Field(alias="line1")]]
    line2: NotRequired[Annotated[str, Field(alias="line2")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    postal_code: NotRequired[Annotated[str, Field(alias="postal_code")]]
    state: NotRequired[Annotated[str, Field(alias="state")]]

class PublicAddressesUpdate(TypedDict):
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    city: NotRequired[Annotated[str, Field(alias="city")]]
    country: NotRequired[Annotated[str, Field(alias="country")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    label: NotRequired[Annotated[str, Field(alias="label")]]
    line1: NotRequired[Annotated[str, Field(alias="line1")]]
    line2: NotRequired[Annotated[str, Field(alias="line2")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    postal_code: NotRequired[Annotated[str, Field(alias="postal_code")]]
    state: NotRequired[Annotated[str, Field(alias="state")]]

class PublicFiscalPeriods(BaseModel):
    closed_at: datetime.datetime | None = Field(alias="closed_at")
    closed_by_id: uuid.UUID | None = Field(alias="closed_by_id")
    created_at: datetime.datetime = Field(alias="created_at")
    end_date: datetime.date = Field(alias="end_date")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: uuid.UUID = Field(alias="organization_id")
    start_date: datetime.date = Field(alias="start_date")
    status: str = Field(alias="status")

class PublicFiscalPeriodsInsert(TypedDict):
    closed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="closed_at")]]
    closed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="closed_by_id")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    end_date: Annotated[datetime.date, Field(alias="end_date")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    start_date: Annotated[datetime.date, Field(alias="start_date")]
    status: NotRequired[Annotated[str, Field(alias="status")]]

class PublicFiscalPeriodsUpdate(TypedDict):
    closed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="closed_at")]]
    closed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="closed_by_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    end_date: NotRequired[Annotated[datetime.date, Field(alias="end_date")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    start_date: NotRequired[Annotated[datetime.date, Field(alias="start_date")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]

class PublicProcessedEvents(BaseModel):
    event_id: uuid.UUID = Field(alias="event_id")
    event_type: str = Field(alias="event_type")
    handler_name: str = Field(alias="handler_name")
    processed_at: datetime.datetime = Field(alias="processed_at")

class PublicProcessedEventsInsert(TypedDict):
    event_id: Annotated[uuid.UUID, Field(alias="event_id")]
    event_type: Annotated[str, Field(alias="event_type")]
    handler_name: Annotated[str, Field(alias="handler_name")]
    processed_at: Annotated[datetime.datetime, Field(alias="processed_at")]

class PublicProcessedEventsUpdate(TypedDict):
    event_id: NotRequired[Annotated[uuid.UUID, Field(alias="event_id")]]
    event_type: NotRequired[Annotated[str, Field(alias="event_type")]]
    handler_name: NotRequired[Annotated[str, Field(alias="handler_name")]]
    processed_at: NotRequired[Annotated[datetime.datetime, Field(alias="processed_at")]]

class PublicDepartments(BaseModel):
    code: str = Field(alias="code")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    description: str = Field(alias="description")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    sku_count: int = Field(alias="sku_count")

class PublicDepartmentsInsert(TypedDict):
    code: Annotated[str, Field(alias="code")]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    sku_count: NotRequired[Annotated[int, Field(alias="sku_count")]]

class PublicDepartmentsUpdate(TypedDict):
    code: NotRequired[Annotated[str, Field(alias="code")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    sku_count: NotRequired[Annotated[int, Field(alias="sku_count")]]

class PublicUnitsOfMeasure(BaseModel):
    code: str = Field(alias="code")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    family: str = Field(alias="family")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")

class PublicUnitsOfMeasureInsert(TypedDict):
    code: Annotated[str, Field(alias="code")]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    family: NotRequired[Annotated[str, Field(alias="family")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]

class PublicUnitsOfMeasureUpdate(TypedDict):
    code: NotRequired[Annotated[str, Field(alias="code")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    family: NotRequired[Annotated[str, Field(alias="family")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]

class PublicVendors(BaseModel):
    address: str = Field(alias="address")
    contact_name: str = Field(alias="contact_name")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    email: str = Field(alias="email")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    phone: str = Field(alias="phone")

class PublicVendorsInsert(TypedDict):
    address: NotRequired[Annotated[str, Field(alias="address")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    email: NotRequired[Annotated[str, Field(alias="email")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    phone: NotRequired[Annotated[str, Field(alias="phone")]]

class PublicVendorsUpdate(TypedDict):
    address: NotRequired[Annotated[str, Field(alias="address")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    email: NotRequired[Annotated[str, Field(alias="email")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    phone: NotRequired[Annotated[str, Field(alias="phone")]]

class PublicProducts(BaseModel):
    category_id: uuid.UUID = Field(alias="category_id")
    category_name: str = Field(alias="category_name")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    description: str = Field(alias="description")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    sku_count: int = Field(alias="sku_count")
    updated_at: datetime.datetime = Field(alias="updated_at")

class PublicProductsInsert(TypedDict):
    category_id: Annotated[uuid.UUID, Field(alias="category_id")]
    category_name: NotRequired[Annotated[str, Field(alias="category_name")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    sku_count: NotRequired[Annotated[int, Field(alias="sku_count")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]

class PublicProductsUpdate(TypedDict):
    category_id: NotRequired[Annotated[uuid.UUID, Field(alias="category_id")]]
    category_name: NotRequired[Annotated[str, Field(alias="category_name")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    sku_count: NotRequired[Annotated[int, Field(alias="sku_count")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]

class PublicSkus(BaseModel):
    barcode: str | None = Field(alias="barcode")
    base_unit: str = Field(alias="base_unit")
    category_id: uuid.UUID = Field(alias="category_id")
    category_name: str = Field(alias="category_name")
    cost: float = Field(alias="cost")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    description: str = Field(alias="description")
    grade: str = Field(alias="grade")
    id: uuid.UUID = Field(alias="id")
    min_stock: int = Field(alias="min_stock")
    name: str = Field(alias="name")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    pack_qty: int = Field(alias="pack_qty")
    price: float = Field(alias="price")
    product_family_id: uuid.UUID = Field(alias="product_family_id")
    purchase_pack_qty: int = Field(alias="purchase_pack_qty")
    purchase_uom: str = Field(alias="purchase_uom")
    quantity: float = Field(alias="quantity")
    sell_uom: str = Field(alias="sell_uom")
    sku: str = Field(alias="sku")
    spec: str = Field(alias="spec")
    updated_at: datetime.datetime = Field(alias="updated_at")
    variant_attrs: str = Field(alias="variant_attrs")
    variant_label: str = Field(alias="variant_label")
    vendor_barcode: str | None = Field(alias="vendor_barcode")

class PublicSkusInsert(TypedDict):
    barcode: NotRequired[Annotated[str | None, Field(alias="barcode")]]
    base_unit: NotRequired[Annotated[str, Field(alias="base_unit")]]
    category_id: Annotated[uuid.UUID, Field(alias="category_id")]
    category_name: NotRequired[Annotated[str, Field(alias="category_name")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    grade: NotRequired[Annotated[str, Field(alias="grade")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    min_stock: NotRequired[Annotated[int, Field(alias="min_stock")]]
    name: Annotated[str, Field(alias="name")]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    pack_qty: NotRequired[Annotated[int, Field(alias="pack_qty")]]
    price: Annotated[float, Field(alias="price")]
    product_family_id: Annotated[uuid.UUID, Field(alias="product_family_id")]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: Annotated[str, Field(alias="sku")]
    spec: NotRequired[Annotated[str, Field(alias="spec")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    variant_attrs: NotRequired[Annotated[str, Field(alias="variant_attrs")]]
    variant_label: NotRequired[Annotated[str, Field(alias="variant_label")]]
    vendor_barcode: NotRequired[Annotated[str | None, Field(alias="vendor_barcode")]]

class PublicSkusUpdate(TypedDict):
    barcode: NotRequired[Annotated[str | None, Field(alias="barcode")]]
    base_unit: NotRequired[Annotated[str, Field(alias="base_unit")]]
    category_id: NotRequired[Annotated[uuid.UUID, Field(alias="category_id")]]
    category_name: NotRequired[Annotated[str, Field(alias="category_name")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    grade: NotRequired[Annotated[str, Field(alias="grade")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    min_stock: NotRequired[Annotated[int, Field(alias="min_stock")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    pack_qty: NotRequired[Annotated[int, Field(alias="pack_qty")]]
    price: NotRequired[Annotated[float, Field(alias="price")]]
    product_family_id: NotRequired[Annotated[uuid.UUID, Field(alias="product_family_id")]]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    spec: NotRequired[Annotated[str, Field(alias="spec")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    variant_attrs: NotRequired[Annotated[str, Field(alias="variant_attrs")]]
    variant_label: NotRequired[Annotated[str, Field(alias="variant_label")]]
    vendor_barcode: NotRequired[Annotated[str | None, Field(alias="vendor_barcode")]]

class PublicVendorItems(BaseModel):
    cost: float = Field(alias="cost")
    created_at: datetime.datetime = Field(alias="created_at")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    id: uuid.UUID = Field(alias="id")
    is_preferred: bool = Field(alias="is_preferred")
    lead_time_days: int | None = Field(alias="lead_time_days")
    moq: float | None = Field(alias="moq")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    purchase_pack_qty: int = Field(alias="purchase_pack_qty")
    purchase_uom: str = Field(alias="purchase_uom")
    sku_id: uuid.UUID = Field(alias="sku_id")
    updated_at: datetime.datetime = Field(alias="updated_at")
    vendor_id: uuid.UUID = Field(alias="vendor_id")
    vendor_name: str = Field(alias="vendor_name")
    vendor_sku: str | None = Field(alias="vendor_sku")

class PublicVendorItemsInsert(TypedDict):
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    is_preferred: NotRequired[Annotated[bool, Field(alias="is_preferred")]]
    lead_time_days: NotRequired[Annotated[int | None, Field(alias="lead_time_days")]]
    moq: NotRequired[Annotated[float | None, Field(alias="moq")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    vendor_id: Annotated[uuid.UUID, Field(alias="vendor_id")]
    vendor_name: NotRequired[Annotated[str, Field(alias="vendor_name")]]
    vendor_sku: NotRequired[Annotated[str | None, Field(alias="vendor_sku")]]

class PublicVendorItemsUpdate(TypedDict):
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    is_preferred: NotRequired[Annotated[bool, Field(alias="is_preferred")]]
    lead_time_days: NotRequired[Annotated[int | None, Field(alias="lead_time_days")]]
    moq: NotRequired[Annotated[float | None, Field(alias="moq")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    vendor_id: NotRequired[Annotated[uuid.UUID, Field(alias="vendor_id")]]
    vendor_name: NotRequired[Annotated[str, Field(alias="vendor_name")]]
    vendor_sku: NotRequired[Annotated[str | None, Field(alias="vendor_sku")]]

class PublicSkuCounters(BaseModel):
    counter: int = Field(alias="counter")
    organization_id: uuid.UUID = Field(alias="organization_id")
    product_family_id: uuid.UUID = Field(alias="product_family_id")

class PublicSkuCountersInsert(TypedDict):
    counter: NotRequired[Annotated[int, Field(alias="counter")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    product_family_id: Annotated[uuid.UUID, Field(alias="product_family_id")]

class PublicSkuCountersUpdate(TypedDict):
    counter: NotRequired[Annotated[int, Field(alias="counter")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    product_family_id: NotRequired[Annotated[uuid.UUID, Field(alias="product_family_id")]]

class PublicStockTransactions(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    organization_id: uuid.UUID = Field(alias="organization_id")
    original_quantity: float | None = Field(alias="original_quantity")
    original_unit: str | None = Field(alias="original_unit")
    product_name: str = Field(alias="product_name")
    quantity_after: float = Field(alias="quantity_after")
    quantity_before: float = Field(alias="quantity_before")
    quantity_delta: float = Field(alias="quantity_delta")
    reason: str | None = Field(alias="reason")
    reference_id: str | None = Field(alias="reference_id")
    reference_type: str | None = Field(alias="reference_type")
    sku: str = Field(alias="sku")
    sku_id: uuid.UUID = Field(alias="sku_id")
    transaction_type: str = Field(alias="transaction_type")
    unit: str = Field(alias="unit")
    user_id: uuid.UUID = Field(alias="user_id")
    user_name: str = Field(alias="user_name")

class PublicStockTransactionsInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    original_quantity: NotRequired[Annotated[float | None, Field(alias="original_quantity")]]
    original_unit: NotRequired[Annotated[str | None, Field(alias="original_unit")]]
    product_name: NotRequired[Annotated[str, Field(alias="product_name")]]
    quantity_after: Annotated[float, Field(alias="quantity_after")]
    quantity_before: Annotated[float, Field(alias="quantity_before")]
    quantity_delta: Annotated[float, Field(alias="quantity_delta")]
    reason: NotRequired[Annotated[str | None, Field(alias="reason")]]
    reference_id: NotRequired[Annotated[str | None, Field(alias="reference_id")]]
    reference_type: NotRequired[Annotated[str | None, Field(alias="reference_type")]]
    sku: Annotated[str, Field(alias="sku")]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    transaction_type: Annotated[str, Field(alias="transaction_type")]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    user_id: Annotated[uuid.UUID, Field(alias="user_id")]
    user_name: NotRequired[Annotated[str, Field(alias="user_name")]]

class PublicStockTransactionsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    original_quantity: NotRequired[Annotated[float | None, Field(alias="original_quantity")]]
    original_unit: NotRequired[Annotated[str | None, Field(alias="original_unit")]]
    product_name: NotRequired[Annotated[str, Field(alias="product_name")]]
    quantity_after: NotRequired[Annotated[float, Field(alias="quantity_after")]]
    quantity_before: NotRequired[Annotated[float, Field(alias="quantity_before")]]
    quantity_delta: NotRequired[Annotated[float, Field(alias="quantity_delta")]]
    reason: NotRequired[Annotated[str | None, Field(alias="reason")]]
    reference_id: NotRequired[Annotated[str | None, Field(alias="reference_id")]]
    reference_type: NotRequired[Annotated[str | None, Field(alias="reference_type")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    transaction_type: NotRequired[Annotated[str, Field(alias="transaction_type")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    user_id: NotRequired[Annotated[uuid.UUID, Field(alias="user_id")]]
    user_name: NotRequired[Annotated[str, Field(alias="user_name")]]

class PublicCycleCounts(BaseModel):
    committed_at: datetime.datetime | None = Field(alias="committed_at")
    committed_by_id: uuid.UUID | None = Field(alias="committed_by_id")
    created_at: datetime.datetime = Field(alias="created_at")
    created_by_id: uuid.UUID = Field(alias="created_by_id")
    created_by_name: str = Field(alias="created_by_name")
    id: uuid.UUID = Field(alias="id")
    organization_id: uuid.UUID = Field(alias="organization_id")
    scope: str | None = Field(alias="scope")
    status: str = Field(alias="status")

class PublicCycleCountsInsert(TypedDict):
    committed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="committed_at")]]
    committed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="committed_by_id")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    created_by_id: Annotated[uuid.UUID, Field(alias="created_by_id")]
    created_by_name: NotRequired[Annotated[str, Field(alias="created_by_name")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    scope: NotRequired[Annotated[str | None, Field(alias="scope")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]

class PublicCycleCountsUpdate(TypedDict):
    committed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="committed_at")]]
    committed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="committed_by_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    created_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="created_by_id")]]
    created_by_name: NotRequired[Annotated[str, Field(alias="created_by_name")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    scope: NotRequired[Annotated[str | None, Field(alias="scope")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]

class PublicCycleCountItems(BaseModel):
    counted_qty: float | None = Field(alias="counted_qty")
    created_at: datetime.datetime = Field(alias="created_at")
    cycle_count_id: uuid.UUID = Field(alias="cycle_count_id")
    id: uuid.UUID = Field(alias="id")
    notes: str | None = Field(alias="notes")
    product_name: str = Field(alias="product_name")
    sku: str = Field(alias="sku")
    sku_id: uuid.UUID = Field(alias="sku_id")
    snapshot_qty: float = Field(alias="snapshot_qty")
    unit: str = Field(alias="unit")
    variance: float | None = Field(alias="variance")

class PublicCycleCountItemsInsert(TypedDict):
    counted_qty: NotRequired[Annotated[float | None, Field(alias="counted_qty")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    cycle_count_id: Annotated[uuid.UUID, Field(alias="cycle_count_id")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    product_name: NotRequired[Annotated[str, Field(alias="product_name")]]
    sku: Annotated[str, Field(alias="sku")]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    snapshot_qty: Annotated[float, Field(alias="snapshot_qty")]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    variance: NotRequired[Annotated[float | None, Field(alias="variance")]]

class PublicCycleCountItemsUpdate(TypedDict):
    counted_qty: NotRequired[Annotated[float | None, Field(alias="counted_qty")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    cycle_count_id: NotRequired[Annotated[uuid.UUID, Field(alias="cycle_count_id")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    product_name: NotRequired[Annotated[str, Field(alias="product_name")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    snapshot_qty: NotRequired[Annotated[float, Field(alias="snapshot_qty")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    variance: NotRequired[Annotated[float | None, Field(alias="variance")]]

class PublicWithdrawals(BaseModel):
    billing_entity: str = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    contractor_company: str = Field(alias="contractor_company")
    contractor_id: uuid.UUID = Field(alias="contractor_id")
    contractor_name: str = Field(alias="contractor_name")
    cost_total: float = Field(alias="cost_total")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    invoice_id: uuid.UUID | None = Field(alias="invoice_id")
    items: str | None = Field(alias="items")
    job_id: uuid.UUID = Field(alias="job_id")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    paid_at: datetime.datetime | None = Field(alias="paid_at")
    payment_status: str = Field(alias="payment_status")
    processed_by_id: uuid.UUID = Field(alias="processed_by_id")
    processed_by_name: str = Field(alias="processed_by_name")
    service_address: str = Field(alias="service_address")
    subtotal: float = Field(alias="subtotal")
    tax: float = Field(alias="tax")
    tax_rate: float = Field(alias="tax_rate")
    total: float = Field(alias="total")

class PublicWithdrawalsInsert(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_company: NotRequired[Annotated[str, Field(alias="contractor_company")]]
    contractor_id: Annotated[uuid.UUID, Field(alias="contractor_id")]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    cost_total: Annotated[float, Field(alias="cost_total")]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    items: NotRequired[Annotated[str | None, Field(alias="items")]]
    job_id: Annotated[uuid.UUID, Field(alias="job_id")]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    paid_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="paid_at")]]
    payment_status: NotRequired[Annotated[str, Field(alias="payment_status")]]
    processed_by_id: Annotated[uuid.UUID, Field(alias="processed_by_id")]
    processed_by_name: NotRequired[Annotated[str, Field(alias="processed_by_name")]]
    service_address: Annotated[str, Field(alias="service_address")]
    subtotal: Annotated[float, Field(alias="subtotal")]
    tax: Annotated[float, Field(alias="tax")]
    tax_rate: NotRequired[Annotated[float, Field(alias="tax_rate")]]
    total: Annotated[float, Field(alias="total")]

class PublicWithdrawalsUpdate(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_company: NotRequired[Annotated[str, Field(alias="contractor_company")]]
    contractor_id: NotRequired[Annotated[uuid.UUID, Field(alias="contractor_id")]]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    items: NotRequired[Annotated[str | None, Field(alias="items")]]
    job_id: NotRequired[Annotated[uuid.UUID, Field(alias="job_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    paid_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="paid_at")]]
    payment_status: NotRequired[Annotated[str, Field(alias="payment_status")]]
    processed_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="processed_by_id")]]
    processed_by_name: NotRequired[Annotated[str, Field(alias="processed_by_name")]]
    service_address: NotRequired[Annotated[str, Field(alias="service_address")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    tax_rate: NotRequired[Annotated[float, Field(alias="tax_rate")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]

class PublicMaterialRequests(BaseModel):
    contractor_id: uuid.UUID = Field(alias="contractor_id")
    contractor_name: str = Field(alias="contractor_name")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    job_id: uuid.UUID | None = Field(alias="job_id")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID = Field(alias="organization_id")
    processed_at: datetime.datetime | None = Field(alias="processed_at")
    processed_by_id: uuid.UUID | None = Field(alias="processed_by_id")
    service_address: str | None = Field(alias="service_address")
    status: str = Field(alias="status")
    withdrawal_id: uuid.UUID | None = Field(alias="withdrawal_id")

class PublicMaterialRequestsInsert(TypedDict):
    contractor_id: Annotated[uuid.UUID, Field(alias="contractor_id")]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    processed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="processed_at")]]
    processed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="processed_by_id")]]
    service_address: NotRequired[Annotated[str | None, Field(alias="service_address")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="withdrawal_id")]]

class PublicMaterialRequestsUpdate(TypedDict):
    contractor_id: NotRequired[Annotated[uuid.UUID, Field(alias="contractor_id")]]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    processed_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="processed_at")]]
    processed_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="processed_by_id")]]
    service_address: NotRequired[Annotated[str | None, Field(alias="service_address")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="withdrawal_id")]]

class PublicMaterialRequestItems(BaseModel):
    cost: float = Field(alias="cost")
    id: uuid.UUID = Field(alias="id")
    material_request_id: uuid.UUID = Field(alias="material_request_id")
    name: str = Field(alias="name")
    quantity: float = Field(alias="quantity")
    sku: str = Field(alias="sku")
    sku_id: uuid.UUID = Field(alias="sku_id")
    unit: str = Field(alias="unit")
    unit_price: float = Field(alias="unit_price")

class PublicMaterialRequestItemsInsert(TypedDict):
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    material_request_id: Annotated[uuid.UUID, Field(alias="material_request_id")]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: Annotated[float, Field(alias="quantity")]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicMaterialRequestItemsUpdate(TypedDict):
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    material_request_id: NotRequired[Annotated[uuid.UUID, Field(alias="material_request_id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicReturns(BaseModel):
    billing_entity: str = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    contractor_id: uuid.UUID = Field(alias="contractor_id")
    contractor_name: str = Field(alias="contractor_name")
    cost_total: float = Field(alias="cost_total")
    created_at: datetime.datetime = Field(alias="created_at")
    credit_note_id: uuid.UUID | None = Field(alias="credit_note_id")
    id: uuid.UUID = Field(alias="id")
    job_id: uuid.UUID = Field(alias="job_id")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    processed_by_id: uuid.UUID = Field(alias="processed_by_id")
    processed_by_name: str = Field(alias="processed_by_name")
    reason: str = Field(alias="reason")
    subtotal: float = Field(alias="subtotal")
    tax: float = Field(alias="tax")
    total: float = Field(alias="total")
    updated_at: datetime.datetime = Field(alias="updated_at")
    withdrawal_id: uuid.UUID = Field(alias="withdrawal_id")

class PublicReturnsInsert(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_id: Annotated[uuid.UUID, Field(alias="contractor_id")]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    credit_note_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="credit_note_id")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    job_id: Annotated[uuid.UUID, Field(alias="job_id")]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    processed_by_id: Annotated[uuid.UUID, Field(alias="processed_by_id")]
    processed_by_name: NotRequired[Annotated[str, Field(alias="processed_by_name")]]
    reason: NotRequired[Annotated[str, Field(alias="reason")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    withdrawal_id: Annotated[uuid.UUID, Field(alias="withdrawal_id")]

class PublicReturnsUpdate(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_id: NotRequired[Annotated[uuid.UUID, Field(alias="contractor_id")]]
    contractor_name: NotRequired[Annotated[str, Field(alias="contractor_name")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    credit_note_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="credit_note_id")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    job_id: NotRequired[Annotated[uuid.UUID, Field(alias="job_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    processed_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="processed_by_id")]]
    processed_by_name: NotRequired[Annotated[str, Field(alias="processed_by_name")]]
    reason: NotRequired[Annotated[str, Field(alias="reason")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID, Field(alias="withdrawal_id")]]

class PublicWithdrawalItems(BaseModel):
    amount: float = Field(alias="amount")
    cost: float = Field(alias="cost")
    cost_total: float = Field(alias="cost_total")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    quantity: float = Field(alias="quantity")
    sell_cost: float = Field(alias="sell_cost")
    sell_uom: str = Field(alias="sell_uom")
    sku: str = Field(alias="sku")
    sku_id: uuid.UUID = Field(alias="sku_id")
    unit: str = Field(alias="unit")
    unit_price: float = Field(alias="unit_price")
    withdrawal_id: uuid.UUID = Field(alias="withdrawal_id")

class PublicWithdrawalItemsInsert(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: Annotated[float, Field(alias="quantity")]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]
    withdrawal_id: Annotated[uuid.UUID, Field(alias="withdrawal_id")]

class PublicWithdrawalItemsUpdate(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID, Field(alias="withdrawal_id")]]

class PublicReturnItems(BaseModel):
    amount: float = Field(alias="amount")
    cost: float = Field(alias="cost")
    cost_total: float = Field(alias="cost_total")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    quantity: float = Field(alias="quantity")
    return_id: uuid.UUID = Field(alias="return_id")
    sell_cost: float = Field(alias="sell_cost")
    sell_uom: str = Field(alias="sell_uom")
    sku: str = Field(alias="sku")
    sku_id: uuid.UUID = Field(alias="sku_id")
    unit: str = Field(alias="unit")
    unit_price: float = Field(alias="unit_price")

class PublicReturnItemsInsert(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: Annotated[float, Field(alias="quantity")]
    return_id: Annotated[uuid.UUID, Field(alias="return_id")]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: Annotated[uuid.UUID, Field(alias="sku_id")]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicReturnItemsUpdate(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    cost_total: NotRequired[Annotated[float, Field(alias="cost_total")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    return_id: NotRequired[Annotated[uuid.UUID, Field(alias="return_id")]]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku: NotRequired[Annotated[str, Field(alias="sku")]]
    sku_id: NotRequired[Annotated[uuid.UUID, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicInvoices(BaseModel):
    amount_credited: float = Field(alias="amount_credited")
    approved_at: datetime.datetime | None = Field(alias="approved_at")
    approved_by_id: uuid.UUID | None = Field(alias="approved_by_id")
    billing_address: str = Field(alias="billing_address")
    billing_entity: str = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    contact_email: str = Field(alias="contact_email")
    contact_name: str = Field(alias="contact_name")
    created_at: datetime.datetime = Field(alias="created_at")
    currency: str = Field(alias="currency")
    deleted_at: datetime.datetime | None = Field(alias="deleted_at")
    due_date: datetime.datetime | None = Field(alias="due_date")
    id: uuid.UUID = Field(alias="id")
    invoice_date: datetime.datetime | None = Field(alias="invoice_date")
    invoice_number: str = Field(alias="invoice_number")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    payment_terms: str = Field(alias="payment_terms")
    po_reference: str = Field(alias="po_reference")
    status: str = Field(alias="status")
    subtotal: float = Field(alias="subtotal")
    tax: float = Field(alias="tax")
    tax_rate: float = Field(alias="tax_rate")
    total: float = Field(alias="total")
    updated_at: datetime.datetime = Field(alias="updated_at")
    xero_cogs_journal_id: str | None = Field(alias="xero_cogs_journal_id")
    xero_invoice_id: str | None = Field(alias="xero_invoice_id")
    xero_sync_status: str = Field(alias="xero_sync_status")

class PublicInvoicesInsert(TypedDict):
    amount_credited: NotRequired[Annotated[float, Field(alias="amount_credited")]]
    approved_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="approved_at")]]
    approved_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="approved_by_id")]]
    billing_address: NotRequired[Annotated[str, Field(alias="billing_address")]]
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contact_email: NotRequired[Annotated[str, Field(alias="contact_email")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    currency: NotRequired[Annotated[str, Field(alias="currency")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    due_date: NotRequired[Annotated[datetime.datetime | None, Field(alias="due_date")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    invoice_date: NotRequired[Annotated[datetime.datetime | None, Field(alias="invoice_date")]]
    invoice_number: Annotated[str, Field(alias="invoice_number")]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    payment_terms: NotRequired[Annotated[str, Field(alias="payment_terms")]]
    po_reference: NotRequired[Annotated[str, Field(alias="po_reference")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    subtotal: Annotated[float, Field(alias="subtotal")]
    tax: Annotated[float, Field(alias="tax")]
    tax_rate: NotRequired[Annotated[float, Field(alias="tax_rate")]]
    total: Annotated[float, Field(alias="total")]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    xero_cogs_journal_id: NotRequired[Annotated[str | None, Field(alias="xero_cogs_journal_id")]]
    xero_invoice_id: NotRequired[Annotated[str | None, Field(alias="xero_invoice_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicInvoicesUpdate(TypedDict):
    amount_credited: NotRequired[Annotated[float, Field(alias="amount_credited")]]
    approved_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="approved_at")]]
    approved_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="approved_by_id")]]
    billing_address: NotRequired[Annotated[str, Field(alias="billing_address")]]
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contact_email: NotRequired[Annotated[str, Field(alias="contact_email")]]
    contact_name: NotRequired[Annotated[str, Field(alias="contact_name")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    currency: NotRequired[Annotated[str, Field(alias="currency")]]
    deleted_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="deleted_at")]]
    due_date: NotRequired[Annotated[datetime.datetime | None, Field(alias="due_date")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    invoice_date: NotRequired[Annotated[datetime.datetime | None, Field(alias="invoice_date")]]
    invoice_number: NotRequired[Annotated[str, Field(alias="invoice_number")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    payment_terms: NotRequired[Annotated[str, Field(alias="payment_terms")]]
    po_reference: NotRequired[Annotated[str, Field(alias="po_reference")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    tax_rate: NotRequired[Annotated[float, Field(alias="tax_rate")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    xero_cogs_journal_id: NotRequired[Annotated[str | None, Field(alias="xero_cogs_journal_id")]]
    xero_invoice_id: NotRequired[Annotated[str | None, Field(alias="xero_invoice_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicInvoiceWithdrawals(BaseModel):
    invoice_id: uuid.UUID = Field(alias="invoice_id")
    withdrawal_id: uuid.UUID = Field(alias="withdrawal_id")

class PublicInvoiceWithdrawalsInsert(TypedDict):
    invoice_id: Annotated[uuid.UUID, Field(alias="invoice_id")]
    withdrawal_id: Annotated[uuid.UUID, Field(alias="withdrawal_id")]

class PublicInvoiceWithdrawalsUpdate(TypedDict):
    invoice_id: NotRequired[Annotated[uuid.UUID, Field(alias="invoice_id")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID, Field(alias="withdrawal_id")]]

class PublicInvoiceLineItems(BaseModel):
    amount: float = Field(alias="amount")
    cost: float = Field(alias="cost")
    description: str = Field(alias="description")
    id: uuid.UUID = Field(alias="id")
    invoice_id: uuid.UUID = Field(alias="invoice_id")
    job_id: uuid.UUID | None = Field(alias="job_id")
    quantity: float = Field(alias="quantity")
    sell_cost: float = Field(alias="sell_cost")
    sku_id: uuid.UUID | None = Field(alias="sku_id")
    unit: str = Field(alias="unit")
    unit_price: float = Field(alias="unit_price")

class PublicInvoiceLineItemsInsert(TypedDict):
    amount: Annotated[float, Field(alias="amount")]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    invoice_id: Annotated[uuid.UUID, Field(alias="invoice_id")]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    quantity: Annotated[float, Field(alias="quantity")]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: Annotated[float, Field(alias="unit_price")]

class PublicInvoiceLineItemsUpdate(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    invoice_id: NotRequired[Annotated[uuid.UUID, Field(alias="invoice_id")]]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicInvoiceCounters(BaseModel):
    counter: int = Field(alias="counter")
    key: str = Field(alias="key")
    organization_id: uuid.UUID = Field(alias="organization_id")

class PublicInvoiceCountersInsert(TypedDict):
    counter: NotRequired[Annotated[int, Field(alias="counter")]]
    key: Annotated[str, Field(alias="key")]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]

class PublicInvoiceCountersUpdate(TypedDict):
    counter: NotRequired[Annotated[int, Field(alias="counter")]]
    key: NotRequired[Annotated[str, Field(alias="key")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]

class PublicCreditNotes(BaseModel):
    billing_entity: str = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    created_at: datetime.datetime = Field(alias="created_at")
    credit_note_number: str = Field(alias="credit_note_number")
    id: uuid.UUID = Field(alias="id")
    invoice_id: uuid.UUID | None = Field(alias="invoice_id")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    return_id: uuid.UUID | None = Field(alias="return_id")
    status: str = Field(alias="status")
    subtotal: float = Field(alias="subtotal")
    tax: float = Field(alias="tax")
    total: float = Field(alias="total")
    updated_at: datetime.datetime = Field(alias="updated_at")
    xero_credit_note_id: str | None = Field(alias="xero_credit_note_id")
    xero_sync_status: str = Field(alias="xero_sync_status")

class PublicCreditNotesInsert(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    credit_note_number: Annotated[str, Field(alias="credit_note_number")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    return_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="return_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    xero_credit_note_id: NotRequired[Annotated[str | None, Field(alias="xero_credit_note_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicCreditNotesUpdate(TypedDict):
    billing_entity: NotRequired[Annotated[str, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    credit_note_number: NotRequired[Annotated[str, Field(alias="credit_note_number")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    return_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="return_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    subtotal: NotRequired[Annotated[float, Field(alias="subtotal")]]
    tax: NotRequired[Annotated[float, Field(alias="tax")]]
    total: NotRequired[Annotated[float, Field(alias="total")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    xero_credit_note_id: NotRequired[Annotated[str | None, Field(alias="xero_credit_note_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicCreditNoteLineItems(BaseModel):
    amount: float = Field(alias="amount")
    cost: float = Field(alias="cost")
    credit_note_id: uuid.UUID = Field(alias="credit_note_id")
    description: str = Field(alias="description")
    id: uuid.UUID = Field(alias="id")
    quantity: float = Field(alias="quantity")
    sell_cost: float = Field(alias="sell_cost")
    sku_id: uuid.UUID | None = Field(alias="sku_id")
    unit: str = Field(alias="unit")
    unit_price: float = Field(alias="unit_price")

class PublicCreditNoteLineItemsInsert(TypedDict):
    amount: Annotated[float, Field(alias="amount")]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    credit_note_id: Annotated[uuid.UUID, Field(alias="credit_note_id")]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    quantity: Annotated[float, Field(alias="quantity")]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: Annotated[float, Field(alias="unit_price")]

class PublicCreditNoteLineItemsUpdate(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    credit_note_id: NotRequired[Annotated[uuid.UUID, Field(alias="credit_note_id")]]
    description: NotRequired[Annotated[str, Field(alias="description")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    quantity: NotRequired[Annotated[float, Field(alias="quantity")]]
    sell_cost: NotRequired[Annotated[float, Field(alias="sell_cost")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str, Field(alias="unit")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicPayments(BaseModel):
    amount: float = Field(alias="amount")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    invoice_id: uuid.UUID | None = Field(alias="invoice_id")
    method: str = Field(alias="method")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID = Field(alias="organization_id")
    payment_date: datetime.datetime = Field(alias="payment_date")
    recorded_by_id: uuid.UUID = Field(alias="recorded_by_id")
    reference: str = Field(alias="reference")
    updated_at: datetime.datetime = Field(alias="updated_at")
    xero_payment_id: str | None = Field(alias="xero_payment_id")

class PublicPaymentsInsert(TypedDict):
    amount: Annotated[float, Field(alias="amount")]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    method: NotRequired[Annotated[str, Field(alias="method")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    payment_date: Annotated[datetime.datetime, Field(alias="payment_date")]
    recorded_by_id: Annotated[uuid.UUID, Field(alias="recorded_by_id")]
    reference: NotRequired[Annotated[str, Field(alias="reference")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    xero_payment_id: NotRequired[Annotated[str | None, Field(alias="xero_payment_id")]]

class PublicPaymentsUpdate(TypedDict):
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    invoice_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="invoice_id")]]
    method: NotRequired[Annotated[str, Field(alias="method")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    payment_date: NotRequired[Annotated[datetime.datetime, Field(alias="payment_date")]]
    recorded_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="recorded_by_id")]]
    reference: NotRequired[Annotated[str, Field(alias="reference")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    xero_payment_id: NotRequired[Annotated[str | None, Field(alias="xero_payment_id")]]

class PublicPaymentWithdrawals(BaseModel):
    payment_id: uuid.UUID = Field(alias="payment_id")
    withdrawal_id: uuid.UUID = Field(alias="withdrawal_id")

class PublicPaymentWithdrawalsInsert(TypedDict):
    payment_id: Annotated[uuid.UUID, Field(alias="payment_id")]
    withdrawal_id: Annotated[uuid.UUID, Field(alias="withdrawal_id")]

class PublicPaymentWithdrawalsUpdate(TypedDict):
    payment_id: NotRequired[Annotated[uuid.UUID, Field(alias="payment_id")]]
    withdrawal_id: NotRequired[Annotated[uuid.UUID, Field(alias="withdrawal_id")]]

class PublicFinancialLedger(BaseModel):
    account: str = Field(alias="account")
    amount: float = Field(alias="amount")
    billing_entity: str | None = Field(alias="billing_entity")
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    contractor_id: uuid.UUID | None = Field(alias="contractor_id")
    created_at: datetime.datetime = Field(alias="created_at")
    department: str | None = Field(alias="department")
    id: uuid.UUID = Field(alias="id")
    job_id: uuid.UUID | None = Field(alias="job_id")
    journal_id: uuid.UUID | None = Field(alias="journal_id")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    performed_by_user_id: uuid.UUID | None = Field(alias="performed_by_user_id")
    quantity: float | None = Field(alias="quantity")
    reference_id: str = Field(alias="reference_id")
    reference_type: str = Field(alias="reference_type")
    sku_id: uuid.UUID | None = Field(alias="sku_id")
    unit: str | None = Field(alias="unit")
    unit_cost: float | None = Field(alias="unit_cost")
    vendor_name: str | None = Field(alias="vendor_name")

class PublicFinancialLedgerInsert(TypedDict):
    account: Annotated[str, Field(alias="account")]
    amount: Annotated[float, Field(alias="amount")]
    billing_entity: NotRequired[Annotated[str | None, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="contractor_id")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    department: NotRequired[Annotated[str | None, Field(alias="department")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    journal_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="journal_id")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    performed_by_user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="performed_by_user_id")]]
    quantity: NotRequired[Annotated[float | None, Field(alias="quantity")]]
    reference_id: Annotated[str, Field(alias="reference_id")]
    reference_type: Annotated[str, Field(alias="reference_type")]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str | None, Field(alias="unit")]]
    unit_cost: NotRequired[Annotated[float | None, Field(alias="unit_cost")]]
    vendor_name: NotRequired[Annotated[str | None, Field(alias="vendor_name")]]

class PublicFinancialLedgerUpdate(TypedDict):
    account: NotRequired[Annotated[str, Field(alias="account")]]
    amount: NotRequired[Annotated[float, Field(alias="amount")]]
    billing_entity: NotRequired[Annotated[str | None, Field(alias="billing_entity")]]
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    contractor_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="contractor_id")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    department: NotRequired[Annotated[str | None, Field(alias="department")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    job_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="job_id")]]
    journal_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="journal_id")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    performed_by_user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="performed_by_user_id")]]
    quantity: NotRequired[Annotated[float | None, Field(alias="quantity")]]
    reference_id: NotRequired[Annotated[str, Field(alias="reference_id")]]
    reference_type: NotRequired[Annotated[str, Field(alias="reference_type")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    unit: NotRequired[Annotated[str | None, Field(alias="unit")]]
    unit_cost: NotRequired[Annotated[float | None, Field(alias="unit_cost")]]
    vendor_name: NotRequired[Annotated[str | None, Field(alias="vendor_name")]]

class PublicPurchaseOrders(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    created_by_id: uuid.UUID = Field(alias="created_by_id")
    created_by_name: str = Field(alias="created_by_name")
    document_date: str | None = Field(alias="document_date")
    document_id: uuid.UUID | None = Field(alias="document_id")
    id: uuid.UUID = Field(alias="id")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    received_at: datetime.datetime | None = Field(alias="received_at")
    received_by_id: uuid.UUID | None = Field(alias="received_by_id")
    received_by_name: str | None = Field(alias="received_by_name")
    status: str = Field(alias="status")
    total: float | None = Field(alias="total")
    updated_at: datetime.datetime | None = Field(alias="updated_at")
    vendor_id: uuid.UUID | None = Field(alias="vendor_id")
    vendor_name: str = Field(alias="vendor_name")
    xero_bill_id: str | None = Field(alias="xero_bill_id")
    xero_sync_status: str = Field(alias="xero_sync_status")

class PublicPurchaseOrdersInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    created_by_id: Annotated[uuid.UUID, Field(alias="created_by_id")]
    created_by_name: NotRequired[Annotated[str, Field(alias="created_by_name")]]
    document_date: NotRequired[Annotated[str | None, Field(alias="document_date")]]
    document_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="document_id")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    received_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="received_at")]]
    received_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="received_by_id")]]
    received_by_name: NotRequired[Annotated[str | None, Field(alias="received_by_name")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    total: NotRequired[Annotated[float | None, Field(alias="total")]]
    updated_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="updated_at")]]
    vendor_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="vendor_id")]]
    vendor_name: NotRequired[Annotated[str, Field(alias="vendor_name")]]
    xero_bill_id: NotRequired[Annotated[str | None, Field(alias="xero_bill_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicPurchaseOrdersUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    created_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="created_by_id")]]
    created_by_name: NotRequired[Annotated[str, Field(alias="created_by_name")]]
    document_date: NotRequired[Annotated[str | None, Field(alias="document_date")]]
    document_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="document_id")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    received_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="received_at")]]
    received_by_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="received_by_id")]]
    received_by_name: NotRequired[Annotated[str | None, Field(alias="received_by_name")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    total: NotRequired[Annotated[float | None, Field(alias="total")]]
    updated_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="updated_at")]]
    vendor_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="vendor_id")]]
    vendor_name: NotRequired[Annotated[str, Field(alias="vendor_name")]]
    xero_bill_id: NotRequired[Annotated[str | None, Field(alias="xero_bill_id")]]
    xero_sync_status: NotRequired[Annotated[str, Field(alias="xero_sync_status")]]

class PublicPurchaseOrderItems(BaseModel):
    base_unit: str = Field(alias="base_unit")
    cost: float = Field(alias="cost")
    delivered_qty: float | None = Field(alias="delivered_qty")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    ordered_qty: float = Field(alias="ordered_qty")
    organization_id: uuid.UUID | None = Field(alias="organization_id")
    original_sku: str | None = Field(alias="original_sku")
    pack_qty: int = Field(alias="pack_qty")
    po_id: uuid.UUID = Field(alias="po_id")
    purchase_pack_qty: int = Field(alias="purchase_pack_qty")
    purchase_uom: str = Field(alias="purchase_uom")
    sell_uom: str = Field(alias="sell_uom")
    sku_id: uuid.UUID | None = Field(alias="sku_id")
    status: str = Field(alias="status")
    suggested_department: str = Field(alias="suggested_department")
    unit_price: float = Field(alias="unit_price")

class PublicPurchaseOrderItemsInsert(TypedDict):
    base_unit: NotRequired[Annotated[str, Field(alias="base_unit")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    delivered_qty: NotRequired[Annotated[float | None, Field(alias="delivered_qty")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: Annotated[str, Field(alias="name")]
    ordered_qty: NotRequired[Annotated[float, Field(alias="ordered_qty")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    original_sku: NotRequired[Annotated[str | None, Field(alias="original_sku")]]
    pack_qty: NotRequired[Annotated[int, Field(alias="pack_qty")]]
    po_id: Annotated[uuid.UUID, Field(alias="po_id")]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    suggested_department: NotRequired[Annotated[str, Field(alias="suggested_department")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicPurchaseOrderItemsUpdate(TypedDict):
    base_unit: NotRequired[Annotated[str, Field(alias="base_unit")]]
    cost: NotRequired[Annotated[float, Field(alias="cost")]]
    delivered_qty: NotRequired[Annotated[float | None, Field(alias="delivered_qty")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    ordered_qty: NotRequired[Annotated[float, Field(alias="ordered_qty")]]
    organization_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="organization_id")]]
    original_sku: NotRequired[Annotated[str | None, Field(alias="original_sku")]]
    pack_qty: NotRequired[Annotated[int, Field(alias="pack_qty")]]
    po_id: NotRequired[Annotated[uuid.UUID, Field(alias="po_id")]]
    purchase_pack_qty: NotRequired[Annotated[int, Field(alias="purchase_pack_qty")]]
    purchase_uom: NotRequired[Annotated[str, Field(alias="purchase_uom")]]
    sell_uom: NotRequired[Annotated[str, Field(alias="sell_uom")]]
    sku_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="sku_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    suggested_department: NotRequired[Annotated[str, Field(alias="suggested_department")]]
    unit_price: NotRequired[Annotated[float, Field(alias="unit_price")]]

class PublicDocuments(BaseModel):
    created_at: datetime.datetime = Field(alias="created_at")
    document_type: str = Field(alias="document_type")
    file_hash: str = Field(alias="file_hash")
    file_size: int = Field(alias="file_size")
    filename: str = Field(alias="filename")
    id: uuid.UUID = Field(alias="id")
    mime_type: str = Field(alias="mime_type")
    organization_id: uuid.UUID = Field(alias="organization_id")
    parsed_data: str | None = Field(alias="parsed_data")
    po_id: uuid.UUID | None = Field(alias="po_id")
    status: str = Field(alias="status")
    updated_at: datetime.datetime = Field(alias="updated_at")
    uploaded_by_id: uuid.UUID = Field(alias="uploaded_by_id")
    vendor_name: str | None = Field(alias="vendor_name")

class PublicDocumentsInsert(TypedDict):
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    document_type: NotRequired[Annotated[str, Field(alias="document_type")]]
    file_hash: NotRequired[Annotated[str, Field(alias="file_hash")]]
    file_size: NotRequired[Annotated[int, Field(alias="file_size")]]
    filename: Annotated[str, Field(alias="filename")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    mime_type: NotRequired[Annotated[str, Field(alias="mime_type")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    parsed_data: NotRequired[Annotated[str | None, Field(alias="parsed_data")]]
    po_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="po_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]
    uploaded_by_id: Annotated[uuid.UUID, Field(alias="uploaded_by_id")]
    vendor_name: NotRequired[Annotated[str | None, Field(alias="vendor_name")]]

class PublicDocumentsUpdate(TypedDict):
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    document_type: NotRequired[Annotated[str, Field(alias="document_type")]]
    file_hash: NotRequired[Annotated[str, Field(alias="file_hash")]]
    file_size: NotRequired[Annotated[int, Field(alias="file_size")]]
    filename: NotRequired[Annotated[str, Field(alias="filename")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    mime_type: NotRequired[Annotated[str, Field(alias="mime_type")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    parsed_data: NotRequired[Annotated[str | None, Field(alias="parsed_data")]]
    po_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="po_id")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]
    uploaded_by_id: NotRequired[Annotated[uuid.UUID, Field(alias="uploaded_by_id")]]
    vendor_name: NotRequired[Annotated[str | None, Field(alias="vendor_name")]]

class PublicJobs(BaseModel):
    billing_entity_id: uuid.UUID | None = Field(alias="billing_entity_id")
    code: str = Field(alias="code")
    created_at: datetime.datetime = Field(alias="created_at")
    id: uuid.UUID = Field(alias="id")
    name: str = Field(alias="name")
    notes: str | None = Field(alias="notes")
    organization_id: uuid.UUID = Field(alias="organization_id")
    service_address: str = Field(alias="service_address")
    status: str = Field(alias="status")
    updated_at: datetime.datetime = Field(alias="updated_at")

class PublicJobsInsert(TypedDict):
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    code: Annotated[str, Field(alias="code")]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: Annotated[uuid.UUID, Field(alias="organization_id")]
    service_address: NotRequired[Annotated[str, Field(alias="service_address")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]

class PublicJobsUpdate(TypedDict):
    billing_entity_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="billing_entity_id")]]
    code: NotRequired[Annotated[str, Field(alias="code")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    name: NotRequired[Annotated[str, Field(alias="name")]]
    notes: NotRequired[Annotated[str | None, Field(alias="notes")]]
    organization_id: NotRequired[Annotated[uuid.UUID, Field(alias="organization_id")]]
    service_address: NotRequired[Annotated[str, Field(alias="service_address")]]
    status: NotRequired[Annotated[str, Field(alias="status")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]

class PublicMemoryArtifacts(BaseModel):
    content: str = Field(alias="content")
    created_at: datetime.datetime = Field(alias="created_at")
    expires_at: datetime.datetime | None = Field(alias="expires_at")
    id: uuid.UUID = Field(alias="id")
    org_id: uuid.UUID = Field(alias="org_id")
    session_id: uuid.UUID = Field(alias="session_id")
    subject: str = Field(alias="subject")
    tags: str = Field(alias="tags")
    type: str = Field(alias="type")
    user_id: uuid.UUID = Field(alias="user_id")

class PublicMemoryArtifactsInsert(TypedDict):
    content: NotRequired[Annotated[str, Field(alias="content")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    expires_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="expires_at")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    org_id: Annotated[uuid.UUID, Field(alias="org_id")]
    session_id: Annotated[uuid.UUID, Field(alias="session_id")]
    subject: NotRequired[Annotated[str, Field(alias="subject")]]
    tags: NotRequired[Annotated[str, Field(alias="tags")]]
    type: NotRequired[Annotated[str, Field(alias="type")]]
    user_id: Annotated[uuid.UUID, Field(alias="user_id")]

class PublicMemoryArtifactsUpdate(TypedDict):
    content: NotRequired[Annotated[str, Field(alias="content")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    expires_at: NotRequired[Annotated[datetime.datetime | None, Field(alias="expires_at")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    org_id: NotRequired[Annotated[uuid.UUID, Field(alias="org_id")]]
    session_id: NotRequired[Annotated[uuid.UUID, Field(alias="session_id")]]
    subject: NotRequired[Annotated[str, Field(alias="subject")]]
    tags: NotRequired[Annotated[str, Field(alias="tags")]]
    type: NotRequired[Annotated[str, Field(alias="type")]]
    user_id: NotRequired[Annotated[uuid.UUID, Field(alias="user_id")]]

class PublicAgentRuns(BaseModel):
    agent_name: str = Field(alias="agent_name")
    attempts: int = Field(alias="attempts")
    cost_usd: float = Field(alias="cost_usd")
    created_at: datetime.datetime = Field(alias="created_at")
    duration_ms: int = Field(alias="duration_ms")
    error: str | None = Field(alias="error")
    error_kind: str | None = Field(alias="error_kind")
    handoff_from: str | None = Field(alias="handoff_from")
    id: uuid.UUID = Field(alias="id")
    input_tokens: int = Field(alias="input_tokens")
    mode: str | None = Field(alias="mode")
    model: str = Field(alias="model")
    org_id: uuid.UUID = Field(alias="org_id")
    output_tokens: int = Field(alias="output_tokens")
    parent_run_id: uuid.UUID | None = Field(alias="parent_run_id")
    response_text: str | None = Field(alias="response_text")
    session_id: uuid.UUID = Field(alias="session_id")
    tool_calls: str = Field(alias="tool_calls")
    user_id: uuid.UUID | None = Field(alias="user_id")
    user_message: str | None = Field(alias="user_message")
    validation_failures: str = Field(alias="validation_failures")
    validation_passed: bool | None = Field(alias="validation_passed")
    validation_scores: str = Field(alias="validation_scores")

class PublicAgentRunsInsert(TypedDict):
    agent_name: Annotated[str, Field(alias="agent_name")]
    attempts: NotRequired[Annotated[int, Field(alias="attempts")]]
    cost_usd: NotRequired[Annotated[float, Field(alias="cost_usd")]]
    created_at: Annotated[datetime.datetime, Field(alias="created_at")]
    duration_ms: NotRequired[Annotated[int, Field(alias="duration_ms")]]
    error: NotRequired[Annotated[str | None, Field(alias="error")]]
    error_kind: NotRequired[Annotated[str | None, Field(alias="error_kind")]]
    handoff_from: NotRequired[Annotated[str | None, Field(alias="handoff_from")]]
    id: Annotated[uuid.UUID, Field(alias="id")]
    input_tokens: NotRequired[Annotated[int, Field(alias="input_tokens")]]
    mode: NotRequired[Annotated[str | None, Field(alias="mode")]]
    model: Annotated[str, Field(alias="model")]
    org_id: Annotated[uuid.UUID, Field(alias="org_id")]
    output_tokens: NotRequired[Annotated[int, Field(alias="output_tokens")]]
    parent_run_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="parent_run_id")]]
    response_text: NotRequired[Annotated[str | None, Field(alias="response_text")]]
    session_id: Annotated[uuid.UUID, Field(alias="session_id")]
    tool_calls: NotRequired[Annotated[str, Field(alias="tool_calls")]]
    user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="user_id")]]
    user_message: NotRequired[Annotated[str | None, Field(alias="user_message")]]
    validation_failures: NotRequired[Annotated[str, Field(alias="validation_failures")]]
    validation_passed: NotRequired[Annotated[bool | None, Field(alias="validation_passed")]]
    validation_scores: NotRequired[Annotated[str, Field(alias="validation_scores")]]

class PublicAgentRunsUpdate(TypedDict):
    agent_name: NotRequired[Annotated[str, Field(alias="agent_name")]]
    attempts: NotRequired[Annotated[int, Field(alias="attempts")]]
    cost_usd: NotRequired[Annotated[float, Field(alias="cost_usd")]]
    created_at: NotRequired[Annotated[datetime.datetime, Field(alias="created_at")]]
    duration_ms: NotRequired[Annotated[int, Field(alias="duration_ms")]]
    error: NotRequired[Annotated[str | None, Field(alias="error")]]
    error_kind: NotRequired[Annotated[str | None, Field(alias="error_kind")]]
    handoff_from: NotRequired[Annotated[str | None, Field(alias="handoff_from")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    input_tokens: NotRequired[Annotated[int, Field(alias="input_tokens")]]
    mode: NotRequired[Annotated[str | None, Field(alias="mode")]]
    model: NotRequired[Annotated[str, Field(alias="model")]]
    org_id: NotRequired[Annotated[uuid.UUID, Field(alias="org_id")]]
    output_tokens: NotRequired[Annotated[int, Field(alias="output_tokens")]]
    parent_run_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="parent_run_id")]]
    response_text: NotRequired[Annotated[str | None, Field(alias="response_text")]]
    session_id: NotRequired[Annotated[uuid.UUID, Field(alias="session_id")]]
    tool_calls: NotRequired[Annotated[str, Field(alias="tool_calls")]]
    user_id: NotRequired[Annotated[uuid.UUID | None, Field(alias="user_id")]]
    user_message: NotRequired[Annotated[str | None, Field(alias="user_message")]]
    validation_failures: NotRequired[Annotated[str, Field(alias="validation_failures")]]
    validation_passed: NotRequired[Annotated[bool | None, Field(alias="validation_passed")]]
    validation_scores: NotRequired[Annotated[str, Field(alias="validation_scores")]]

class PublicEmbeddings(BaseModel):
    content: str = Field(alias="content")
    content_hash: str = Field(alias="content_hash")
    embedding: list[Any] = Field(alias="embedding")
    entity_id: uuid.UUID = Field(alias="entity_id")
    entity_type: str = Field(alias="entity_type")
    id: uuid.UUID = Field(alias="id")
    org_id: uuid.UUID = Field(alias="org_id")
    updated_at: datetime.datetime = Field(alias="updated_at")

class PublicEmbeddingsInsert(TypedDict):
    content: Annotated[str, Field(alias="content")]
    content_hash: Annotated[str, Field(alias="content_hash")]
    embedding: Annotated[list[Any], Field(alias="embedding")]
    entity_id: Annotated[uuid.UUID, Field(alias="entity_id")]
    entity_type: Annotated[str, Field(alias="entity_type")]
    id: Annotated[uuid.UUID, Field(alias="id")]
    org_id: Annotated[uuid.UUID, Field(alias="org_id")]
    updated_at: Annotated[datetime.datetime, Field(alias="updated_at")]

class PublicEmbeddingsUpdate(TypedDict):
    content: NotRequired[Annotated[str, Field(alias="content")]]
    content_hash: NotRequired[Annotated[str, Field(alias="content_hash")]]
    embedding: NotRequired[Annotated[list[Any], Field(alias="embedding")]]
    entity_id: NotRequired[Annotated[uuid.UUID, Field(alias="entity_id")]]
    entity_type: NotRequired[Annotated[str, Field(alias="entity_type")]]
    id: NotRequired[Annotated[uuid.UUID, Field(alias="id")]]
    org_id: NotRequired[Annotated[uuid.UUID, Field(alias="org_id")]]
    updated_at: NotRequired[Annotated[datetime.datetime, Field(alias="updated_at")]]

class PublicEntityEdges(BaseModel):
    org_id: uuid.UUID | None = Field(alias="org_id")
    relation: str | None = Field(alias="relation")
    source_id: uuid.UUID | None = Field(alias="source_id")
    source_type: str | None = Field(alias="source_type")
    target_id: uuid.UUID | None = Field(alias="target_id")
    target_type: str | None = Field(alias="target_type")
