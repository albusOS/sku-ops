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
- **Backend** — FastAPI in Docker; connects to Supabase Postgres via `DATABASE_URL`.
- **Auth** (Supabase) — issues JWTs. Backend validates with Supabase `JWT_SECRET`.
- **Database** — Supabase Postgres on port **5432 (direct)**, NOT 6543 (pooler). asyncpg uses prepared statements incompatible with pgbouncer.

---

## Environments

| Environment | `ENV` value | Where | Purpose |
|---|---|---|---|
| Local dev | `development` | Your machine | Local Supabase stack, permissive defaults |
| Test | `test` | CI / local pytest | Test Postgres DB, conftest sets this |
| Production | `production` | Hosted API + Vercel + Supabase | Strict config, Supabase Auth required |

There is no staging environment. `config.py` accepts exactly three values: `development`, `test`, `production`.

### Production guards (hard startup errors, not warnings)

| Guard | What happens |
|---|---|
| `JWT_SECRET` missing or dev default | `RuntimeError` — app refuses to start |
| `CORS_ORIGINS` is `*` or empty | `RuntimeError` — app refuses to start |
| `ALLOW_PUBLIC_AUTH=true` | `RuntimeError` — local login/register would be exposed |
| `DATABASE_URL` not PostgreSQL | `RuntimeError` |

---

## New environment (step by step)

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. From **Settings > API** / **Settings > API keys**, collect:
   - **Project URL** — `https://xxxx.supabase.co`
   - **Publishable key** — `sb_publishable_...` (public, safe for frontend)
   - **JWT Secret** — under **JWT Settings** (backend validates tokens; not the publishable key)
3. From **Settings > Database**, collect the **direct** connection string (port **5432**), not the pooler (6543).

### 2. Deploy the backend

Run the same image built from [backend/Dockerfile](../backend/Dockerfile) on your host (e.g. DigitalOcean App Platform). Configure:

**Required — app will not start without:**

| Variable | Notes |
|---|---|
| `ENV` | `production` |
| `DATABASE_URL` | Supabase direct, port 5432 |
| `SUPABASE_URL` | Same project URL as frontend; JWKS |
| `JWT_SECRET` | Supabase JWT secret from dashboard |
| `CORS_ORIGINS` | Comma-separated; include all stable Vercel origins |

**Recommended:**

| Variable | Notes |
|---|---|
| `REDIS_URL` | Required for `WORKERS > 1` |
| `WORKERS` | `2` or more with Redis for AI chat concurrency |
| `FRONTEND_URL` | Vercel production URL — Xero OAuth redirects |
| `SENTRY_DSN` | Error tracking |
| `CORS_ORIGIN_REGEX` | e.g. Vercel preview URLs |

**Optional:** AI keys (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY`), Xero (`XERO_*`), pool tuning (`PG_POOL_MAX`).

The process listens on `$PORT` if the platform sets it (see Dockerfile `CMD`).

### 3. Deploy frontend on Vercel

1. Import the repo. Root [vercel.json](../vercel.json) defines build, CSP, and SPA rewrites.
2. Set **build-time** env vars in Vercel (see [frontend/.env.example](../frontend/.env.example)):

| Variable | Notes |
|---|---|
| `VITE_BACKEND_URL` | Public API origin, no trailing slash |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Publishable key |

3. After deploy, add every stable Vercel origin to backend `CORS_ORIGINS` (production domain, `*.vercel.app` project URL, etc.).

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
| **Production** | Supabase JWT; `JWT_SECRET` must match project; claims from `app_metadata` via `auth_provider.py` |

---

## CI/CD

GitHub Actions: [.github/workflows/ci.yml](../.github/workflows/ci.yml) — backend lint/test, frontend lint/build/test, Docker image build smoke.

Automated deploy to Vercel / your API host is configured in your CI provider, not duplicated here.

---

## WebSocket support

| Endpoint | Purpose |
|---|---|
| `GET /api/beta/shared/ws?token=...` | Domain events |
| `GET /api/beta/assistant/ws/chat?token=...` | AI assistant streaming |

With `WORKERS > 1`, `REDIS_URL` is required (Redis pub/sub for events).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 401 on all API calls | `JWT_SECRET` not Supabase secret | Set backend `JWT_SECRET` from Supabase JWT settings |
| missing `organization_id` claim | `raw_app_meta_data` not set | SQL update on `auth.users` |
| CORS errors | Origin not in `CORS_ORIGINS` | Add Vercel URLs; use `CORS_ORIGIN_REGEX` for previews |
| Frontend cannot reach API | Wrong `VITE_BACKEND_URL` | Fix Vercel env, redeploy |
| DB connection fails | Using pooler port 6543 | Use direct 5432 `DATABASE_URL` |

---

## Reference files

| File | Purpose |
|---|---|
| [frontend/.env.example](../frontend/.env.example) | Vercel / frontend `VITE_*` template |
| [.env.production.example](../.env.production.example) | Optional `docker compose` root `.env` template |
| [backend/.env.example](../backend/.env.example) | Native local backend |
