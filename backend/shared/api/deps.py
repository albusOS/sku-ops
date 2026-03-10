"""Shared Annotated dependency aliases for FastAPI route handlers.

Import these instead of writing ``Depends(get_current_user)`` inline.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from identity.application.auth_service import get_current_user, require_role
from kernel.types import CurrentUser

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
AdminDep = Annotated[CurrentUser, Depends(require_role("admin"))]
