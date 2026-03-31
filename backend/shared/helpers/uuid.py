"""UUID helpers for internal surrogate identifiers."""

from __future__ import annotations

from uuid import UUID

from uuid6 import uuid7


def new_uuid7() -> UUID:
    """Return a new RFC 9562 UUIDv7 value."""

    return uuid7()


def new_uuid7_str() -> str:
    """Return a new UUIDv7 rendered as canonical text."""

    return str(new_uuid7())
