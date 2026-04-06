---
name: Production deploy hardening
overview: Fix the Gunicorn temp dir issue for DO App Platform, add GHCR registry credentials and ingress to the app spec, switch CI tests from bare Postgres to Supabase CLI (matching local dev), and add scope/type annotations to env vars.
todos:
  - id: fix-dockerfile-cmd
    content: Add --worker-tmp-dir /dev/shm to gunicorn CMD in backend/Dockerfile
    status: completed
  - id: fix-app-yaml
    content: "Fix .do/app.yaml: add registry_credentials, ingress block, scope on envs, fix region slug"
    status: completed
  - id: fix-ci-supabase
    content: Switch ci.yml backend job from bare Postgres service to supabase/setup-cli + supabase start/reset
    status: completed
  - id: update-rules
    content: Update deployment-hardening.mdc with gunicorn tmp dir requirement
    status: completed
isProject: false
---

# Production Deploy Hardening

## Answers to your questions first

### Gunicorn temp dir issue - YES, you will hit this

Even though you're building on GHCR and not on DO, **App Platform still runs the container**. The limitation is about the runtime, not the build. The Gunicorn `--worker-tmp-dir /dev/shm` fix is required. Your current CMD in [`backend/Dockerfile`](backend/Dockerfile) line 51 is missing it.

### `/var/run` issue - NO

You use `python:3.13-slim-bookworm` (Debian), not Alpine. This only affects Alpine-based images.

### Where to keep env vars for `.do/app.yaml`

Three tiers:

- **Non-sensitive, version-controlled**: In [`.do/app.yaml`](.do/app.yaml) directly (ENV, PORT, WORKERS, LOG_LEVEL, pool sizes). Already done correctly.
- **Secrets**: Set via `doctl` or the DO dashboard after first deploy. The `type: SECRET` entries in the spec are placeholders - after first `doctl apps create --spec .do/app.yaml`, you update them once via dashboard. The encrypted values persist across spec updates.
- **Per-environment overrides**: If you later add a staging/preview app, create a separate spec file (e.g. `.do/app-preview.yaml`) or use `doctl apps update` with `--env` flags.

The current approach of `REPLACE_VIA_DASHBOARD` placeholders is the standard pattern. You never check real secret values into the YAML.

---

## Changes needed

### 1. Fix Dockerfile Gunicorn CMD for App Platform compatibility

In [`backend/Dockerfile`](backend/Dockerfile), add `--worker-tmp-dir /dev/shm` to the gunicorn command:

```dockerfile
CMD ["sh", "-c", "gunicorn main:app --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS:-1} --worker-class uvicorn.workers.UvicornWorker --worker-tmp-dir /dev/shm --timeout 120 --graceful-timeout 30 --keep-alive 5 --access-logfile -"]
```

### 2. Fix `.do/app.yaml` against the official spec

Issues found by cross-referencing the [App Spec Reference](https://docs.digitalocean.com/products/app-platform/reference/app-spec/):

- **Missing `registry_credentials`**: GHCR requires `$username:$access_token` for App Platform to pull the image. This is a required field for `registry_type: GHCR`. The value gets encrypted after first submission.
- **Missing `ingress` block**: The `routes` field is deprecated. App Platform now uses the `ingress` top-level key to route traffic to components.
- **Missing `scope` on env vars**: Env vars should specify `scope: RUN_TIME` (default) or `RUN_AND_BUILD_TIME`. Since we use a pre-built image, all vars are `RUN_TIME` only. Being explicit is better.
- **`region` value**: `nyc` should be a full region slug like `nyc1` or `nyc3` depending on your preference.

### 3. Switch CI backend tests from bare Postgres to Supabase CLI

Current state: [`ci.yml`](.github/workflows/ci.yml) spins up a bare `postgres:16-alpine` Docker service and connects tests to it. This means tests run against an empty database without your Supabase migrations or seeds.

Local dev: `pixi run tests backend` runs `supabase db reset --local` which applies all migrations + seeds, then pytest. This is the correct flow.

The CI workflow should match local dev:

- Remove the `services.postgres` block
- Add `supabase/setup-cli@v1` step (already used in [`codegen.yml`](.github/workflows/codegen.yml))
- Add `supabase start` to boot the local Supabase stack (includes Postgres on :54322)
- Run `supabase db reset --local` to apply migrations + seeds
- Update `DATABASE_URL` to `postgresql://postgres:postgres@127.0.0.1:54322/postgres` (matches local dev)
- Add `supabase stop` in an `if: always()` cleanup step

This makes CI and local dev use the exact same database setup path - migrations, seeds, RLS policies, everything.

### 4. Update deployment-hardening cursor rule

Add the `--worker-tmp-dir /dev/shm` requirement to the Docker section in [`.cursor/rules/deployment-hardening.mdc`](.cursor/rules/deployment-hardening.mdc).

---

## Files changed

- [`backend/Dockerfile`](backend/Dockerfile) - add `--worker-tmp-dir /dev/shm` to CMD
- [`.do/app.yaml`](.do/app.yaml) - add `registry_credentials`, `ingress`, `scope` on envs, fix `region`
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) - replace bare Postgres with Supabase CLI
- [`.cursor/rules/deployment-hardening.mdc`](.cursor/rules/deployment-hardening.mdc) - document gunicorn tmp dir requirement
