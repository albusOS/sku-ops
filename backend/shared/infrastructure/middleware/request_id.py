"""Request ID middleware — generates or propagates X-Request-ID per request.

Sets contextvars consumed by the structured logger so every log line in the
request lifecycle carries the same correlation ID.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from shared.infrastructure.logging_config import org_id_var, request_id_var, user_id_var

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = request.headers.get(_HEADER) or uuid.uuid4().hex
        request_id_var.set(rid)

        # Reset per-request context (will be filled by auth dependency later)
        user_id_var.set("")
        org_id_var.set("")

        response = await call_next(request)
        response.headers[_HEADER] = rid
        return response
