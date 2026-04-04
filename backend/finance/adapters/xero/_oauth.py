"""Xero OAuth 2.0 token management mixin."""

from datetime import UTC, datetime

import httpx

from finance.adapters.xero._base import (
    XERO_CONNECTIONS_URL,
    XERO_OAUTH_ENDPOINT,
)
from finance.domain.xero_settings import XeroSettings
from shared.infrastructure.config import XERO_CLIENT_ID, XERO_CLIENT_SECRET
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


class XeroOAuthMixin:
    async def refresh_token(self, settings: XeroSettings) -> XeroSettings:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                XERO_OAUTH_ENDPOINT,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": settings.xero_refresh_token,
                    "client_id": XERO_CLIENT_ID,
                    "client_secret": XERO_CLIENT_SECRET,
                },
                timeout=15,
            )
        resp.raise_for_status()
        token_data = resp.json()

        expiry = datetime.now(UTC).timestamp() + token_data.get("expires_in", 1800)
        updated = settings.model_copy(
            update={
                "xero_access_token": token_data["access_token"],
                "xero_refresh_token": token_data.get("refresh_token", settings.xero_refresh_token),
                "xero_token_expiry": datetime.fromtimestamp(expiry, tz=UTC),
            }
        )
        persisted = await get_database_manager().finance.org_settings_upsert(get_org_id(), updated)
        return XeroSettings.model_validate(persisted.model_dump())

    async def get_tenants(self, access_token: str) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                XERO_CONNECTIONS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=15,
            )
        resp.raise_for_status()
        return resp.json()
