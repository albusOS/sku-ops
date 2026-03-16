"""Rate limiting — handled entirely by nginx upstream.

nginx enforces:
  - General API:      60 req/min  (zone=api,  /api/)
  - Auth endpoints:   10 req/min  (zone=auth, /api/auth/)
  - Chat endpoints:   20 req/min  (zone=chat, /api/beta/assistant/ws/chat, /api/beta/assistant/chat)

This module is kept as a stub so that any import references survive without
error during the transition. Nothing here applies runtime limits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def setup_rate_limiting(app: FastAPI) -> None:
    """No-op — rate limiting is enforced by nginx."""


def auth_limit(func):
    """No-op decorator — auth rate limiting handled by nginx zone=auth."""
    return func


def chat_limit(func):
    """No-op decorator — chat rate limiting handled by nginx zone=chat."""
    return func
