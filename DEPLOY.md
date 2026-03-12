# Deployment Runbook — Railway + Vercel + Supabase

Follow these steps **in order**. Steps have dependencies on each other.

---

## Prerequisites

- Railway account, project created, Postgres plugin added
- Vercel account, project connected to this repo
- Supabase project created (free tier is fine)
- This repo pushed to GitHub and connected to both Railway and Vercel

---

## Step 1 — Supabase: collect your credentials

Go to **Supabase Dashboard → Settings → API**.

Copy these — you'll need them in every step below:

| What | Where | Used by |
|---|---|---|
| Project URL | `https://xxxx.supabase.co` | Vercel build env, frontend |
| Anon (public) key | long `eyJ...` string | Vercel build env, frontend |
| JWT Secret | under "JWT Settings" | Railway env var |

> **The JWT Secret is not the anon key.** It's a separate secret. If you set the wrong value in Railway, every API request returns 401.

---

## Step 2 — Supabase: create your first user

1. Go to **Authentication → Users → Invite user** (or Add user).
2. Enter your email and password.
3. Copy the UUID from the `id` column in the Users list — you'll need it in Step 4.

---

## Step 3 — Railway: set environment variables

In your Railway service, go to **Variables** and set all of the following.

### Required (app won't start without these)

```
ENV=production
DATABASE_URL=<see note below>
JWT_SECRET=<Supabase JWT Secret from Step 1>
CORS_ORIGINS=https://<your-vercel-app>.vercel.app
```

> **DATABASE_URL must use port 5432 (direct connection), not 6543 (pgbouncer).**
>
> In Railway's Postgres plugin, go to **Connect → Available Variables** and copy
> `DATABASE_URL` — this is the direct connection string. Do NOT use the pooler URL.
> asyncpg uses prepared statements which are incompatible with pgbouncer.

### Strongly recommended

```
FRONTEND_URL=https://<your-vercel-app>.vercel.app
SENTRY_DSN=https://...@sentry.io/...
```

### AI features (set at least one to enable the assistant and OCR)

```
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-...          # only needed for semantic product search embeddings
```

### Optional

```
WORKERS=1                      # increase to 2×CPU+1 if Railway plan supports it; requires REDIS_URL if >1
REDIS_URL=redis://...          # required only if WORKERS > 1
LOG_LEVEL=INFO
SESSION_COST_CAP=2.00          # per-session AI spend cap in USD
XERO_CLIENT_ID=
XERO_CLIENT_SECRET=
XERO_REDIRECT_URI=https://<your-railway-domain>/api/xero/callback
```

After setting all variables, **deploy**. Watch the startup logs. A healthy start looks like:

```
INFO  Database initialized
INFO  LLM provider initialized
INFO  WebSocket endpoints verified: ['/api/ws', '/api/ws/chat']
INFO  Database connectivity verified
INFO  Application ready — env=production, db=postgres, ...
```

If you see a `RuntimeError` on startup, the error message will tell you exactly which required variable is missing.

---

## Step 4 — Provision your admin user in the database

The backend needs a row in its local `users` table that matches your Supabase user's UUID. Run this from the project root:

```bash
PYTHONPATH=backend:. uv run python backend/scripts/create_admin.py \
    --id <supabase-user-uuid-from-step-2> \
    --email you@example.com \
    --name "Your Name"
```

> This connects to whatever `DATABASE_URL` is in `backend/.env`. For production, temporarily set `DATABASE_URL` to your Railway Postgres direct URL, run the script, then remove it.
>
> Alternatively, run this inside a Railway shell (Railway CLI: `railway run python backend/scripts/create_admin.py ...`).

The script will also print the SQL you need to run next.

---

## Step 5 — Supabase: set the admin role on your user

Run this in **Supabase Dashboard → SQL Editor**:

```sql
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(
  COALESCE(raw_app_meta_data, '{}'::jsonb),
  '{role}', '"admin"'
)
WHERE email = 'you@example.com';
```

> **This step is not optional.** Without it, `app_metadata.role` is empty and every API request returns 401, even with a valid session. The backend requires a role claim; it will never default to admin.

---

## Step 6 — Verify the backend is healthy

```bash
curl https://<your-railway-domain>/api/health
# → {"status":"ok","version":"0.1.0","env":"production","uptime_seconds":...}

curl https://<your-railway-domain>/api/ready
# → {"status":"ok","checks":{"database":{"status":"ok",...},...}}
```

If `/api/ready` returns `503`, check the `checks` object — it will identify which subsystem is unhealthy.

---

## Step 7 — Vercel: set build-time environment variables

Go to **Vercel → Project → Settings → Environment Variables** and add:

```
VITE_SUPABASE_URL=https://xxxx.supabase.co          (from Step 1)
VITE_SUPABASE_ANON_KEY=eyJ...                        (from Step 1)
VITE_BACKEND_URL=https://<your-railway-domain>       (no trailing slash)
```

> These are baked into the JavaScript bundle at build time. Setting them after a
> deploy has no effect — a new deploy is required.

---

## Step 8 — Vercel: trigger a deployment

Push a commit, or manually trigger a redeploy from the Vercel dashboard. Confirm the build picks up the env vars (check the build logs for `VITE_SUPABASE_URL` being used).

---

## Step 9 — End-to-end smoke test

1. Open the Vercel URL in an incognito window.
2. Log in with the email/password from Step 2.
3. Confirm you land on the dashboard (not a 401 or blank screen).
4. Open the browser console — confirm no CORS errors and no failed API calls.
5. Hit `https://<railway-domain>/api/ready` — confirm all checks pass.

---

## Common failure modes

| Symptom | Most likely cause |
|---|---|
| Backend crashes on startup | Missing required env var — read the `RuntimeError` message |
| Every API request returns 401 | `JWT_SECRET` doesn't match Supabase JWT Secret, OR `app_metadata.role` not set (Step 5) |
| Login succeeds but app is broken | `users` row not provisioned (Step 4) — `/api/auth/me` falls back to sparse claims |
| Frontend can't reach backend | `VITE_BACKEND_URL` wrong or missing, or `CORS_ORIGINS` doesn't match Vercel URL |
| DB connection fails | `DATABASE_URL` using port 6543 (pgbouncer) instead of 5432 (direct) |
| WebSocket broken | `VITE_BACKEND_URL` not set — WS URLs fall back to relative path which doesn't work cross-origin |
| AI assistant disabled | No `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` set |

---

## Re-deploying after config changes

- **Railway env var change**: Railway auto-redeploys. No build needed.
- **Vercel `VITE_*` change**: Must trigger a new Vercel build — env is baked at build time.
- **Supabase JWT Secret rotation**: Update `JWT_SECRET` in Railway immediately. All existing sessions will be invalidated — users must log in again.

---

## Adding more users (post-launch)

1. Create user in Supabase Dashboard → Authentication → Users.
2. Run `create_admin.py` with their Supabase UUID and desired role.
3. Set `app_metadata.role` in Supabase SQL Editor.

For non-admin roles, use `--role contractor` or `--role viewer` in Step 2,
and set `'{role}', '"contractor"'` in the SQL in Step 3.
