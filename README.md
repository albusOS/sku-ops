# SKU-Ops

Material management for supply yards — contractors, warehouses, and inventory.

## Quick Start

```bash
npm install
cp backend/.env.example backend/.env   # edit with your keys
npm run dev
```

- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:3000

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.local | demo123 |
| Contractor | contractor@demo.local | demo123 |

Demo users are auto-created in development. See [docs/MULTI_TENANT_DEMO_SCRIPT.md](docs/MULTI_TENANT_DEMO_SCRIPT.md) for a full walkthrough.

## Features

- **Contractors:** Request materials (search, barcode, cart) → staff processes at pickup
- **Admin / Warehouse:** Material Terminal (POS), Pending Requests, Inventory, Financials, Invoices
- **Document Import:** AI-powered receipt/invoice parsing (Claude) with OCR fallback
- **Purchase Orders:** Review → receive → stock update workflow
- **AI Assistant:** Multi-agent chat for inventory, finance, and operations queries
- **Dashboard:** Revenue, low stock, recent transactions (with time filters)
- **Invoicing:** Unpaid → Invoiced → Paid flows; Xero sync
- **Multi-tenant:** Org-scoped data isolation

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLite (dev) / PostgreSQL (prod)
- **Frontend:** React, Vite, Tailwind, Tremor
- **AI:** Anthropic Claude (documents, UOM, assistant), OpenAI (embeddings), OpenRouter (agent gateway)
- **Deploy:** Docker, Nginx, docker-compose

## Environment

Configuration is environment-aware (`ENV=development|staging|production|test`). See `backend/.env.example` for all available settings. Key behaviors:

| | Development | Staging | Production |
|---|---|---|---|
| JWT_SECRET | default | required | required |
| CORS | permissive (*) | required | required |
| Demo seed | auto | opt-in | disabled |
| Database | SQLite file | Postgres | Postgres |

## Architecture

```
backend/
├── api/              # Top-level router aggregation
├── identity/         # Auth, users, organizations
├── catalog/          # Products, departments, vendors, SKUs
├── inventory/        # Stock transactions, UOM classification
├── documents/        # Document parsing (OCR, AI), import logic
├── purchasing/       # Purchase orders, receiving
├── operations/       # Withdrawals, material requests
├── finance/          # Invoicing, payments (Stripe), Xero
├── assistant/        # AI chat agents, LLM infrastructure
├── reports/          # Dashboard analytics
├── scripts/          # Seed data, backfills, dev tools
└── shared/           # Config, DB, logging, metrics, middleware
```

Cross-domain dependencies use **dependency injection** — application/domain layers define what they need as callable type hints; API routes wire concrete implementations. No circular imports.

## Docker

```bash
cp backend/.env.example .env   # set JWT_SECRET, CORS_ORIGINS, etc.
docker compose up -d
```

The backend runs behind Nginx with the frontend served as static files from `frontend/dist`.
