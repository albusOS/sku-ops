"""Org settings API - Xero account codes and connection status."""

import logging

from fastapi import APIRouter, HTTPException

from finance.application.org_settings_service import get_org_settings, upsert_org_settings
from finance.domain.org_settings import OrgSettings, OrgSettingsUpdate
from shared.api.deps import AdminDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


_REDACTED = "***"


def _mask(settings: OrgSettings) -> dict:
    """Return settings dict with secrets masked."""
    d = settings.model_dump()
    for key in ("xero_access_token", "xero_refresh_token"):
        if d.get(key):
            d[key] = _REDACTED
    d["xero_connected"] = bool(settings.xero_tenant_id and settings.xero_access_token)
    return d


@router.get("/xero")
async def get_xero_settings(current_user: AdminDep):
    """Return Xero config for the org. Secrets are masked in the response."""
    try:
        settings = await get_org_settings()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in get_xero_settings")
        raise
    if settings is None:
        raise HTTPException(status_code=404, detail="Organization settings not found")
    return _mask(settings)


@router.put("/xero")
async def update_xero_settings(
    data: OrgSettingsUpdate,
    current_user: AdminDep,
):
    """Update Xero account codes and/or API credentials."""
    try:
        settings = await get_org_settings()
        if settings is None:
            raise HTTPException(status_code=404, detail="Organization settings not found")

        update = data.model_dump(exclude_none=True)
        merged = settings.model_copy(update=update)
        saved = await upsert_org_settings(merged)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error in update_xero_settings")
        raise
    return _mask(saved)
