# SKU-Ops

Material management for supply yards — contractors, warehouses, and inventory.

## Quick Start

```bash
npm install                           # root monorepo deps (concurrently)
cd backend && uv sync --dev && cd ..  # Python deps via uv
cd frontend && npm install && cd ..   # frontend deps
cp backend/.env.example backend/.env  # edit with your keys
npm run dev                           # starts backend + frontend
```

- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:3000

## Dev Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | dev@supply-yard.local | dev123 |
| Contractor | contractor@supply-yard.local | dev123 |

Dev users and demo data load from `supabase/seeds/` on database reset:

```bash
./bin/dev db:reset               # migrations + seeds (org, departments, demo, dev users above)
./bin/dev import --vendors       # optional: Hike POS vendors
./bin/dev import --products      # optional: Hike POS products
```

## Features

- **Contractors:** Request materials (search, barcode, cart) -> staff processes at pickup
- **Admin:** Material Terminal (POS), Pending Requests, Inventory, Financials, Invoices
- **Document Import:** AI-powered receipt/invoice parsing (Claude) with OCR fallback
- **Purchase Orders:** Review -> receive -> stock update workflow
- **AI Assistant:** Multi-agent chat with streaming via WebSocket (inventory, finance, operations)
- **Dashboard:** Revenue, margins, low stock, department P&L, daily charts (with time filters)
- **Reports:** P&L, inventory valuation, operations metrics, trend analysis
- **Invoicing:** Unpaid -> Invoiced -> Paid flows; Xero sync
- **Real-time:** WebSocket event broadcasting — UI updates automatically when data changes
- **Org-scoped:** Data isolation via organization_id

## Tech Stack

- **Backend:** Python 3.13, FastAPI, uv (package manager), PostgreSQL
- **Frontend:** React 18, Vite, Tailwind CSS, Radix UI, TanStack Query, ECharts
- **AI:** Anthropic Claude (documents, UOM, assistant), OpenAI (embeddings), OpenRouter (agent gateway)
- **Infra:** Redis (event pub/sub, chat sessions, distributed locks), Prometheus metrics, Sentry error tracking
- **Quality:** Ruff (Python lint + format), ESLint 9 + Prettier (frontend), commitizen (conventional commits), CI on every push
- **Deploy:** Railway (backend), Vercel (frontend), Supabase (auth + DB)

## Dev Commands

All commands run from the project root:

```bash
npm run dev              # start backend + frontend (concurrently)
./bin/dev test [args]    # run pytest
./bin/dev lint           # lint backend (ruff)
./bin/dev fmt            # format backend (ruff)
./bin/dev lint:fe        # lint frontend (ESLint)
./bin/dev fmt:fe         # format frontend (Prettier)
./bin/dev commit         # commitizen conventional commit
./bin/dev server         # start backend only
./bin/dev ui             # start frontend only
./bin/dev container      # start devcontainer
```

## Environment

Configuration is environment-aware (`ENV=development|test|production`). See `backend/.env.example` for all available settings.

| | Development | Test | Production |
|---|---|---|---|
| JWT_SECRET | default | default | required |
| CORS | permissive (*) | permissive (*) | required |
| Provisioning | `supabase/seeds/` + `./bin/dev db:reset` | `pytest_minimal.sql` + UOM SQL | Supabase SQL seeds |
| Database | Postgres (Docker) | Postgres | Postgres |
| Redis | optional | required | required |
| WORKERS | 1 | 1+ (with Redis) | 2+ (with Redis) |

## Architecture

```
backend/
├── server.py         # App composition root (middleware, exception handlers)
├── routes.py         # Router aggregation — all context routers wired here
├── startup.py        # Lifespan: init, warm-up, seeding, shutdown
├── scheduler.py      # Background jobs (Xero nightly sync)
├── identity/         # Auth, users, organizations
├── catalog/          # Products, departments, vendors, SKUs
├── inventory/        # Stock transactions, cycle counts, UOM
├── documents/        # Document parsing (OCR, AI), import logic
├── purchasing/       # Purchase orders, receiving
├── operations/       # Withdrawals, material requests, returns
├── finance/          # Invoicing, Xero integration, ledger
├── assistant/        # AI chat agents, LLM infrastructure
├── reports/          # Dashboard analytics, P&L, trends
├── jobs/             # Job definitions
├── shared/           # Config, DB, logging, metrics, middleware, health, WebSocket
├── devtools/         # Import scripts, evals (excluded from Docker)
└── kernel/           # Shared types, errors

frontend/
├── src/
│   ├── components/   # UI components (shadcn/ui, charts, reports)
│   ├── pages/        # Route pages (finance, inventory, operations)
│   ├── hooks/        # Data hooks, useRealtimeSync, useChatSocket
│   ├── context/      # AuthContext
│   └── lib/          # API client, query client, constants
```

Each backend context owns its domain, infrastructure, and API layers. Cross-context access goes through application-layer facades, never direct infrastructure imports.

## Real-time Architecture

```
Backend domain event -> event_hub.emit() -> Redis pub/sub (multi-worker)
                                         -> asyncio queues (single-worker fallback)
                                         -> WebSocket /api/ws
                                         -> WebSocket /api/ws/chat (AI streaming)

Frontend: useRealtimeSync() -> invalidates TanStack Query cache -> UI re-renders
          useChatSocket()   -> streams AI responses (delta, tool_start, done)
```

Events are org-scoped and role-filtered. Contractors only receive events relevant to their role. With `REDIS_URL` set, events propagate across all workers via Redis Pub/Sub. Chat sessions are stored in Redis hashes with TTL expiry. The Xero sync lock uses a distributed Redis key.

## Docker

```bash
cp .env.production.example .env   # set JWT_SECRET, CORS_ORIGINS, REDIS_URL, etc.
docker compose up -d
```

The stack includes PostgreSQL, Redis, the backend (FastAPI + uvicorn), Nginx (reverse proxy + static frontend), and Certbot (TLS). The backend runs behind Nginx with the frontend served as static files from `frontend/dist`.

See [Deployment Guide](docs/deployment.md) for full VPS and managed-platform deployment guides, and [Launch Checklist](docs/launch-checklist.md) for the production readiness checklist.
