"""Shared auth helpers for tests."""

import time

import jwt

from identity.application.auth_service import create_token
from shared.infrastructure.config import JWT_ALGORITHM, JWT_SECRET


def admin_headers() -> dict:
    token = create_token("user-1", "test@test.com", "admin", "default")
    return {"Authorization": f"Bearer {token}"}


def contractor_headers() -> dict:
    token = create_token("contractor-1", "contractor@test.com", "contractor", "default")
    return {"Authorization": f"Bearer {token}"}


def admin_token() -> str:
    return create_token("user-1", "test@test.com", "admin", "default")


def contractor_token() -> str:
    return create_token("contractor-1", "contractor@test.com", "contractor", "default")


def make_token(
    user_id: str = "user-1",
    org_id: str = "default",
    role: str = "admin",
    name: str = "Test User",
    expired: bool = False,
) -> str:
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "organization_id": org_id,
        "role": role,
        "name": name,
        "exp": int(time.time()) + (-3600 if expired else 3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def expired_token() -> str:
    return make_token(expired=True)
