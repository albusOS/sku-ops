---
name: use-ci-cd
description: Operate the CI/CD pipeline - trigger CI or CD workflows, interpret run results, and fix failures. Use when the user mentions CI, CD, pipelines, deploy, tests failing in CI, GitHub Actions, workflow runs, or asks to ship/deploy code. Also use when you need to verify code changes pass CI before merging.
---

# CI/CD Pipeline

Two GitHub Actions workflows: **CI** (`ci.yml`) and **CD** (`cd.yml`). For full details see [references/overview.md](references/overview.md).

## What fires when

| Event | CI | CD |
|-------|----|----|
| Push to `dev` | Yes | No |
| Push to `main` | No (called by CD) | Yes |
| PR to `main`/`dev` | Yes | No |
| `workflow_dispatch` | Yes | Yes |

**Key rule:** pushes to `main` never trigger standalone CI - CD calls `ci.yml` as its gate. No duplicate runs.

## CI jobs

All jobs are gated by `dorny/paths-filter` on the `changes` job:

- **Backend lint**: `backend/**` or `supabase/**` changed
- **Backend test**: `backend/**` or `supabase/**` changed
- **Frontend lint**: `frontend/**` changed
- **Frontend test**: `backend/**`, `supabase/**`, **or** `frontend/**` changed (backend changes trigger frontend tests to catch cross-stack regressions)

If nothing in `backend/`, `supabase/`, or `frontend/` changed, all four jobs are skipped.

## CD jobs

`changes` -> `ci` (gate) -> `build-backend` (if changed) -> `deploy-backend` (if changed) + `deploy-frontend` (if changed)

On `workflow_dispatch`, all deploy flags forced `true` (full pipeline).

## Commands

```bash
# Run CI on a branch
gh workflow run ci.yml --ref dev
gh workflow run ci.yml --ref main

# Deploy everything (CI gate + full deploy)
gh workflow run cd.yml --ref main

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

## Companion skills

When CI/CD needs monitoring or fixing, use these:

- **`/ci-watcher`**: Delegate to watch pipeline status, report pass/fail with logs. Use when waiting for CI results or when CI has failed and you need details.
- **`/fix-ci`**: Identify the failing job, extract the root error, apply the smallest fix. Use when a specific CI check is red.
- **`/loop-on-ci`**: Watch CI, fix failures, commit, push, repeat until green. Use when iterating to get a branch green.

## Decision guide

| Situation | Action |
|-----------|--------|
| Pushed to `dev`, want to check tests | `gh run list --branch dev --limit 3` or use `/ci-watcher` |
| Need to verify a fix passes CI before PR | `gh workflow run ci.yml --ref <branch>`, then `/ci-watcher` |
| CI is red, need to fix it | Use `/fix-ci` |
| Want to iterate until green | Use `/loop-on-ci` |
| Ready to deploy to production | Merge to `main` (CD auto-fires) or `gh workflow run cd.yml --ref main` |
| Deploy failed | Use `/ci-watcher` to get logs, then `/fix-ci` on the failure |
