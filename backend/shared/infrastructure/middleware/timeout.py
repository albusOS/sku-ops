"""Request timeout middleware — prevents slow requests from exhausting workers.

Applies a configurable timeout to all non-WebSocket, non-streaming requests.
WebSocket connections and SSE streams are excluded since they are long-lived
by design and have their own heartbeat/cancellation logic.

Timeout values (seconds):
  - General API:  REQUEST_TIMEOUT  (default 30)
  - AI endpoints: AI_REQUEST_TIMEOUT (default 120)

AI endpoints are identified by path prefix (/api/chat).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

if TYPE_CHECKING:
    from starlette.requests import Request

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))
AI_REQUEST_TIMEOUT = int(os.environ.get("AI_REQUEST_TIMEOUT", "120"))

# Paths that get the longer AI timeout
_AI_PREFIXES = ("/api/chat", "/api/beta/assistant/chat")

# Paths excluded from timeout enforcement (long-lived connections)
_EXCLUDED_PREFIXES = ("/api/ws", "/metrics")


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip WebSocket upgrades and excluded paths
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        if any(path.startswith(p) for p in _EXCLUDED_PREFIXES):
            return await call_next(request)

        # Pick timeout based on path
        timeout = (
            AI_REQUEST_TIMEOUT if any(path.startswith(p) for p in _AI_PREFIXES) else REQUEST_TIMEOUT
        )

        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except TimeoutError:
            logger.warning(
                "Request timed out after %ds: %s %s",
                timeout,
                request.method,
                path,
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out. Please try again."},
            )
