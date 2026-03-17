"""User repository — pure persistence for the users table.

Owns all direct SQL access to the users table. Auth routes and any other
consumer that needs user lookups must go through this module.
"""

import time

from shared.infrastructure.database import get_connection

# ── Lightweight deactivation cache ───────────────────────────────────────────
# Avoids a DB roundtrip on every authenticated request. Entries expire after
# _ACTIVE_CACHE_TTL seconds, so a deactivated user loses access within ~60s
# instead of waiting for their JWT to expire (up to 15 min).

_ACTIVE_CACHE_TTL = 60  # seconds
_ACTIVE_CACHE_MAX = 1000  # evict oldest entries when cache exceeds this size
_active_cache: dict[str, tuple[bool, float]] = {}


async def is_user_active(user_id: str) -> bool:
    """Check whether a user account is active (cached, TTL-based)."""
    now = time.monotonic()
    cached = _active_cache.get(user_id)
    if cached and (now - cached[1]) < _ACTIVE_CACHE_TTL:
        return cached[0]

    try:
        conn = get_connection()
        cursor = await conn.execute(
            "SELECT is_active FROM users WHERE id = $1",
            (user_id,),
        )
        row = await cursor.fetchone()
        active = bool(row[0]) if row else True  # unknown user → allow (JWT will fail elsewhere)
    except (RuntimeError, OSError):
        # DB not available — fail open so requests aren't blocked during startup
        return True

    _active_cache[user_id] = (active, now)

    # Evict expired entries if cache grows too large
    if len(_active_cache) > _ACTIVE_CACHE_MAX:
        expired = [k for k, (_, ts) in _active_cache.items() if (now - ts) >= _ACTIVE_CACHE_TTL]
        for k in expired:
            del _active_cache[k]

    return active


_SELECT_COLS = (
    "id, email, password, name, role, company, billing_entity, phone, is_active, organization_id"
)

_SELECT_COLS_SAFE = "id, email, name, role, company, billing_entity, billing_entity_id, phone, is_active, organization_id"


async def fetch_by_email(email: str) -> dict | None:
    """Fetch user row by email. Returns dict with password included (for auth)."""
    conn = get_connection()
    cursor = await conn.execute(
        f"SELECT {_SELECT_COLS} FROM users WHERE email = $1",
        (email,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def fetch_by_id(user_id: str) -> dict | None:
    """Fetch user row by ID. Returns dict without password (safe for profiles)."""
    conn = get_connection()
    cursor = await conn.execute(
        f"SELECT {_SELECT_COLS_SAFE} FROM users WHERE id = $1",
        (user_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def insert_user(
    *,
    user_id: str,
    email: str,
    password_hash: str,
    name: str,
    role: str = "admin",
    organization_id: str,
    created_at: str,
) -> None:
    """Insert a new user row."""
    conn = get_connection()
    await conn.execute(
        "INSERT INTO users (id, email, password, name, role, is_active, organization_id, created_at)"
        " VALUES ($1, $2, $3, $4, $5, 1, $6, $7)",
        (user_id, email, password_hash, name, role, organization_id, created_at),
    )
    await conn.commit()
