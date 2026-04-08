---
name: use-environment
description: Manage backend environment variables, dotenv file hierarchy, and the Config singleton. Use when adding, modifying, or debugging env vars, changing PUBLIC_ENV, editing .env files, updating secrets for DigitalOcean or GitHub Actions, or troubleshooting config loading.
---

# Environment Configuration

## Key concepts

- **`PUBLIC_*`** prefix = non-secret (committed). **`PRIVATE_*`** prefix = secret (gitignored / platform-injected).
- **`PUBLIC_ENV`** is the control variable: `development` | `test` | `production`. It selects which profile file loads (`.env.development` or `.env.production`). Must be set in the **process environment** before Python starts - dotenv files cannot override it once set.
- Process env keys present before `env.py` imports are **never overwritten** by dotenv files.

## File hierarchy (backend/)

| File | Committed | Purpose |
|------|-----------|---------|
| `.env` | Yes | Shared non-secret defaults (pool sizes, model names, timeouts) |
| `.env.development` | Yes | Local dev overrides (DB host, Supabase URL, permissive CORS) |
| `.env.production` | Yes | Production non-secrets (DB host/port/SSL, Supabase URL, CORS, Xero) |
| `.env.local` | No | Secrets (`PRIVATE_*`). Highest file precedence. This represents the local development version of the secrets that should be injected by the platform. |

**Merge order (later wins):** `repo/.env` < `backend/.env` < `backend/.env.{profile}` < `backend/.env.local`

## Docker image and deployment flow

The committed env files (`.env`, `.env.development`, `.env.production`) are **copied into the Docker image** via `COPY backend/ .` in the Dockerfile. The image is pushed to GHCR and deployed on DigitalOcean App Platform. So non-secret `PUBLIC_*` values from these files are accessible inside the running container.

**Secrets** (`PRIVATE_*`) are **never in the image**. They live in:
1. `backend/.env.local` for local development
2. GitHub Actions Environments:
   - `backend_digital_ocean_deployment` for production - injected via `envsubst` into `.do/app.yaml` at deploy time
   - `frontend_vercel_deployment` for Vercel deployment - injected via `secrets` at deploy time
   - `supabase_deployment` for Supabase migrations - injected via `secrets` at deploy time

The `.do/app.yaml` spec sets `PUBLIC_ENV=production` as a runtime env var, which causes `env.py` to load `.env.production` (already in the image) as the profile file. Platform-injected `PRIVATE_*` secrets become process env keys, so they always win over any file value.

## Adding a new env var

1. Choose prefix: `PUBLIC_` (non-secret, committable) or `PRIVATE_` (secret)
2. Add to the right file:
   - Shared non-secret -> `backend/.env`
   - Dev non-secret -> `backend/.env.development`
   - Prod non-secret -> `backend/.env.production`
   - Local secret -> `backend/.env.local` + GitHub Actions Environment
3. Add a `@property` on `Config` in `backend/shared/infrastructure/config.py`
4. Update `backend/.env.example` and `backend/.env.local.example`
5. If secret needed in production: add to `.do/app.yaml` envs section + add to `backend_digital_ocean_deployment` GitHub Environment + add to `envsubst` variable list in `.github/workflows/cd.yml`

## Config singleton usage

```python
from shared.infrastructure.config import config

config.DATABASE_URL      # postgresql+asyncpg://...
config.ENV               # "development" | "test" | "production"
config.is_production     # bool
config.ANTHROPIC_API_KEY # reads PRIVATE_ANTHROPIC_API_KEY
```

## Hot reload (dev only)

`PUBLIC_ENV=development` triggers debounced (2s) re-merge of `.env`, `.env.development`, `.env.local` on each `config.*` access. No restart needed for env file edits. Pool/CORS/Sentry changes still require restart.

## Production caching

`PUBLIC_ENV=production` caches `os.environ` reads per key on first access. Runtime mutation of `os.environ` is invisible through cached keys.

## Troubleshooting

- **Wrong DB/mode in tests:** `conftest.py` sets `PUBLIC_ENV=test` before imports.
- **Key not picking up:** If set in shell/pixi/platform before Python starts, dotenv cannot override it.
- **Production CORS crash:** Empty or `*` `PUBLIC_CORS_ORIGINS` raises at startup.

## References

- Full environment docs: [references/overview.md](references/overview.md)
- Exhaustive env var list: [references/env_vars.md](references/env_vars.md)
- Implementation: `backend/shared/infrastructure/env.py`, `backend/shared/infrastructure/config.py`
- Deploy spec template: `.do/app.yaml`
- CI/CD workflows: `.github/workflows/cd.yml`, `.github/workflows/ci.yml`
