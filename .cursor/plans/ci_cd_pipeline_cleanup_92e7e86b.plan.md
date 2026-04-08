---
name: CI/CD Pipeline Cleanup
overview: Eliminate duplicate test runs on main by making ci.yml only trigger standalone on dev/PRs, and rename deploy.yml to cd.yml for conventional naming. Document the full pipeline in docs/ci-cd.md.
todos:
  - id: fix-ci-trigger
    content: "Remove `main` from ci.yml push branches and add `workflow_dispatch` (line 5: `[main, dev]` -> `[dev]`, plus manual trigger)"
    status: completed
  - id: rename-deploy
    content: Rename deploy.yml to cd.yml, update name and all self-references in path filters
    status: completed
  - id: update-hardening-rule
    content: Update deployment-hardening.mdc globs and CI/CD prose for new filenames/triggers
    status: completed
  - id: write-docs
    content: Write docs/ci-cd.md with trigger table, job graph, concurrency, and test strategy
    status: completed
  - id: verify-pipeline
    content: Push to main and verify only CD triggers, no duplicate CI run
    status: completed
isProject: false
---

# CI/CD Pipeline Cleanup

## Problem

Every push to `main` triggers both `ci.yml` (standalone) and `deploy.yml` (which calls `ci.yml` via `workflow_call`). Tests run twice - ~18min of compute for ~9min of actual testing. The standalone CI run usually gets cancelled mid-flight anyway (by the next push's concurrency group), wasting the partial run.

## Root Cause

[`ci.yml`](.github/workflows/ci.yml) line 5: `branches: [main, dev]` fires standalone on main pushes, while [`deploy.yml`](.github/workflows/deploy.yml) line 76: `uses: ./.github/workflows/ci.yml` also calls it. Two independent triggers, same tests.

## Solution: Single trigger per branch

| Event | `ci.yml` (standalone) | `cd.yml` (was deploy.yml) |
|-------|----------------------|---------------------------|
| Push to `dev` | Fires | No |
| Push to `main` | No (called by cd.yml) | Fires -> calls ci.yml |
| PR to `main`/`dev` | Fires | No |
| `workflow_dispatch` | Runs full CI on chosen ref | Runs full pipeline (CI gate + conditional deploy) on chosen ref |

## Changes

### 1. `ci.yml` - Remove main from push trigger + manual run

- Line 5: Change `branches: [main, dev]` to `branches: [dev]`
- Add `workflow_dispatch:` under `on:` so agents/CLI can run CI without a push (same jobs as a normal CI run; use `--ref` to pick branch)
- Keep `pull_request: branches: [main, dev]` (PRs still get CI)
- Keep `workflow_call:` (cd.yml still calls it)
- Everything else stays identical

### 2. Rename `deploy.yml` to `cd.yml`

- Rename file: `.github/workflows/deploy.yml` -> `.github/workflows/cd.yml`
- Update `name: Deploy` to `name: CD`
- **Keep** existing `workflow_dispatch:` (already present; no change except file rename) so manual deploy-from-CLI still works
- Update all self-references in path filters (lines 10, 51, 56, 59):
  - `.github/workflows/deploy.yml` -> `.github/workflows/cd.yml`
- No other workflow files reference `deploy.yml`

### 3. Update `deployment-hardening.mdc`

- [`deployment-hardening.mdc`](.cursor/rules/deployment-hardening.mdc) line 3 globs: update `deploy.yml` -> `cd.yml`
- Lines 50-52: Update CI/CD section prose to reflect new trigger logic and filenames

### 4. Write `docs/ci-cd.md`

Document the full pipeline with:
- Trigger table (what fires when)
- **Manual runs (CLI / agents):** `gh workflow run CI --ref <branch>`, `gh workflow run CD --ref main` (workflow file names: `ci.yml`, `cd.yml` after rename). Note `CD` manual run uses the existing `workflow_dispatch` branch in `changes` resolve step (deploy all components unless you rely on push-only path filters - see note below)
- Job dependency graph (mermaid)
- Path-filter logic for conditional lint/deploy
- Concurrency behavior (CI cancels stale on dev; CD serializes on main)
- Test strategy: lint is gated by changes, tests always run both suites (cross-stack regression safety)

**Note on manual `CD`:** [`deploy.yml`](.github/workflows/deploy.yml) already sets `backend_build`, `backend_deploy`, and `frontend` all to `true` when `github.event_name == 'workflow_dispatch'`, so a manual CD run is a full gate + full deploy path - appropriate for "ship from CLI". No change needed beyond documenting it.

## What stays the same

- **All job definitions** in ci.yml (changes, backend-lint, backend-test, frontend-lint, frontend-test) are untouched
- **Test strategy**: both backend and frontend tests always run; lint is conditional on path changes
- **cd.yml internals**: CI gate, path-conditional build, path-conditional deploy - all unchanged
- **codegen.yml**: independent, not touched in this PR
- **Concurrency groups**: CI uses `ci-$workflow-$ref` (cancel stale), CD uses `deploy-prod` (serialize)

## Validation

After merging, the next push to main should show:
- Only ONE workflow triggered: `CD`
- CI gate runs tests once inside `CD`
- No orphaned standalone `CI` run on main
- Push to dev still triggers standalone `CI` as before

## Pipeline visualization (proposed)

```
Push to dev:
  ci.yml -> changes -> [backend-lint?] [frontend-lint?] [backend-test] [frontend-test]

Push to main:
  cd.yml -> changes -> ci.yml (gate) -> [build-backend?] -> [deploy-backend?]
                                      -> [deploy-frontend?]

PR to main/dev:
  ci.yml -> changes -> [backend-lint?] [frontend-lint?] [backend-test] [frontend-test]

Manual (anytime):
  gh workflow run ci.yml --ref dev|main   -> standalone CI
  gh workflow run cd.yml --ref main       -> CD (CI gate + full deploy; dispatch sets all change flags true)
```

`?` = conditional on path changes