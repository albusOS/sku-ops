# Supabase Context Migration Matrix

## Context status

| Context | Primary persistence path now | SQLModel status | Keep raw SQL? | Notes |
|---|---|---|---|---|
| `shared` | Central DB layer via `get_connection()` and `get_session()` | Ready for progressive adoption | Yes | Profile, audit, org, and auth-adjacent rows remain backend-owned. |
| `catalog` | Raw SQL repos through centralized DB layer | Not yet modeled | Partial | CRUD can move first; barcode and vendor lookups can stay explicit SQL. |
| `inventory` | Raw SQL repos through centralized DB layer | Not yet modeled | Partial | Ledger-style stock writes and analytics can stay SQL-first. |
| `operations` | Raw SQL repos through centralized DB layer | Not yet modeled | Yes | Withdrawal and return flows are transaction-heavy and should migrate carefully. |
| `finance` | Raw SQL repos through centralized DB layer | Not yet modeled | Yes | Ledger analytics, joins, and Xero sync queries should remain SQL for now. |
| `purchasing` | Raw SQL repos through centralized DB layer | Not yet modeled | Partial | PO CRUD can move first; receiving and analytics can stay SQL. |
| `documents` | Raw SQL repo through centralized DB layer | Not yet modeled | Partial | Small enough for early SQLModel migration if desired. |
| `jobs` | Raw SQL repo through centralized DB layer | Not yet modeled | Partial | Good low-risk candidate for early SQLModel conversion. |
| `assistant` | DB metadata now sourced from Supabase migration artifact | Not yet modeled | Yes | Embeddings, analyst SQL, and graph traversal remain explicit SQL. |

## Recommended order

1. `shared` profile and org helpers
2. `jobs`
3. `documents`
4. `catalog`
5. `inventory`
6. `purchasing`
7. `operations`
8. `finance`
9. `assistant`

## Rules for what stays raw SQL

- Keep raw SQL for recursive CTEs, analytics rollups, `FOR UPDATE`, pgvector search, and wide reporting queries.
- Move straightforward CRUD and typed row-mapping flows to SQLModel over time.
- Route every context through the centralized DB layer even when the query itself remains handwritten SQL.
- Do not reintroduce per-context connection setup or app-owned schema bootstrap.
