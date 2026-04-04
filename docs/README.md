# Documentation index

Repo markdown uses **snake_case** filenames, except **README.md** (package or folder entrypoints) and **SKILL.md** (Cursor skills).

## Deploy and operations

| Document | Purpose |
| --- | --- |
| [deploy.md](deploy.md) | Primary playbook: Railway + Vercel + Supabase |
| [deploy_client.md](deploy_client.md) | Per-client setup on that stack |
| [deployment.md](deployment.md) | VPS / self-hosted Docker |
| [launch_checklist.md](launch_checklist.md) | Production readiness |

## Engineering

| Document | Purpose |
| --- | --- |
| [testing.md](testing.md) | How to run lint, unit, integration, and e2e tests |

## Product and QA narratives

| Document | Purpose |
| --- | --- |
| [day_in_life_user_story.md](day_in_life_user_story.md) | Day-in-the-life user story |
| [executive_financial_story.md](executive_financial_story.md) | Executive financial narrative |
| [manual_walkthrough_checklist.md](manual_walkthrough_checklist.md) | Human walkthrough checklist |

## Data platform notes

| Document | Purpose |
| --- | --- |
| [supabase_context_migration_matrix.md](supabase_context_migration_matrix.md) | Context migration matrix |
| [supabase_cutover_inventory.md](supabase_cutover_inventory.md) | Cutover inventory |

## LLM prompts (co-located with code)

Prompts stay next to their callers under `backend/` (e.g. `backend/assistant/agents/*/prompt.md`, `backend/catalog/application/*_prompt.md`). Paths are referenced from Python via `load_prompt` or explicit `Path` constants.
