# SKU-Ops

Material management for supply yards—contractors, warehouses, and inventory.

## Quick Start

```bash
npm install
npm run dev
```

- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:3000

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.local | demo123 |
| Contractor | contractor@demo.local | demo123 |

Demo users are created on startup. See [docs/MULTI_TENANT_DEMO_SCRIPT.md](docs/MULTI_TENANT_DEMO_SCRIPT.md) for a full demo flow.

## Features

- **Contractors:** Request materials (search, barcode, cart) → staff processes at pickup
- **Admin / Warehouse:** Material Terminal (POS), Pending Requests, Inventory, Financials, Invoices
- **Dashboard:** Revenue, low stock, recent transactions (with time filters)
- **Invoicing:** Unpaid → Invoiced → Paid flows; Xero sync

## Tech Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** React, Vite, Tailwind, Tremor
