"""UUID helpers for internal surrogate identifiers."""

from __future__ import annotations

from uuid import UUID

from uuid6 import uuid7


def parse_uuid_str(field_name: str, raw: str) -> str:
    """Parse and canonicalize a UUID string for DB binds (asyncpg validates str strictly).

    Rejects whitespace, non-UUID text, and malformed values before they reach SQL,
    so callers can turn this into 401 instead of an unhandled DBAPIError (500).
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"invalid {field_name}: empty")
    try:
        return str(UUID(raw.strip()))
    except ValueError as e:
        raise ValueError(f"invalid {field_name}: {e}") from e


def new_uuid7() -> UUID:
    """Return a new RFC 9562 UUIDv7 value."""

    return uuid7()


def new_uuid7_str() -> str:
    """Return a new UUIDv7 rendered as canonical text."""

    return str(new_uuid7())
