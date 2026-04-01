"""OAuth state persistence for Xero connect flow.

Owned by finance — the OAuth flow is for the Xero integration,
not a general auth concern.
"""

from datetime import UTC, datetime

from shared.infrastructure.db import get_org_id, sql_execute


async def save_oauth_state(state: str) -> None:
    org_id = get_org_id()
    now = datetime.now(UTC)
    await sql_execute(
        """INSERT INTO oauth_states (state, org_id, created_at) VALUES ($1, $2, $3)
           ON CONFLICT(state) DO UPDATE SET org_id = $4, created_at = $5""",
        (state, org_id, now, org_id, now),
        read_only=False,
    )


async def pop_oauth_state(state: str) -> str | None:
    res = await sql_execute(
        "SELECT org_id FROM oauth_states WHERE state = $1",
        (state,),
        read_only=True,
        max_rows=2,
    )
    row = res.rows[0] if res.rows else None
    if not row:
        return None
    await sql_execute(
        "DELETE FROM oauth_states WHERE state = $1", (state,), read_only=False
    )
    return row["org_id"]
