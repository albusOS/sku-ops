"""User repository — persistence for the users table (delegates to SharedDatabaseService)."""

from datetime import datetime

from shared.infrastructure.db.base import get_database_manager


async def is_user_active(user_id: str) -> bool:
    db = get_database_manager()
    return await db.shared.is_user_active(user_id)


async def fetch_by_email(email: str) -> dict | None:
    db = get_database_manager()
    return await db.shared.fetch_user_by_email(email)


async def fetch_by_id(user_id: str) -> dict | None:
    db = get_database_manager()
    return await db.shared.fetch_user_safe_by_id(user_id)


async def insert_user(
    *,
    user_id: str,
    email: str,
    password_hash: str,
    name: str,
    role: str = "admin",
    organization_id: str,
    created_at: datetime,
) -> None:
    db = get_database_manager()
    await db.shared.insert_user(
        user_id=user_id,
        email=email,
        password_hash=password_hash,
        name=name,
        role=role,
        organization_id=organization_id,
        created_at=created_at,
    )
