"""Org Xero settings projection — application-layer facade.

Safe for cross-context import. Callers use `get_xero_settings` for the Xero
integration shape; direct org_settings CRUD uses `get_database_manager().finance`
at call sites.
"""

from __future__ import annotations

from finance.domain.xero_settings import XeroSettings
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager


async def get_xero_settings() -> XeroSettings:
    """Return org settings projected to the XeroSettings shape.

    All Xero integration callers need this projection. Centralising it here
    means callers never touch OrgSettings directly and never perform the
    model_validate(model_dump()) cast themselves.
    """
    settings = await get_database_manager().finance.org_settings_get(
        get_org_id()
    )
    return XeroSettings.model_validate(settings.model_dump())
