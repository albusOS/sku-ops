"""Audit logging — records who-did-what for sensitive operations.

Usage in routes:

    from shared.api.deps import CurrentUserDep
    from shared.infrastructure.middleware.audit import audit_log

    @router.post("/some-sensitive-action")
    async def handler(request: Request, current_user: CurrentUserDep):
        # ... perform action ...
        await audit_log(
            user_id=current_user.id,
            action="payment.mark_paid",
            resource_type="withdrawal",
            resource_id=withdrawal_id,
            request=request,
            org_id=current_user.organization_id,
        )

This is intentionally a function, not global middleware, to avoid noisy logs
on read-only endpoints.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from shared.helpers.uuid import new_uuid7_str
from shared.infrastructure.db.base import get_database_manager
from shared.infrastructure.db.orm_utils import as_uuid_required

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)


def _db_shared():
    return get_database_manager().shared


async def audit_log(
    *,
    user_id: str,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | str | None = None,
    request: Request | None = None,
    org_id: str | None = None,
) -> None:
    """Write an audit log entry to the database."""
    ip = ""
    if request:
        ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not ip and request.client:
            ip = request.client.host

    details_str = json.dumps(details) if isinstance(details, dict) else (details or "")
    now = datetime.now(UTC)

    try:
        await _db_shared().insert_audit_row(
            audit_id=as_uuid_required(new_uuid7_str()),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_str,
            ip_address=ip,
            organization_id=org_id,
            created_at=now,
        )
    except Exception:
        logger.exception("Failed to write audit log entry")
