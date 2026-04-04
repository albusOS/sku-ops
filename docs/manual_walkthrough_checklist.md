# Manual Walkthrough Checklist

**Purpose:** Walk through every user activity, user story, workflow, report, and logic as a human user. No automated tests — define examples, expected outcomes, edge cases, then manually execute.

**Reference:** [Day in the Life User Story](./day_in_life_user_story.md)

---

## Prerequisites

### 1. Start the Live App

```bash
pixi run db     # start dev Postgres (first time)
pixi run dev      # starts backend + frontend
```

- **Backend:** http://localhost:8000  
- **Frontend:** http://localhost:3000  

### 2. Provision Data

```bash
pixi run provision -- --dev                # org + departments + dev users
pixi run import -- --vendors --products   # vendors + products from Hike POS
```

### 3. Log In

| Role | Email | Password |
|------|-------|----------|
| Admin | dev@supply-yard.local | dev123 |
| Contractor | contractor@supply-yard.local | dev123 |

---

## Act 1: Morning — Admin Sets Up the Yard

### Scene 1: Login

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Open http://localhost:3000 | Login page loads |
| 2 | Enter `dev@supply-yard.local` / `dev123` | POST /api/auth/login succeeds |
| 3 | Click Login | JWT stored, redirect to `/` (Dashboard) |
| 4 | Check sessionStorage | Token present |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Wrong password | `dev1234` | Error toast, stay on login |
| Wrong email | `admin@wrong.local` | Error toast |
| Empty fields | Submit without input | Validation error or error toast |
| Contractor login | `contractor@supply-yard.local` / `dev123` | Dashboard, different nav (no Financials, Invoices, etc.) |

---

### Scene 2: Dashboard

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Logged in as Admin | `GET /api/dashboard/stats` |
| 2 | View page | Stats render: total products, low stock count, recent transactions, revenue |
| 3 | Check time filter | If present, changing filter updates data |

**Expected data shape:** `stats` with `total_products`, `low_stock_count`, `recent_transactions`, `revenue`, etc.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Empty state | Fresh seed, no products | Zero counts, no recent transactions |
| Contractor view | Log in as contractor | Contractor-specific widgets (withdrawals, unpaid balance) |

---

### Scene 3: Upload Vendor Invoice/Receipt

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Navigate to `/import` | Receive Inventory page loads |
| 2 | Upload a PDF (e.g. vendor receipt) | `POST /api/documents/parse?use_ai=true` |
| 3 | AI extracts | Vendor name, line items (name, qty, unit, etc.) |
| 4 | Review parsed table | Editable rows; can correct quantity, assign department |
| 5 | Click "Save as Purchase Order" | `POST /api/purchase-orders` → PO created, status `ordered` |

**Example:** PDF from "Johnson Lumber Co" with 2x4x8 Studs 200, 1/2" PEX 100ft 50.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| No AI / OCR fallback | `use_ai=false` or parse fails | Fallback behavior or error |
| Invalid file type | Upload .txt or .doc | Reject with error toast |
| Empty extraction | PDF with no tables | Handle gracefully, show message |
| Duplicate vendor | Vendor already exists | Match or create; no duplicates |
| Partial save | Some rows deselected | Only selected rows in PO |

**Gap (from user story):** Silent failures in parse → PO → receive can make items vanish. Trace full flow.

---

### Scene 4: Delivery Arrives

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/purchase-orders` | List of POs |
| 2 | Expand PO from Scene 3 | Items with status `ordered` |
| 3 | Select items arrived, click "Mark at Dock" | `POST /api/purchase-orders/{id}/delivery` |
| 4 | Items move | `ordered` → `pending` |
| 5 | Enter received quantities | Verify counts |
| 6 | Click "Receive" | `POST /api/purchase-orders/{id}/receive` |
| 7 | For each item | Product matched/created, stock incremented, stock transaction recorded |
| 8 | Go to `/inventory` | Products visible with correct quantities |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Receive more than ordered | Enter 250 when ordered 200 | Allowed or validation error |
| Receive 0 | Enter 0 | Skip or error |
| Partial receive | Some items received, some not | Partial status, remaining `pending` |
| New product | No match in catalog | Product created with SKU |

---

### Scene 5: Check Inventory

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/inventory` | `GET /api/products` with pagination |
| 2 | Search by name/SKU | Filtered results |
| 3 | Filter by department | Department filter applied |
| 4 | Filter "low stock only" | Only products below min_stock |
| 5 | Edit product | Open modal, change price, min_stock |
| 6 | Save | PUT /api/products/{id}, UI updates |

**Expected:** Table with SKU, name, department, quantity, price, min_stock, low-stock indicator.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Pagination | > 20–50 products | Next/Prev works |
| Delete product | Delete from detail | Product removed, inventory updated |
| Zero stock | Product at 0 | Shown, low-stock if min_stock > 0 |

---

## Act 2: Midday — Contractors Pick Up Materials

### Scene 6: Contractor Logs In

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Log out, log in as `contractor@supply-yard.local` / `dev123` | Contractor dashboard |
| 2 | Check nav | Request Materials, My History (no POS, Financials, Invoices) |

---

### Scene 7a: Contractor Requests Materials (Async)

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/request-materials` | Product catalog, search, departments |
| 2 | Search "lumber" or filter by Lumber | Products listed |
| 3 | Add items to cart | Cart shows qty, price, subtotal |
| 4 | Try to add more than stock | "Not enough stock" toast |
| 5 | Enter job ID, service address, notes | Form filled |
| 6 | Submit | `POST /api/material-requests` → status `pending` |
| 7 | Go to `/my-history` | Request appears as Pending |

**Example:** Job ID `JOB-001`, Address `123 Main St`, 5x 2x4x8 Studs.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Empty cart | Submit with no items | Validation error |
| Barcode scan | Enter barcode in input | Product found, added to cart |
| Max quantity | Add up to product.quantity | Allowed; +1 blocked with toast |
| No job ID / address | Omit (if optional) | Request created; Admin must fill in Pending Requests |

---

### Scene 7b: Admin Processes Request

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Log in as Admin | Full nav |
| 2 | Go to `/pending-requests` | Pending requests from Scene 7a |
| 3 | Click "Process" on a request | Modal opens |
| 4 | Enter Job ID, Service Address (required) | Form validation |
| 5 | Submit | `POST /api/material-requests/{id}/process` |
| 6 | Backend | Withdrawal created, stock decremented, draft invoice (if applicable) |
| 7 | Request disappears from pending | Status changed |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Job ID empty | Submit without Job ID | "Job ID is required" toast |
| Service address empty | Submit without address | "Service address is required" toast |
| Insufficient stock | Process when stock < requested | 400 or graceful error |
| Urgent styling | Request > 48h old | Red border (if implemented) |

**Gap (from user story):** Admin re-enters job_id/service_address even if contractor provided them. Verify pre-fill from request.

---

### Scene 8: Walk-Up POS (Synchronous)

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Admin: Go to `/pos` | Material Terminal |
| 2 | Select contractor from dropdown | Contractors loaded from `/api/contractors` |
| 3 | Search product, add to cart | Search by name or SKU |
| 4 | Enter job ID, service address | Optional or required |
| 5 | Click "Charge to Account" | `POST /api/withdrawals/for-contractor` |
| 6 | Backend | Stock decremented, withdrawal recorded, draft invoice |
| 7 | Receipt/confirmation shown | Success state |

**Example:** Contractor "Demo Co", 10x 2x4x8 Studs, Job JOB-002, 456 Oak Ave.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| No contractor selected | Submit without contractor | Validation error |
| Insufficient stock | 100 when only 50 available | 400, "Not enough stock" |
| Barcode scan | Scan product | Adds to cart |
| Empty cart | Submit with no items | Validation error |

---

### Scene 9: Contractor Self-Checkout (if permitted)

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Contractor: Go to `/pos` | If permitted, contractor sees POS |
| 2 | Contractor auto-selected | `selectedContractor` = current user |
| 3 | Add items, submit | `POST /api/withdrawals` |
| 4 | Charged to account | Withdrawal created, invoiced later |

**Check:** Is POS visible to contractor in `App.jsx`? Current routes show POS under admin role only.

---

## Act 3: Afternoon — Admin Handles Billing

### Scene 10: Review Financials

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/financials` | `GET /api/financials/summary`, `GET /api/withdrawals` |
| 2 | View summary | Revenue, costs, margins, outstanding |
| 3 | Filter by status | Unpaid, Invoiced, Paid |
| 4 | Filter by entity | Billing entity dropdown |
| 5 | Filter by date range | Start/end date |
| 6 | Mark Paid (single) | `PUT /api/withdrawals/{id}/mark-paid` |
| 7 | Bulk Mark Paid | Select multiple, `PUT /api/withdrawals/bulk-mark-paid` |
| 8 | Export CSV | Download financials export |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| No unpaid | All paid | Empty or zero outstanding |
| Date range | Future dates | No results or error |

---

### Scene 11: Invoicing

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/invoices` | List of invoices |
| 2 | Open Create Invoice | Modal from Financials or Invoices |
| 3 | Select unpaid withdrawals | Multi-select |
| 4 | Create | `POST /api/invoices` |
| 5 | Invoice created | Draft, line items from withdrawals |
| 6 | Sync to Xero | `POST /api/invoices/{id}/sync-xero` |
| 7 | Bulk sync | Select invoices, bulk sync |

**Expected:** Invoice shows line items, tax, totals. Withdrawals linked.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| No unpaid | Create invoice with no selection | Validation |
| Already invoiced | Select same withdrawal twice | Prevent or error |
| Xero not connected | Sync | Stub message or OAuth flow |

**Gap (from user story):** `payment_status` "invoiced" should be set when withdrawal added to invoice. Verify.

---

### Scene 12: Xero Integration

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | If Xero connected | OAuth flow, tenant selection |
| 2 | Sync invoice | Invoice sent to Xero |
| 3 | Verify | Correct account codes, tracking categories |

**Note:** Xero may be stub. Document actual behavior.

---

## Act 4: End of Day — Reports and AI

### Scene 13: Reports

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/reports` | Reports page |
| 2 | Sales report | Withdrawals by period, contractor, job |
| 3 | Inventory report | Stock levels, value, low stock |
| 4 | Revenue trends | Time series chart |
| 5 | Product margins | Cost vs revenue per product |
| 6 | Job P&L | Profitability per job/address |
| 7 | KPIs | Turns, margin %, fill rate |
| 8 | Date presets | Last 7d, 30d, etc. |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| No data | Fresh org | Empty charts, zero values |
| Date range | Custom range | Data filtered correctly |

---

### Scene 14: AI Assistant

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Open chat (bottom-right) | Chat panel |
| 2 | Ask "What's our inventory health?" | Inventory stats, low stock, reorder suggestions |
| 3 | Ask "Show me P&L for this month" | Financial summary |
| 4 | Ask "What did contractor X pull this week?" | Withdrawal history |
| 5 | Ask "Which products are slow movers?" | Slow mover analysis |

**Agent routing:** Chat uses path-based agent (inventory, ops, finance) for context.

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Empty org | No products | Graceful response |
| Vague query | "stuff" | Clarification or broad answer |
| Multi-domain | "inventory and finance" | Parallel tool calls if supported |

---

### Scene 15: Product Performance

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/product-performance` | Deep product analysis |
| 2 | View table | Velocity, margin, trend per product |
| 3 | Sort columns | Sortable |
| 4 | Date range | Filter applied |
| 5 | Download | Export if available |

---

## Act 5: Periodic — Stock Corrections

### Scene 16: Stock Adjustment

| Step | Action | Expected Outcome |
|------|--------|-------------------|
| 1 | Go to `/inventory` | Product list |
| 2 | Open product detail | Click row or "View" |
| 3 | Click "Adjust Stock" | `AdjustStockDialog` opens |
| 4 | Enter delta (+ or -) and reason | e.g. +5, "Cycle count" |
| 5 | Submit | `POST /api/stock/{product_id}/adjust` |
| 6 | Stock transaction | Type `ADJUSTMENT` recorded |
| 7 | Product quantity updated | UI reflects new qty |

**Edge cases:**

| Case | Action | Expected |
|------|--------|----------|
| Negative result | Delta -100 when stock 50 | Error: cannot go negative |
| Zero delta | Delta 0 | Reject or no-op |
| No reason | Submit without reason | Validation if required |

---

## Additional Flows to Verify

### Vendors

| Step | Action | Expected |
|------|--------|----------|
| 1 | Go to `/vendors` | Vendor list |
| 2 | Create vendor | Form, POST |
| 3 | Edit vendor | PUT |
| 4 | Vendor from import | Auto-created if "Create vendor if missing" |

### Departments

| Step | Action | Expected |
|------|--------|----------|
| 1 | Go to `/departments` | 8 standard + custom |
| 2 | Create department | Code, name |
| 3 | Product count | Updates when products assigned |

### Contractors

| Step | Action | Expected |
|------|--------|----------|
| 1 | Admin: `/contractors` | Contractor list |
| 2 | Create contractor | User with role contractor |
| 3 | Deactivate | is_active = false |

### CSV Import (Receipt Import)

| Step | Action | Expected |
|------|--------|----------|
| 1 | `/import` → CSV tab | Upload CSV |
| 2 | Parse | Products extracted |
| 3 | Map departments | Assign, import |

### Purchase Orders from Receipt Import

| Step | Action | Expected |
|------|--------|----------|
| 1 | After parse, "Save as PO" | PO created |
| 2 | Go to POs | New PO in list |
| 3 | Receive flow | Same as Scene 4 |

---

## Known Limitations

| # | Area | Note |
|---|------|------|
| 1 | Contractor POS | POS is admin-only; contractor self-checkout is not exposed |
| 2 | Document parse → PO → receive | Trace full flow, watch for silent extraction failures |
| 3 | Material request processing | Verify job ID/address pre-fills from contractor input |

---

## Provisioning Commands

```bash
pixi run provision -- --dev                # org + departments + dev users
pixi run import -- --vendors --products  # real Hike POS data
```
