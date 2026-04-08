# Deployment Playbook

Target stack: **DigitalOcean** (or equivalent for the FastAPI backend) + **Vercel** (frontend) + **Supabase** (auth + Postgres). CI/CD wiring is repo-specific — this doc covers env, auth, and verification only.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Vercel     │     │  API host    │     │   Supabase   │
│  (Frontend)  │────▶│  (Backend)   │────▶│  (Auth + DB) │
│  React SPA   │     │  FastAPI     │     │  Postgres 16 │
└──────────────┘     └──────────────┘     └──────────────┘
  Deploys from:        Your pipeline       Managed
  Root dir: /          Docker image
```

- **Frontend** (Vercel) — static React SPA; API calls go to `VITE_BACKEND_URL`.
- **Backend** — FastAPI in Docker; connects to Supabase Postgres via `PRIVATE_DATABASE_URL` (or composed `PUBLIC_DB_*` + `PRIVATE_DB_PASSWORD`).
- **Auth** (Supabase) — issues JWTs. Backend validates with Supabase `PRIVATE_JWT_SECRET`.
- **Database** — Supabase Postgres. Use **port 5432** with either the **direct** host or the **session** pooler (see [DigitalOcean App Platform and Supabase (IPv4)](#digitalocean-app-platform-and-supabase-ipv4)). **Do not** use the **transaction** pooler on **6543** here: asyncpg uses prepared statements that do not match transaction-pooled PgBouncer.

### DigitalOcean App Platform and Supabase (IPv4)

**App Platform egress is IPv4-centric.** Under **Networking limits**, DigitalOcean states they **do not offer dedicated egress IPv6 addresses**, that App Platform apps **do not support connecting to IPv6 services or hosts**, and that IPv6-oriented client config can produce **`ETIMEDOUT`** (bind to IPv4 / `0.0.0.0` in examples; see [App Platform limits](https://docs.digitalocean.com/products/app-platform/details/limits)). Plan Postgres outbound as **IPv4**.

**Supabase direct** hostnames (`db.<project_ref>.supabase.co`) often resolve in ways that are **not reachable from IPv4-only clients**, so a backend on App Platform may see **`No route to host`** or similar even though the password and SSL are correct.

**Two practical fixes:**

1. **Session pooler (session mode, port 5432)** — Supabase documents that session mode connects to Postgres **via a proxy** and is **only recommended as an alternative to a direct connection when connecting via an IPv4 network** (see [Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)). Copy the **Session pooler** string from the project dashboard (**Connect**). It looks like:
   `postgres://postgres.<project_ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres`
   (Your shard may be `aws-0` or `aws-1`; it must match what the dashboard shows for the project.) **This repo uses the session pooler for production on App Platform.**
2. **Supabase IPv4 add-on** — Paid option (about **$4/month**; confirm current price in Supabase billing) that exposes **IPv4** for the **direct** connection if you want to avoid the pooler.

**Still avoid port 6543 (transaction pooling)** for this stack: that mode is not the same as session mode and remains a poor fit for asyncpg prepared statements.

---

## Environments

| Environment | `PUBLIC_ENV` value | Where | Purpose |
|---|---|---|---|
| Local dev | `development` | Your machine | Local Supabase stack, permissive defaults |
| Test | `test` | CI / local pytest | Test Postgres DB, conftest sets this |
| Production | `production` | Hosted API + Vercel + Supabase | Strict config, Supabase Auth required |

There is no staging environment. `config.py` accepts exactly three values: `development`, `test`, `production` (legacy `ENV` is still read as a fallback).

### Production guards (hard startup errors, not warnings)

| Guard | What happens |
|---|---|
| `PRIVATE_JWT_SECRET` missing or dev default | `RuntimeError` — app refuses to start |
| `PUBLIC_CORS_ORIGINS` is `*` or empty | `RuntimeError` — app refuses to start |
| `PUBLIC_ALLOW_PUBLIC_AUTH=true` | `RuntimeError` — local login/register would be exposed |
| `PRIVATE_DATABASE_URL` not PostgreSQL | `RuntimeError` |

---

## New environment (step by step)

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. From **Settings > API** / **Settings > API keys**, collect:
   - **Project URL** — `https://xxxx.supabase.co`
   - **Publishable key** — `sb_publishable_...` (public, safe for frontend)
   - **JWT Secret** — under **JWT Settings** (backend validates tokens; not the publishable key)
3. From **Settings > Database** or the **Connect** dialog: for **IPv4-only** API hosts (e.g. DigitalOcean App Platform), use the **Session pooler** connection string (**port 5432**, user like `postgres.<project_ref>`). For environments that can reach the direct hostname over IPv4, use the **direct** connection (**port 5432**). Do not use the **transaction** pooler on **6543** for this backend.

### 2. Deploy the backend

Run the same image built from [backend/Dockerfile](../backend/Dockerfile) on your host (e.g. DigitalOcean App Platform). Configure:

**Required — app will not start without:**

| Variable | Notes |
|---|---|
| `PUBLIC_ENV` | `production` |
| `PRIVATE_DATABASE_URL` | Supabase **5432**: direct URL where IPv4 works; on App Platform prefer **session pooler** URL from **Connect** (not **6543** transaction pooler) |
| `PUBLIC_SUPABASE_URL` | Same project URL as frontend; JWKS |
| `PRIVATE_JWT_SECRET` | Supabase JWT secret from dashboard |
| `PUBLIC_CORS_ORIGINS` | Comma-separated; include all stable Vercel origins |

**Recommended:**

| Variable | Notes |
|---|---|
| `PUBLIC_REDIS_URL` | Required for `PUBLIC_WORKERS > 1` |
| `PUBLIC_WORKERS` | `2` or more with Redis for AI chat concurrency |
| `PUBLIC_FRONTEND_URL` | Vercel production URL — Xero OAuth redirects |
| `PRIVATE_SENTRY_DSN` | Error tracking |
| `PUBLIC_CORS_ORIGIN_REGEX` | e.g. Vercel preview URLs |

**Optional:** AI keys (`PRIVATE_ANTHROPIC_API_KEY`, `PRIVATE_OPENROUTER_API_KEY`, `PRIVATE_OPENAI_API_KEY`), Xero (`PUBLIC_XERO_*`, `PRIVATE_XERO_CLIENT_SECRET`), pool tuning (`PUBLIC_PG_POOL_MAX`).

The process listens on `$PORT` if the platform sets it (see Dockerfile `CMD`).

### 3. Deploy frontend on Vercel

1. Import the repo. Root [vercel.json](../vercel.json) defines build, CSP, and SPA rewrites.
2. Set **build-time** env vars in Vercel (see [frontend/.env.example](../frontend/.env.example)):

| Variable | Notes |
|---|---|
| `VITE_BACKEND_URL` | Public API origin, no trailing slash |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Publishable key |

3. After deploy, add every stable Vercel origin to backend `PUBLIC_CORS_ORIGINS` (production domain, `*.vercel.app` project URL, etc.).

### 4. Create the organization

The schema may create a `"default"` org on first startup. Rename for the client:

```sql
UPDATE organizations SET name = 'ClientName', slug = 'clientname' WHERE id = 'default';
```

### 5. Create the admin user

1. Create the user in **Supabase Dashboard > Authentication > Users**.
2. Set role and `organization_id` in **Supabase SQL Editor**:

   ```sql
   UPDATE auth.users
   SET raw_app_meta_data = jsonb_set(
     jsonb_set(
       COALESCE(raw_app_meta_data, '{}'::jsonb),
       '{role}', '"admin"'
     ),
     '{organization_id}', '"default"'
   )
   WHERE email = 'admin@clientname.com';
   ```

   **`organization_id` is required** in production JWTs or the API returns 401.

3. Create the profile row (see `pixi run create-admin` in backend tooling) so `/api/auth/me` returns enriched data.

### 6. Verify

```bash
pixi run verify -- --url https://api.your-domain.com
```

Check:

- `/api/health` and `GET /api/beta/shared/health` / `/api/ready` as appropriate for your probes
- Browser login via Supabase SDK
- No CORS errors
- WebSockets: `/api/beta/shared/ws` and `/api/beta/assistant/ws/chat`

---

## Auth model (short)

| Concept | Meaning |
|---|---|
| **Organization** | Tenancy boundary; `organization_id` on business data |
| **User** | `users` table; `role` is `admin` or `contractor` |
| **Production** | Supabase JWT; `PRIVATE_JWT_SECRET` must match project; claims from `app_metadata` via `auth_provider.py` |

---

## CI/CD

Pipeline docs live in the [`use-ci-cd` skill](../.cursor/skills/use-ci-cd/SKILL.md) (triggers, path filters, manual runs).

- [.github/workflows/ci.yml](../.github/workflows/ci.yml) - lint (path-gated), tests, reusable CI gate.
- [.github/workflows/cd.yml](../.github/workflows/cd.yml) - production CD on `main` (CI gate, GHCR image, DigitalOcean App Platform, Vercel).

Automated deploy to Vercel / your API host is configured in GitHub Actions, not duplicated in this doc.

### DigitalOcean App Platform + GHCR + Supabase: root cause chain

Short statements of what broke and what fixed it (same order as the failure chain we hit):

| # | Root cause | Fix |
|---|------------|-----|
| 1 | Private GHCR image: each `doctl apps update --spec` replaced the app spec **without** registry credentials, so pulls failed with "Image does not exist or is private". | Put `registry_credentials: "$GHCR_REGISTRY_CREDS"` in `.do/app.yaml` and substitute it in the CD workflow (`envsubst`) from a GitHub secret every deploy. |
| 2 | **`PUBLIC_ENV` unset** on the component: app defaulted to **development**, wrong `.env` profile, and hard-failed on production CORS rules. | Declare `PUBLIC_ENV=production` as a runtime env in the App Platform spec (not only in the image). |
| 3 | **Deploy skipped** `build-backend` / `deploy-backend`: reusable **CI** workflow shared one **concurrency group** with push CI, so runs cancelled each other and `needs: [ci]` left deploy jobs skipped. | Use a workflow-scoped concurrency group, e.g. `ci-${{ github.workflow }}-${{ github.ref }}`. |
| 4 | **`sslmode` in the DB URL** for asyncpg: SQLAlchemy/asyncpg does not accept that as a connect kwarg, causing `unexpected keyword argument 'sslmode'`. | Build the URL without `sslmode`; pass SSL via `connect_args["ssl"]` on `create_async_engine` (e.g. `require`). |
| 5 | **`No route to host`** to `db.<ref>.supabase.co`: App Platform **does not support reaching IPv6-only hosts**; Supabase direct DB may be IPv6-only from the app’s perspective. | Use Supabase **session** pooler on port **5432** (dashboard **Connect**), or Supabase **IPv4 add-on** (~**$4/mo**, confirm in billing) for direct. Pooler host uses `aws-0-` or `aws-1-` plus region per dashboard; user `postgres.<project_ref>`. Wrong shard yields tenant/user errors. |
| 6 | **Production defaults missing inside the image**: `.dockerignore` had `backend/.env.*`, so **`backend/.env.production` was never copied** into the image (wrong or empty non-secret prod defaults). | Ignore only **`.env.local`** (repo root and `backend/`); keep `.env`, `.env.development`, and `.env.production` in the build context. |
| 7 | **`InvalidPasswordError` for user `postgres`**: **`str(SQLAlchemy URL)` masks the password** as literal `***` in the string passed to the engine. | Use `url_obj.render_as_string(hide_password=False)` when materializing `DATABASE_URL` for the engine. |

---

## WebSocket support

| Endpoint | Purpose |
|---|---|
| `GET /api/beta/shared/ws?token=...` | Domain events |
| `GET /api/beta/assistant/ws/chat?token=...` | AI assistant streaming |

With `PUBLIC_WORKERS > 1`, `PUBLIC_REDIS_URL` is required (Redis pub/sub for events).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 401 on all API calls | `PRIVATE_JWT_SECRET` not Supabase secret | Set backend `PRIVATE_JWT_SECRET` from Supabase JWT settings |
| missing `organization_id` claim | `raw_app_meta_data` not set | SQL update on `auth.users` |
| CORS errors | Origin not in `PUBLIC_CORS_ORIGINS` | Add Vercel URLs; use `PUBLIC_CORS_ORIGIN_REGEX` for previews |
| Frontend cannot reach API | Wrong `VITE_BACKEND_URL` | Fix Vercel env, redeploy |
| DB connection fails / prepared statement errors | **Transaction** pooler port **6543** | Use **5432** only: direct URL or **session** pooler, not transaction mode |
| DB timeout / no route from App Platform | **IPv4-only** egress vs IPv6-only Supabase direct host | **Session pooler** (5432) or Supabase **IPv4 add-on**; see [IPv4 section](#digitalocean-app-platform-and-supabase-ipv4) |

---

## Reference files

| File | Purpose |
|---|---|
| [frontend/.env.example](../frontend/.env.example) | Vercel / frontend `VITE_*` template |
| [.env.production.example](../.env.production.example) | Optional `docker compose` root `.env` template |
| [backend/.env.example](../backend/.env.example) | Native local backend |
