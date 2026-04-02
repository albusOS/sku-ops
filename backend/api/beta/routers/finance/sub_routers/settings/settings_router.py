"""Org settings API - Xero account codes and connection status."""

import logging

from fastapi import APIRouter, HTTPException

from finance.domain.org_settings import OrgSettings, OrgSettingsUpdate
from shared.api.deps import AdminDep
from shared.infrastructure.db import get_org_id
from shared.infrastructure.db.base import get_database_manager

logger = logging.getLogger(__name__)


def _db_finance():
    return get_database_manager().finance


router = APIRouter(prefix="/settings", tags=["settings"])


_REDACTED = "***"


def _mask(settings: OrgSettings) -> dict:
    """Return settings dict with secrets masked."""
    d = settings.model_dump()
    for key in ("xero_access_token", "xero_refresh_token"):
        if d.get(key):
            d[key] = _REDACTED
    d["xero_connected"] = bool(
        settings.xero_tenant_id and settings.xero_access_token
    )
    return d


@router.get("/xero")
async def get_xero_settings(current_user: AdminDep):
    """Return Xero config for the org. Secrets are masked in the response."""
    try:
        settings = await _db_finance().org_settings_get(get_org_id())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in get_xero_settings")
        raise
    if settings is None:
        raise HTTPException(
            status_code=404, detail="Organization settings not found"
        )
    return _mask(settings)


@router.put("/xero")
async def update_xero_settings(
    data: OrgSettingsUpdate,
    current_user: AdminDep,
):
    """Update Xero account codes and/or API credentials."""
    try:
        settings = await _db_finance().org_settings_get(get_org_id())
        if settings is None:
            raise HTTPException(
                status_code=404, detail="Organization settings not found"
            )

        update = data.model_dump(exclude_none=True)
        merged = settings.model_copy(update=update)
        saved = await _db_finance().org_settings_upsert(get_org_id(), merged)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in update_xero_settings")
        raise
    return _mask(saved)
