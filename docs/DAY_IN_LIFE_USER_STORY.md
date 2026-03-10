# Day in the Life — End-to-End User Story

Complete walkthrough of all actors and flows in a real day at the Supply Yard. Use this as the north star for validation, testing, and gap analysis.

---

## Auth Seeding — Current State

The app seeds users on startup via `seed_mock_user()` in `scripts/seed.py`, triggered in `server.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@demo.local` | `demo123` |
| Contractor | `contractor@demo.local` | `demo123` |

Runs automatically when `DEMO_USER_EMAIL` is set (dev script sets via `ENV=development`). Standard departments are also seeded.

---

## Act 1: Morning — Admin Sets Up the Yard

### Scene 1: Login
Admin opens `localhost:3000`, logs in as `admin@demo.local` / `demo123`.
- `POST /api/auth/login` → JWT
- Frontend stores token in sessionStorage, redirects to `/` (Dashboard)

### Scene 2: Dashboard
Dashboard loads stats: total products, low stock count, recent transactions, revenue.
- `GET /api/dashboard/stats`
- Role-specific widgets render

### Scene 3: Upload a Vendor Invoice/Receipt
Admin navigates to `/import`. Uploads a PDF of a vendor receipt (e.g. lumber delivery from "Johnson Lumber Co").
1. `POST /api/documents/parse?use_ai=true` with the PDF
2. AI extracts: vendor name, line items (2x4x8 Studs qty 200, 1/2" PEX 100ft qty 50, etc.)
3. Frontend shows parsed items in editable table. Admin reviews, corrects quantities, assigns department
4. Admin clicks "Save as Purchase Order"
5. `POST /api/purchase-orders` → creates PO with status `ordered`, creates/matches vendor, enriches UOM via AI

### Scene 4: Delivery Arrives
Truck shows up. Admin goes to `/purchase-orders`, finds the PO.
1. Selects items that arrived, clicks "Mark at Dock" → `POST /api/purchase-orders/{id}/delivery`
2. Items move from `ordered` → `pending`
3. Admin counts and verifies quantities, clicks "Receive" → `POST /api/purchase-orders/{id}/receive`
4. For each item: product matched or created, stock incremented, stock transaction recorded
5. Products now visible in inventory with correct quantities

### Scene 5: Check Inventory
Admin goes to `/inventory`. Sees all products with current quantities.
- `GET /api/products` with pagination
- Can search, filter by department, filter "low stock only"
- Can edit prices, min_stock thresholds, etc.

---

## Act 2: Midday — Contractors Pick Up Materials

### Scene 6: Contractor Logs In
Contractor opens `localhost:3000`, logs in as `contractor@demo.local` / `demo123`.
- Sees contractor dashboard (own withdrawals, pending requests)

### Scene 7a: Contractor Requests Materials (Async flow)
Contractor navigates to `/request-materials`.
1. Browses products by department, adds items to cart
2. Enters job ID and service address, submits
3. `POST /api/material-requests` → status `pending`
4. Contractor can see request in `/my-history`

### Scene 7b: Admin Processes Request
Admin goes to `/pending-requests`.
1. Sees contractor's pending request with items
2. Reviews, enters job ID / service address if not set
3. Clicks "Process" → `POST /api/material-requests/{id}/process`
4. Backend: creates withdrawal (stock decremented), creates draft invoice, marks request processed

### Scene 8: Walk-Up POS (Synchronous flow)
Contractor walks into the yard. Admin goes to `/pos`.
1. Selects contractor from dropdown
2. Scans barcode or searches products, adds to cart with quantities
3. Enters job ID, service address
4. Clicks "Charge to Account" → `POST /api/withdrawals/for-contractor`
5. Backend: stock decremented atomically, withdrawal recorded, draft invoice created
6. Receipt shown

### Scene 9: Contractor Self-Checkout (if permitted)
Contractor on `/pos` can also self-checkout:
1. Adds items, submits → `POST /api/withdrawals`
2. Charged to account, invoiced later via Xero

---

## Act 3: Afternoon — Admin Handles Billing

### Scene 10: Review Financials
Admin goes to `/financials`.
- `GET /api/financials/summary` — revenue, costs, margins, outstanding
- `GET /api/withdrawals` — filterable by contractor, payment status, date range
- Can "Mark Paid" individual withdrawals or bulk-mark-paid

### Scene 11: Invoicing
Admin goes to `/invoices`.
1. Sees draft invoices (auto-created from withdrawals)
2. Can manually create invoices from selected unpaid withdrawals: `POST /api/invoices`
3. Can sync to Xero: `POST /api/invoices/{id}/sync-xero` or bulk sync
4. Invoice shows line items with materials, tax, totals

### Scene 12: Xero Integration
If Xero is connected (`/api/xero/connect` → OAuth flow → select tenant):
- Invoices sync as Xero invoices with correct account codes
- Tracking categories map to departments/jobs

---

## Act 4: End of Day — Reports and AI

### Scene 13: Reports
Admin goes to `/reports`.
- Sales report: withdrawals by period, contractor, job
- Inventory report: stock levels, value, low stock
- Revenue trends: time series
- Product margins: cost vs revenue per product
- Job P&L: profitability per service address/job
- KPIs: turns, margin %, fill rate

### Scene 14: AI Assistant
Anyone can open the chat (bottom-right).
- "What's our inventory health?" → inventory stats, low stock, reorder suggestions
- "Show me P&L for this month" → financial summary
- "What did contractor X pull this week?" → withdrawal history
- "Which products are slow movers?" → slow mover analysis
- Supports multi-domain queries that run parallel tool calls

### Scene 15: Product Performance
Admin goes to `/product-performance`.
- Deep analysis of individual products: velocity, margin, trend

---

## Act 5: Periodic — Stock Corrections

### Scene 16: Stock Adjustment
During a physical count, Admin finds discrepancy. Goes to product detail in `/inventory`.
1. Clicks "Adjust Stock"
2. `POST /api/stock/{product_id}/adjust` with delta and reason
3. Stock transaction recorded with `ADJUSTMENT` type

---

## Gaps and Risks

| # | Gap | Impact |
|---|-----|--------|
| 1 | Test failures: `withdrawal_getter not wired` | Invoice-creation-from-withdrawal flow untested |
| 2 | Contractor POS page | Role-based UX (self vs for-contractor) may have edge cases |
| 3 | Document parse → PO → receive | Multi-step flow; silent failures can make items vanish |
| 4 | Invoice auto-creation | Every withdrawal = 1 draft invoice; admin must consolidate manually |
| 5 | Material request process | Admin re-enters job_id/service_address even if contractor provided them |

---

## Next Steps

1. **Save this doc** ✓
2. **Chip away at blockers** — fix seeding, test wiring, propagate request data
3. **Prove reliability** — E2E tests, smoke tests for critical paths
4. **Prove security** — RBAC audit, org scoping, rate limits
5. **Delete debt** — remove unused features, consolidate scripts, prune docs
