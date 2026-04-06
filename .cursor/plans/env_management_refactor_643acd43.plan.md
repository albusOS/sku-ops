---
name: Env management refactor
overview: Refactor environment variable management into a layered .env file system with a singleton Config class that supports hot-reload in development, replacing the current flat module-level exports in config.py while maintaining backward compatibility across ~30 import sites.
todos:
  - id: env-files-backend
    content: Create backend/.env, .env.development, .env.production, .env.local with correct variable classification
    status: completed
  - id: env-files-frontend
    content: Create frontend/.env.development, .env.production, .env.local and migrate current frontend/.env contents
    status: completed
  - id: gitignore
    content: Update .gitignore to allow committed env files and ignore .env.local files
    status: completed
  - id: env-py
    content: Create backend/shared/infrastructure/env.py with Env/DevelopmentEnv/ProductionEnv dataclasses and layered dotenv loading
    status: completed
  - id: config-py-rewrite
    content: Rewrite backend/shared/infrastructure/config.py as Config singleton with property-based access and dev hot-reload via lazy dotenv re-read
    status: completed
  - id: migrate-imports
    content: Update ~30 backend files to use config.X instead of bare name imports from config
    status: completed
  - id: consolidate-scattered-env
    content: Move 6 scattered os.environ.get calls (WORKERS, LOG_LEVEL, METRICS_TOKEN, REQUEST_TIMEOUT, AI_REQUEST_TIMEOUT, MAX_CONCURRENT_GENERATIONS, GENERATION_QUEUE_TIMEOUT) into Config
    status: completed
  - id: update-examples
    content: Update backend/.env.example and frontend/.env.example to document new file structure
    status: completed
  - id: docs-environment-md
    content: Create docs/environment.md documenting the .env file hierarchy, inheritance pattern, Config class usage, hot-reload behavior, and production vs development differences
    status: completed
  - id: test-verify
    content: Run backend tests to verify nothing breaks, check config loads correctly in dev and test modes
    status: completed
isProject: false
---

# Environment Management Refactor

## Current State

[`backend/shared/infrastructure/config.py`](backend/shared/infrastructure/config.py) exports ~40 module-level variables (`DATABASE_URL`, `JWT_SECRET`, `SUPABASE_URL`, etc.) that are read once at import time via `os.environ.get(...)`. These are imported by ~30 backend files as bare names:

```python
from shared.infrastructure.config import DATABASE_URL, is_production, CORS_ORIGINS
```

There are also 6 files that read `os.environ` directly outside config.py: `startup.py` (`WORKERS`), `logging_config.py` (`LOG_LEVEL`), `prometheus.py` (`METRICS_TOKEN`), `middleware/timeout.py` (`REQUEST_TIMEOUT`, `AI_REQUEST_TIMEOUT`), `assistant/infrastructure/concurrency.py` (`MAX_CONCURRENT_GENERATIONS`, `GENERATION_QUEUE_TIMEOUT`).

The frontend uses 4 `VITE_*` vars via Vite's built-in `import.meta.env` - that mechanism is already correct and needs only file reorganization.

## Target Architecture

### .env File Hierarchy

```
sku-ops/
  backend/
    .env                  # shared vars (same in dev & prod) - COMMITTED
    .env.development      # dev-only non-sensitive overrides - COMMITTED
    .env.production       # prod-only non-sensitive overrides - COMMITTED
    .env.local            # sensitive secrets (API keys, passwords) - GITIGNORED
    .env.example          # keep as documentation template - COMMITTED
  frontend/
    .env                  # shared vars (same in dev & prod) - COMMITTED
    .env.development      # dev-only non-sensitive overrides - COMMITTED  
    .env.production       # prod-only non-sensitive overrides - COMMITTED
    .env.local            # sensitive secrets - GITIGNORED
    .env.example          # keep as documentation template - COMMITTED
```

Load order (later files override earlier):
1. `backend/.env` (shared defaults)
2. `backend/.env.{development|production}` (environment-specific)
3. `backend/.env.local` (secrets, never committed)

### Variable Classification

**backend/.env** (committed, shared across envs):
- `JWT_ALGORITHM=HS256`
- `JWT_ACCESS_EXPIRATION_MINUTES=15`
- `REFRESH_TOKEN_EXPIRATION_DAYS=7`
- `PG_POOL_MIN=2`
- `PG_POOL_MAX=10`
- `PG_ACQUIRE_TIMEOUT=10`
- `PG_COMMAND_TIMEOUT=30`
- `EMBEDDING_MODEL=text-embedding-3-small`
- `ANTHROPIC_MODEL=claude-sonnet-4-6`
- `ANTHROPIC_FAST_MODEL=claude-sonnet-4-6`
- `SESSION_COST_CAP=2.00`
- `XERO_SYNC_HOUR=2`
- `LOG_LEVEL=INFO`
- `WORKERS=1`
- `REQUEST_TIMEOUT=30`
- `AI_REQUEST_TIMEOUT=120`
- `MAX_CONCURRENT_GENERATIONS=4`
- `GENERATION_QUEUE_TIMEOUT=10`

**backend/.env.development** (committed):
- `ENV=development`
- `DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- `SUPABASE_URL=http://127.0.0.1:54321`
- `CORS_ORIGINS=*`
- `REDIS_URL=` (empty - optional in dev)

**backend/.env.production** (committed):
- `ENV=production`
- `WORKERS=2`
- `PG_POOL_MIN=2`
- `PG_POOL_MAX=20`

**backend/.env.local** (gitignored - secrets):
- `DATABASE_URL=` (prod override if needed)
- `JWT_SECRET=`
- `SUPABASE_SECRET_KEY=`
- `PUBLIC_SUPABASE_PUBLISHABLE_KEY=`
- `ANTHROPIC_API_KEY=`
- `OPENAI_API_KEY=`
- `OPENROUTER_API_KEY=`
- `XERO_CLIENT_ID=`
- `XERO_CLIENT_SECRET=`
- `SENTRY_DSN=`
- `METRICS_TOKEN=`
- `CORS_ORIGINS=` (prod override)
- `FRONTEND_URL=`
- `XERO_REDIRECT_URI=`

### Backend Config Architecture

Three files replace the current monolithic `config.py`:

**`backend/shared/infrastructure/env.py`** - Env dataclass hierarchy:

```python
from dataclasses import dataclass, fields
import os
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class Env:
    """Base env vars shared across all environments. Reads from .env"""
    # Values here are properties that read os.environ on every access
    # so .env.local changes propagate without restart in dev.
    ...

@dataclass  
class DevelopmentEnv(Env):
    """Loads .env.development overrides on top of .env"""
    ...

@dataclass
class ProductionEnv(Env):
    """Loads .env.production overrides on top of .env"""
    ...
```

**`backend/shared/infrastructure/config.py`** - Config singleton:

```python
class Config:
    """Singleton that delegates to the correct Env subclass.
    
    In development: attribute access reads os.environ LIVE
    (so editing .env.local or .env.development and saving
    immediately takes effect - no server restart needed).
    
    In production: values are read once and cached for performance.
    """
    _instance: ClassVar[Config | None] = None
    
    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    @property
    def DATABASE_URL(self) -> str:
        return self._get("DATABASE_URL", self._defaults["DATABASE_URL"])
    # ... one property per var
    
config = Config()
```

### Hot-Reload Strategy (no watchdog)

The key insight: **don't cache values in development**. Each `config.FOO` property access does `os.environ.get("FOO", default)` live. In production, values are cached at startup.

For .env file changes to propagate to `os.environ` without restart, we re-run `load_dotenv(override=True)` on a short interval. Two options:

**Option A - Lazy reload on access (recommended, zero dependencies):** Each property access checks `time.monotonic()` against a debounce window (e.g. 2 seconds). If enough time has passed, re-call `load_dotenv(override=True)` on all three .env files before reading `os.environ`. This means the first access after an env file edit (with >= 2s gap) picks up the change. In production, this check is skipped entirely - values are read once.

**Option B - Background thread with `os.stat` polling:** A daemon thread polls .env file mtimes every 2-3 seconds. If changed, re-runs `load_dotenv(override=True)`. Slightly more proactive but adds a thread.

Option A is simpler and has zero overhead in production. Recommend Option A.

### Migration: Backward Compatibility

The current import pattern (`from shared.infrastructure.config import DATABASE_URL`) is used in ~30 files. Two strategies:

**Phase 1 (this refactor):** Keep `config.py` exporting the same module-level names as proxies to the singleton, so existing imports don't break:

```python
# config.py - backward compat shim
config = Config()

# Module-level aliases (existing imports keep working)
DATABASE_URL = config.DATABASE_URL  # Note: this captures the value at import time
```

However, this defeats hot-reload for module-level imports. For hot-reload to work, callers must use `config.DATABASE_URL` at call-site rather than a captured module-level name.

**Phase 2 (follow-up):** Migrate all import sites from:
```python
from shared.infrastructure.config import DATABASE_URL
# use DATABASE_URL
```
to:
```python
from shared.infrastructure.config import config
# use config.DATABASE_URL
```

This is a mechanical find-and-replace across ~30 files. It should be done in this refactor since the whole point is live access.

### Frontend Changes

Vite already has built-in `.env` file layering (`.env`, `.env.local`, `.env.development`, `.env.production`). We just need to create the files:

- `frontend/.env` - committed, shared: (empty or contains comments)
- `frontend/.env.development` - committed: `VITE_SUPABASE_URL=http://127.0.0.1:54321`
- `frontend/.env.production` - committed: (placeholder comments for Vercel-set vars)
- `frontend/.env.local` - gitignored: `VITE_SUPABASE_PUBLISHABLE_KEY=...`
- Delete current `frontend/.env` (its contents split into above files)

### .gitignore Updates

Add to [`.gitignore`](.gitignore):

```
# Allow committed env files
!backend/.env
!backend/.env.development
!backend/.env.production
!frontend/.env
!frontend/.env.development
!frontend/.env.production
# Keep secrets gitignored
backend/.env.local
frontend/.env.local
```

### Files Changed

- **New:** `backend/shared/infrastructure/env.py` (Env hierarchy + dotenv loading)
- **Rewrite:** `backend/shared/infrastructure/config.py` (Config singleton + backward compat)
- **Modify:** ~30 backend files (change imports to use `config.X` instead of bare names)
- **New:** `backend/.env`, `backend/.env.development`, `backend/.env.production`, `backend/.env.local`
- **New:** `frontend/.env.development`, `frontend/.env.production`, `frontend/.env.local`
- **Modify:** `frontend/.env` (move secrets to `.env.local`, dev values to `.env.development`)
- **Modify:** `.gitignore` (update env file rules)
- **Modify:** `docker-compose.yml` (no change needed - it injects env vars directly)
- **Modify:** `backend/.env.example` (update docs to reflect new structure)
- **Modify:** `frontend/.env.example` (update docs)
- **Modify:** scattered `os.environ.get` in 6 files (consolidate into Config)
- **New:** `docs/environment.md` (architecture docs for the env system)

### Documentation: `docs/environment.md`

A new [`docs/environment.md`](docs/environment.md) file documenting the full environment architecture. Contents:

- **File hierarchy** - which `.env` files exist, what goes in each, which are committed vs gitignored
- **Load order and precedence** - `.env` -> `.env.{environment}` -> `.env.local` -> process env vars (platform-injected)
- **Inheritance diagram** - Mermaid diagram showing `Env` -> `DevelopmentEnv` / `ProductionEnv` -> `Config` singleton
- **Hot-reload behavior** - how dev mode re-reads `.env` files on access, why production caches values
- **Usage guide** - how to access config in backend code (`from shared.infrastructure.config import config; config.DATABASE_URL`)
- **Variable reference table** - every variable, which file it belongs in, whether it's sensitive, its default value
- **Adding a new variable** - step-by-step checklist (add to correct `.env` file, add property to `Env`/subclass, add to `.env.example`)
- **Production deployment** - how platform env vars override everything, which vars are required
- **Frontend env vars** - how Vite's built-in layering works, which `VITE_*` vars exist
- **Troubleshooting** - common issues (value not updating, wrong env loaded, secret accidentally committed)

### Impact on Docker / CI / Deploy

- **Docker/production:** No behavior change. Production injects env vars via the platform (DigitalOcean App Platform, Vercel). The `.env.production` file only has non-sensitive defaults; secrets come from platform env vars which override everything.
- **CI:** `ci.yml` sets `ENV=test` + `DATABASE_URL` + `JWT_SECRET` explicitly - these override any .env file. No change needed.
- **docker-compose.yml:** Already injects all vars via `environment:` block. No change needed.
- **pixi.toml:** Already sets `DATABASE_URL` and `PYTHONPATH` in task env. No change needed.

### Risks

- The `decode_token()` function in config.py contains non-trivial logic (JWKS client, ES256 vs HS256 branching). This stays in config.py as a method on Config.
- `_enforce_cors()` runs at import time and crashes the process in production. This moves to Config._init() to preserve the fail-fast behavior.
- `cli.py` has its own .env loader (manual parse, no python-dotenv). Should be updated to use the new Config, but cli.py is a standalone tool - lower priority.
