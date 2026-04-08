# Exhaustive Environment Variable Reference

Every backend env var, organized by the file where it is defined or expected. Variables use `PUBLIC_*` (non-secret, committable) or `PRIVATE_*` (secret, gitignored/platform-injected) prefixes.

The committed files (`.env`, `.env.development`, `.env.production`) are copied into the Docker image via `COPY backend/ .` and are therefore available inside the DigitalOcean deployment. `.env.local` is **never** in the image.

`PUBLIC_ENV` must be set in the **process environment** (not a dotenv file) to select which profile loads. The `.do/app.yaml` spec sets `PUBLIC_ENV=production` at runtime.

---

## `backend/.env` - Shared non-secret defaults (committed)

Loaded in all environments. Lowest file precedence among backend files.

| Variable | Default | Purpose |
|----------|---------|---------|
| `PUBLIC_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `PUBLIC_REFRESH_TOKEN_EXPIRATION_DAYS` | `7` | Refresh token lifetime |
| `PUBLIC_PG_POOL_MIN` | `2` | Minimum Postgres pool connections |
| `PUBLIC_PG_POOL_MAX` | `10` | Maximum Postgres pool connections |
| `PUBLIC_PG_ACQUIRE_TIMEOUT` | `10` | Pool acquire timeout (seconds) |
| `PUBLIC_PG_COMMAND_TIMEOUT` | `30` | Query timeout (seconds) |
| `PUBLIC_DB_USER` | `postgres` | Postgres username |
| `PUBLIC_DB_NAME` | `postgres` | Postgres database name |
| `PUBLIC_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `PUBLIC_ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Primary Anthropic model |
| `PUBLIC_ANTHROPIC_FAST_MODEL` | `claude-sonnet-4-6` | Fast Anthropic model |
| `PUBLIC_SESSION_COST_CAP` | `2.00` | Max cost per assistant session ($) |
| `PUBLIC_XERO_SYNC_HOUR` | `2` | Hour (UTC) for nightly Xero sync |
| `PUBLIC_LOG_LEVEL` | `INFO` | Application log level |
| `PUBLIC_WORKERS` | `1` | Gunicorn worker count |
| `PUBLIC_REQUEST_TIMEOUT` | `30` | General request timeout (seconds) |
| `PUBLIC_AI_REQUEST_TIMEOUT` | `120` | AI request timeout (seconds) |
| `PUBLIC_MAX_CONCURRENT_GENERATIONS` | `4` | AI generation concurrency limit |
| `PUBLIC_GENERATION_QUEUE_TIMEOUT` | `10` | Queue wait for generation slot (seconds) |
| `PUBLIC_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API base URL |

---

## `backend/.env.development` - Development overrides (committed)

Loaded when `PUBLIC_ENV=development` or `PUBLIC_ENV=test`. Overrides values from `backend/.env`.

| Variable | Value | Purpose |
|----------|-------|---------|
| `PUBLIC_DB_PASSWORD` | `postgres` | Local Supabase default password (safe to commit) |
| `PUBLIC_DB_HOST` | `127.0.0.1` | Local Supabase Postgres host |
| `PUBLIC_DB_PORT` | `54322` | Local Supabase Postgres port |
| `PUBLIC_SUPABASE_URL` | `http://127.0.0.1:54321` | Local Supabase API URL |
| `PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` | Local Supabase anon key |
| `PUBLIC_CORS_ORIGINS` | `*` | Permissive CORS for local dev |
| `PUBLIC_REDIS_URL` | _(empty)_ | No Redis in local dev |
| `PUBLIC_JWT_ACCESS_EXPIRATION_MINUTES` | `480` | Longer tokens for local dev (8 hours) |

---

## `backend/.env.production` - Production non-secrets (committed)

Loaded when `PUBLIC_ENV=production`. Baked into the Docker image and available on DigitalOcean.

| Variable | Value | Purpose |
|----------|-------|---------|
| `PUBLIC_JWT_ACCESS_EXPIRATION_MINUTES` | `15` | Short-lived production tokens |
| `PUBLIC_DB_USER` | `postgres.fjzacucejlieklmmhwsm` | Supavisor session pooler user |
| `PUBLIC_DB_HOST` | `aws-1-us-west-2.pooler.supabase.com` | Supavisor session pooler host (IPv4) |
| `PUBLIC_DB_PORT` | `5432` | Supavisor session pooler port |
| `PUBLIC_DB_SSL_MODE` | `require` | SSL required for hosted DB |
| `PUBLIC_SUPABASE_URL` | `https://fjzacucejlieklmmhwsm.supabase.co` | Hosted Supabase project URL |
| `PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_ZP4_...` | Hosted Supabase anon key |
| `PUBLIC_CORS_ORIGINS` | `https://sku-ops-lac.vercel.app` | Allowed production origins (comma-separated) |
| `PUBLIC_CORS_ORIGIN_REGEX` | _(empty)_ | Optional regex for Vercel preview URLs |
| `PUBLIC_FRONTEND_URL` | `https://sku-ops-lac.vercel.app` | Frontend URL (Xero OAuth redirects) |
| `PUBLIC_XERO_CLIENT_ID` | _(empty)_ | Xero OAuth client ID |
| `PUBLIC_XERO_REDIRECT_URI` | `https://REPLACE.../api/beta/finance/xero/callback` | Xero OAuth callback URL |
| `PUBLIC_WORKERS` | `2` | Production worker count |
| `PUBLIC_PG_POOL_MIN` | `2` | Production pool minimum |
| `PUBLIC_PG_POOL_MAX` | `20` | Production pool maximum |

---

## `backend/.env.local` - Secrets (gitignored)

Highest file precedence. Used for local development secrets. In production, the equivalent values are stored in the GitHub Environment **`backend_digital_ocean_deployment`** and injected into `.do/app.yaml` at deploy time.

Note: For local Supabase development, `PRIVATE_DB_PASSWORD` is not strictly needed (the public default `postgres` from `.env.development` works), and `PRIVATE_JWT_SECRET` uses the legacy local Supabase JWT secret.

| Variable | Type | Purpose |
|----------|------|---------|
| `PUBLIC_ENV` | Control | Set to `development` locally; `production` on DO (set in `.do/app.yaml`) |
| `PRIVATE_DB_PASSWORD` | Secret | Hosted Supabase database password |
| `PRIVATE_JWT_SECRET` | Secret | Supabase project JWT secret (must match Supabase dashboard) |
| `PRIVATE_SENTRY_DSN` | Secret | Sentry DSN for error reporting |
| `PRIVATE_ANTHROPIC_API_KEY` | Secret | Anthropic API key |
| `PRIVATE_OPENAI_API_KEY` | Secret | OpenAI API key |
| `PRIVATE_OPENROUTER_API_KEY` | Secret | OpenRouter API key |
| `PRIVATE_XERO_CLIENT_SECRET` | Secret | Xero OAuth client secret |
| `PRIVATE_SUPABASE_SECRET_KEY` | Secret | Supabase service role key (dev only, not needed in prod app) |

---

## Config-only variables (read by `Config` but not in any default file)

These are read by `config.py` but only set on specific platforms or as overrides:

| Variable | Purpose |
|----------|---------|
| `PRIVATE_DATABASE_URL` | Full Postgres URI override (wins over `PUBLIC_DB_*` parts). Docker/CI/App Platform. |
| `PUBLIC_ALLOW_PUBLIC_AUTH` | Enable public auth bypass (`1`/`true`/`yes`) |
| `PUBLIC_AGENT_PRIMARY_MODEL` | Override primary agent model (else `models.yaml`) |
| `PUBLIC_MODEL_REGISTRY_INFRA_SYNTHESIS` | Override synthesis model |
| `PUBLIC_MODEL_REGISTRY_INFRA_CLASSIFIER` | Override classifier model |
| `PRIVATE_METRICS_TOKEN` | Bearer token for metrics endpoint |
| `PUBLIC_REDIS_URL` | Redis/Valkey URL. In production, injected from DO Valkey binding (`${valkey-cache.DATABASE_URL}`) |

---

## `.do/app.yaml` - DigitalOcean App Platform spec (template)

These are the runtime env vars injected into the DO container. Secrets come from the GitHub Environment `backend_digital_ocean_deployment` via `envsubst` in the CD workflow. The non-secret `PUBLIC_*` values from `.env.production` are already in the Docker image and don't need repeating here.

| Variable | Type | Source |
|----------|------|--------|
| `PUBLIC_ENV` | `GENERAL` | Hardcoded `production` in spec |
| `PRIVATE_DB_PASSWORD` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_JWT_SECRET` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_SENTRY_DSN` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_ANTHROPIC_API_KEY` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_OPENROUTER_API_KEY` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_OPENAI_API_KEY` | `SECRET` | GH Environment -> `envsubst` |
| `PRIVATE_XERO_CLIENT_SECRET` | `SECRET` | GH Environment -> `envsubst` |
| `PUBLIC_REDIS_URL` | `GENERAL` | DO Valkey binding (`${valkey-cache.DATABASE_URL}`) |

Additional spec-level values (not env vars but in the spec):

| Spec field | Source |
|------------|--------|
| `$IMAGE_TAG` | Set by CD workflow (git short SHA or `latest`) |
| `$GHCR_REGISTRY_CREDS` | GH Environment - Docker registry auth for private GHCR image |

---

## GitHub Environment: `backend_digital_ocean_deployment`

All secrets that go into `.do/app.yaml` plus platform auth. These are the same `PRIVATE_*` keys from `.env.local` (production values), plus DO/GHCR auth secrets.

| Secret | Purpose |
|--------|---------|
| `DIGITALOCEAN_ACCESS_TOKEN` | `doctl` API token |
| `DIGITALOCEAN_APP_ID` | App Platform app UUID |
| `GHCR_REGISTRY_CREDS` | `username:PAT` for pulling private GHCR image |
| `PRIVATE_DB_PASSWORD` | Hosted Postgres password |
| `PRIVATE_JWT_SECRET` | Supabase project JWT secret |
| `PRIVATE_SENTRY_DSN` | Sentry DSN |
| `PRIVATE_ANTHROPIC_API_KEY` | Anthropic API key |
| `PRIVATE_OPENROUTER_API_KEY` | OpenRouter API key |
| `PRIVATE_OPENAI_API_KEY` | OpenAI API key |
| `PRIVATE_XERO_CLIENT_SECRET` | Xero OAuth client secret |

---

## GitHub Environment: `supabase_deployment`

Used only by `.github/workflows/supabase.yml` for CLI-driven migrations. Not loaded by the backend runtime.

| Secret | Purpose |
|--------|---------|
| `PRIVATE_ACCESS_TOKEN` | Supabase account access token (for `supabase link`) |
| `PRIVATE_DB_PASSWORD` | Hosted Postgres database password |
| `PUBLIC_PROJECT_ID` | Supabase project ref (from dashboard URL) |

---

## GitHub Environment: `frontend_vercel_deployment`

Used by CD workflow for Vercel CLI auth. Not part of the backend dotenv stack.

| Secret | Purpose |
|--------|---------|
| `VERCEL_TOKEN` | Vercel account token |
| `VERCEL_ORG_ID` | Team/personal org ID |
| `VERCEL_PROJECT_ID` | Linked Vercel project ID |
