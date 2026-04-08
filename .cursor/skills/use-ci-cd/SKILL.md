---
name: use-ci-cd
description: Operate the CI/CD pipeline - trigger CI or CD workflows, interpret run results, and fix failures. Use when the user mentions CI, CD, pipelines, deploy, tests failing in CI, GitHub Actions, workflow runs, or asks to ship/deploy code. Also use when you need to verify code changes pass CI before merging.
---

# CI/CD Pipeline

Three GitHub Actions workflows: **CI** (`ci.yml`), **CD** (`cd.yml`), and **Supabase** (`supabase.yml`). For full details see [references/overview.md](references/overview.md).

## What fires when

| Event | CI | CD | Supabase |
|-------|----|----|----------|
| Push to `dev` | Yes | No | Yes, when [path filters](references/overview.md#supabase-behavior-supabaseyml) match |
| Push to `main` | No (called by CD) | Yes, when CD path filters match | Yes, when Supabase path filters match |
| PR to `main`/`dev` | Yes | No | Yes, when Supabase path filters match |
| `workflow_dispatch` | Yes | Yes | Yes |

**Key rule:** pushes to `main` never trigger standalone CI - CD calls `ci.yml` as its gate. No duplicate runs.

## CI jobs (ci.yml)

All jobs are gated by `dorny/paths-filter` on the `changes` job:

- **Backend lint**: `backend/**` or `supabase/**` changed
- **Backend test**: `backend/**` or `supabase/**` changed
- **Frontend lint**: `frontend/**` changed
- **Frontend test**: `backend/**`, `supabase/**`, **or** `frontend/**` changed (backend changes trigger frontend tests to catch cross-stack regressions)

If nothing in `backend/`, `supabase/`, or `frontend/` changed, all four jobs are skipped.

## CD jobs (cd.yml)

`changes` -> `ci` (gate) -> `build-backend` (if changed) -> `deploy-backend` (if changed) + `deploy-frontend` (if changed)

On `workflow_dispatch`, all deploy flags forced `true` (full pipeline).

## Supabase jobs (supabase.yml)

`typegen-check` -> `db-test` -> `db-push` (only on `main` via `push` or `workflow_dispatch`, not on PRs)

Does not gate CD; runs in parallel when paths match. Production migration push requires GitHub Environment **`supabase_deployment`** secrets (`PRIVATE_ACCESS_TOKEN`, `PRIVATE_DB_PASSWORD`, `PUBLIC_PROJECT_ID`; see overview).

## Commands

```bash
# Run CI on a branch
gh workflow run ci.yml --ref dev
gh workflow run ci.yml --ref main

# Deploy everything (CI gate + full deploy)
gh workflow run cd.yml --ref main

# Supabase: typegen check, SQLModel tests, push migrations (if main)
gh workflow run supabase.yml --ref main

# List recent runs
gh run list --branch "$(git branch --show-current)" --limit 5

# Watch a run until completion
gh run watch --exit-status

# Inspect a failed run
gh run view <run-id> --log-failed
```

## Concurrency

- **CI**: `ci-$workflow-$ref`, cancel-in-progress. Rapid pushes cancel stale runs.
- **CD**: `deploy-prod`, never cancels in-flight deploys. Queues behind running deploy.
- **Supabase**: `supabase-$ref`, cancel-in-progress.

## Companion skills

When CI/CD needs monitoring or fixing, use these:

- **`/ci-watcher`**: Delegate to watch pipeline status, report pass/fail with logs. Use when waiting on CI results or when CI has failed and you need details.
- **`/fix-ci`**: Identify the failing job, extract the root error, apply the smallest fix. Use when a specific CI check is red.
- **`/loop-on-ci`**: Watch CI, fix failures, commit, push, repeat until green. Use when iterating to get a branch green.

## Decision guide

| Situation | Action |
|-----------|--------|
| Pushed to `dev`, want to check tests | `gh run list --branch dev --limit 3` or use `/ci-watcher` |
| Need to verify a fix passes CI before PR | `gh workflow run ci.yml --ref <branch>`, then `/ci-watcher` |
| CI is red, need to fix it | Use `/fix-ci` |
| Want to iterate until green | Use `/loop-on-ci` |
| Ready to deploy app to production | Merge to `main` (CD auto-fires when backend/frontend paths match) or `gh workflow run cd.yml --ref main` |
| DB migrations merged to `main`, need prod schema updated | `supabase.yml` auto-fires when `supabase/**` (or typegen paths) changed, or `gh workflow run supabase.yml --ref main` |
| Deploy failed | Use `/ci-watcher` to get logs, then `/fix-ci` on the failure |
