# Dev data

- **`seed_demo.sql`** - Full DELETE+INSERT bundle produced by `python -m devtools.scripts.seed_demo --target supabase`. Canonical split for local Supabase lives in **`../../supabase/seeds/`** (applied on `db reset`).
- **`archive/legacy_seed_fragments/`** - Old hand-split chunks for SQL clients; superseded by `supabase/seeds/`.
