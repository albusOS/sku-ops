"""Helpers for UUID and ORM row mapping at the DB boundary."""

from __future__ import annotations

import uuid
from datetime import datetime


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


def parse_date_param(value: str | None) -> datetime | None:
    """Parse ISO-8601 query params (e.g. ``2026-03-27T04:00:00.000Z``) for ORM ``timestamptz`` compares.

    Raw strings bound as VARCHAR break Postgres: ``timestamptz >= varchar``."""
    if not value or not value.strip():
        return None
    return datetime.fromisoformat(value.strip())
