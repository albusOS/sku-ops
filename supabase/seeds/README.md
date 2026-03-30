# Database seeds

Files `01_org.sql` through `05_demo_business_data.sql` run in order on `supabase db reset` (see `config.toml` `[db.seed] sql_paths`).

- **pytest_minimal.sql** is for backend tests only (`backend/tests/conftest.py`); it is not listed in `sql_paths`.

Reload local demo data with `supabase db reset --local` or `./bin/dev db:reset` rather than re-running DELETE-heavy SQL manually.
