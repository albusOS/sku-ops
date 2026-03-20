"""Provision the Supply Yard org, departments, and (optionally) a dev user.

Idempotent — safe to run multiple times. Uses ON CONFLICT DO NOTHING.

Usage:
    # Local dev: org + departments + dev user
    PYTHONPATH=backend:. uv run python -m devtools.scripts.provision --dev

    # Production: org + departments only
    DATABASE_URL=<prod-url> PYTHONPATH=backend:. uv run python -m devtools.scripts.provision
"""

import argparse
import asyncio
import logging
import uuid
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


async def main(create_dev_user: bool = False) -> None:
    from devtools.scripts.company import DEPARTMENTS, DEV_CONTRACTOR, DEV_USER, ORG
    from shared.infrastructure.db import close_db, get_connection, init_db

    await init_db()

    try:
        conn = get_connection()
        now = datetime.now(UTC).isoformat()

        # ── Org ───────────────────────────────────────────────────────────
        await conn.execute(
            "INSERT INTO organizations (id, name, slug, created_at) "
            "VALUES ($1, $2, $3, $4) ON CONFLICT (id) DO NOTHING",
            (ORG.id, ORG.name, ORG.slug, now),
        )
        await conn.commit()
        print(f"Org: {ORG.name} ({ORG.id})")

        # ── Departments ───────────────────────────────────────────────────
        created = 0
        for dept in DEPARTMENTS:
            try:
                await conn.execute(
                    "INSERT INTO departments (id, name, code, description, sku_count, organization_id, created_at) "
                    "VALUES ($1, $2, $3, $4, 0, $5, $6) "
                    "ON CONFLICT (organization_id, code) DO NOTHING",
                    (str(uuid.uuid4()), dept.name, dept.code, dept.description, ORG.id, now),
                )
                await conn.commit()
                created += 1
            except Exception as e:
                logger.debug("Department %s already exists: %s", dept.code, e)
        print(f"Departments: {created} created, {len(DEPARTMENTS) - created} already existed")

        # ── Dev user ──────────────────────────────────────────────────────
        if create_dev_user:
            import bcrypt

            hashed = bcrypt.hashpw(DEV_USER.password.encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
            )

            await conn.execute(
                "INSERT INTO users (id, email, password, name, role, company, billing_entity, "
                "phone, is_active, organization_id, created_at) "
                "VALUES ($1, $2, $3, $4, $5, '', '', '', TRUE, $6, $7) "
                "ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, "
                "name = EXCLUDED.name, role = EXCLUDED.role",
                (
                    str(uuid.uuid4()),
                    DEV_USER.email,
                    hashed,
                    DEV_USER.name,
                    DEV_USER.role,
                    ORG.id,
                    now,
                ),
            )
            await conn.commit()
            print(f"Dev admin: {DEV_USER.email} / {DEV_USER.password}")

            # Dev contractor
            hashed_c = bcrypt.hashpw(
                DEV_CONTRACTOR.password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")
            await conn.execute(
                "INSERT INTO users (id, email, password, name, role, company, billing_entity, "
                "phone, is_active, organization_id, created_at) "
                "VALUES ($1, $2, $3, $4, $5, 'Dev Contractor Co', 'Dev Contractor Co', '', TRUE, $6, $7) "
                "ON CONFLICT (email) DO UPDATE SET password = EXCLUDED.password, "
                "name = EXCLUDED.name, role = EXCLUDED.role",
                (
                    str(uuid.uuid4()),
                    DEV_CONTRACTOR.email,
                    hashed_c,
                    DEV_CONTRACTOR.name,
                    DEV_CONTRACTOR.role,
                    ORG.id,
                    now,
                ),
            )
            await conn.commit()
            print(f"Dev contractor: {DEV_CONTRACTOR.email} / {DEV_CONTRACTOR.password}")

        print("Done.")
    finally:
        await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision Supply Yard org + departments")
    parser.add_argument("--dev", action="store_true", help="Also create dev user for local auth")
    args = parser.parse_args()
    asyncio.run(main(create_dev_user=args.dev))
