# Demo Script: Admin + Contractor

Use this to demo the core flows. No seeding required—just start the app.

---

## Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@demo.local | demo123 |
| Contractor | contractor@demo.local | demo123 |

---

## 1. Contractor Flow

| Step | Action | What to show |
|------|--------|--------------|
| 1 | Start app: `npm run dev` | Backend on :8000, frontend on :3000 |
| 2 | Login as **contractor@demo.local** / demo123 | Contractor nav: Dashboard, Request Materials, My History |
| 3 | **Request Materials** | Search, scan barcode, add to cart → Submit Request (job ID, address optional) |
| 4 | **My History** | Request appears as **Pending**; after staff processes → Withdrawal shows as **Unpaid** |

---

## 2. Admin Flow

| Step | Action | What to show |
|------|--------|--------------|
| 1 | Login as **admin@demo.local** / demo123 | Full nav: Material Terminal, Pending Requests, Financials, Invoices, etc. |
| 2 | **Dashboard** | Revenue, unpaid total, low stock, Recent Transactions (time filter, itemized) |
| 3 | **Pending Requests** | Process contractor requests → enter Job ID + Service Address → creates withdrawal |
| 4 | **Material Terminal (POS)** | Direct checkout (admin/WM only) |
| 5 | **Financials** | Unpaid withdrawals grouped by billing entity |
| 6 | **Invoices** | Invoice list; link from Invoiced withdrawals |

---

## 3. End-to-End Flow

| Step | User | Action |
|------|------|--------|
| 1 | **contractor@demo.local** | Request Materials → add items → Submit Request |
| 2 | **admin@demo.local** | Pending Requests → Process → enter Job ID + Service Address → Create Withdrawal |
| 3 | Admin | Go to **Financials** → see new unpaid withdrawal |
| 4 | Admin | Select it → **Create Invoice** |
| 5 | Admin | Go to **Invoices** → open invoice → change status to **Paid** → Save |
| 6 | **contractor@demo.local** | Go to **My History** → same withdrawal shows **Paid** |

---

## Suggested Demo Order (~5 min)

1. **Contractor** – Request Materials, My History states (~2 min)
2. **Admin** – Pending Requests → Process → Financials → Create Invoice → Invoices → Mark Paid (~2 min)
3. **Contractor again** – Show withdrawal moved to Paid (~1 min)
