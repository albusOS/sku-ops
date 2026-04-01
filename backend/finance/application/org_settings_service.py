"""Org settings and Xero OAuth state — application-layer facade.

Safe for cross-context import. Other contexts call these functions
instead of reaching into finance infrastructure directly.
"""

from __future__ import annotations

from finance.domain.xero_settings import XeroSettings
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


def _finance():
    return get_database_manager().finance


async def get_org_settings():
    return await _finance().org_settings_get(get_org_id())


async def get_xero_settings() -> XeroSettings:
    """Return org settings projected to the XeroSettings shape.

    All Xero integration callers need this projection. Centralising it here
    means callers never touch OrgSettings directly and never perform the
    model_validate(model_dump()) cast themselves.
    """
    settings = await get_org_settings()
    return XeroSettings.model_validate(settings.model_dump())


async def upsert_org_settings(settings):
    return await _finance().org_settings_upsert(get_org_id(), settings)


async def clear_xero_tokens() -> None:
    await _finance().org_settings_clear_xero_tokens(get_org_id())


async def save_oauth_state(state: str) -> None:
    await _finance().oauth_save_state(get_org_id(), state)


async def pop_oauth_state(state: str) -> str | None:
    return await _finance().oauth_pop_state(get_org_id(), state)
