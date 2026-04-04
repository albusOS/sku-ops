"""Legacy entry point - canonical org/departments/demo data is SQL under ``supabase/seeds/``.

Local workflow:
    pixi run db-reset

That runs migrations and applies ``supabase/config.toml`` ``[db.seed] sql_paths`` (``01_org`` through ``05_demo``).

``04_users.sql`` seeds ``auth.users`` + ``auth.identities`` for every ``public.users`` row (demo + dev); local password for all is ``dev123``.

This module no longer mutates the database; it only prints the above hint.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deprecated - use supabase db reset for seed data"
    )
    parser.add_argument(
        "--dev", action="store_true", help="Ignored (dev users are in SQL seed)"
    )
    _ = parser.parse_args()
    print(
        "Provisioning is handled by Supabase seeds. Run:\n"
        "  pixi run db-reset\n"
        "or: supabase db reset --local\n"
        "See supabase/seeds/README.md"
    )


if __name__ == "__main__":
    main()
