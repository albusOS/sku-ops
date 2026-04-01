"""Helpers for UUID and ORM row mapping at the DB boundary."""

from __future__ import annotations

import uuid


def as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def as_uuid_required(value: str | uuid.UUID) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def uuid_str(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)
