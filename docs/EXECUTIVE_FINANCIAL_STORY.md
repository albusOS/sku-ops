# Executive Financial Quality Story

**Persona:** Sarah Chen, Director of Operations — runs a 50-SKU supply yard with 12 active contractors across 3 billing entities. Reports to the owner. Her job is to know where every dollar goes.

---

## The Day: Tuesday, 10 AM — Month-End Close

Sarah logs in. She needs to present the owner with a clear picture of:
- How much we made this month
- How much we spent
- What our margins look like by job, by department, by contractor
- Which outstanding bills need chasing
- Whether the numbers in our system match what Xero will show

---

## Story Scenes & Success Criteria

### Scene 1: The Dashboard Tells the Truth

Sarah opens `/financials`. The summary loads with full P&L data.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 1.1 | **Gross revenue** shows sum of all withdrawal subtotals (before tax) | `GET /api/financials/summary` → `gross_revenue` matches manual sum of withdrawal subtotals |
| 1.2 | **Returns** are broken out and subtracted | `returns_total` > 0 if any returns exist; `net_revenue = gross_revenue - returns_total` |
| 1.3 | **COGS** uses the cost recorded at time of sale | `total_cost` reflects withdrawal-time cost, not current catalog cost |
| 1.4 | **Gross profit** = net revenue - COGS | `gross_profit = net_revenue - total_cost` exactly |
| 1.5 | **Gross margin %** is accurate | `gross_margin_pct = gross_profit / net_revenue × 100` |
| 1.6 | **Tax collected** is shown separately | `tax_collected` field present and equals sum of withdrawal taxes minus return taxes |
| 1.7 | **Outstanding receivables** are clear | `total_unpaid`, `total_invoiced`, `total_paid` break down by status |
| 1.8 | **Credit notes** total is shown | `total_credits` reflects all credit notes issued |
| 1.9 | **Department P&L** breakdown is present | `by_department` has entries for each dept with revenue, cost, profit, margin_pct |
| 1.10 | **Entity breakdown** shows per-entity outstanding and credits | `by_billing_entity` entries include `credits` field |

### Scene 2: Invoices Match What Goes to Xero

Sarah goes to `/invoices`. Creates an invoice from 3 unpaid withdrawals for "Smith Builders".

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 2.1 | **Invoice line items have correct prices** | Each `invoice_line_item.unit_price > 0` (not zero) — the `unit_price` vs `price` bug is fixed |
| 2.2 | **Invoice subtotal matches sum of line items** | `subtotal = Σ(qty × unit_price)` for all line items |
| 2.3 | **Tax from withdrawals carries through** | `invoice.tax = Σ(withdrawal.tax)` for linked withdrawals |
| 2.4 | **Invoice total = subtotal + tax** | Arithmetic check |
| 2.5 | **Line items carry cost** | Each `invoice_line_item.cost > 0` for items with catalog cost |
| 2.6 | **Line item margin computable** | `margin = amount - (cost × quantity)` per line; verifiable in GET response |
| 2.7 | **Invoice number is sequential** | Invoice numbers follow `INV-00001`, `INV-00002` pattern within the org |
| 2.8 | **Draft → Sent → Paid status flow works** | PUT to update status; paid cascades to linked withdrawals |
| 2.9 | **Linked withdrawals move to "invoiced"** | After POST /invoices, linked withdrawals have `payment_status = "invoiced"` |
| 2.10 | **Xero account codes are configurable** | `GET /api/settings` shows sales, COGS, inventory, AP account codes |

### Scene 3: A Contractor Returns Materials

Contractor pulls 50 bags of concrete but the job was cancelled. Admin processes a return.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 3.1 | **Return validates against original withdrawal** | `POST /api/returns` with more qty than originally withdrawn → 400 error |
| 3.2 | **Partial returns work** | Return 20 of 50 bags → accepted; remaining 30 still returnable |
| 3.3 | **No double-returns** | Return another 20, then try to return 20 more → rejected (only 10 left) |
| 3.4 | **Stock is restocked** | Product quantity increases by returned amount |
| 3.5 | **Stock transaction uses RETURN type** | `GET /api/stock/{id}/history` shows a `return` transaction with correct +delta |
| 3.6 | **Credit note auto-created** | If withdrawal had an invoice, credit note is generated with `CN-00001` numbering |
| 3.7 | **Credit note amount matches** | `credit_note.subtotal = return.subtotal`, tax and total follow |
| 3.8 | **Return reason is captured** | Return record includes `reason` (wrong_item, defective, overorder, job_cancelled, other) |
| 3.9 | **Return shows in P&L** | `/api/financials/summary` reflects reduced net_revenue after the return |
| 3.10 | **Job P&L reflects the return** | `/api/reports/job-pl` shows the return subtracted from that job's revenue |

### Scene 4: Purchase Order Cost Tracking

A new lumber delivery arrives. Some items are existing products at a different cost.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 4.1 | **New products get PO cost** | Products created from PO receive have `cost` from the PO item |
| 4.2 | **Matched products get weighted avg cost** | If product had cost $10 × 100 units, and PO delivers $12 × 50 units, new cost = ($10×100 + $12×50)/150 = $10.67 |
| 4.3 | **Cost flows to next withdrawal** | New withdrawal for that product uses updated cost in COGS |
| 4.4 | **PO cost_total tracks purchase spend** | `receive_po_items` response includes `cost_total` |
| 4.5 | **Xero PO journal posts Dr Inventory, Cr AP** | Xero adapter `sync_po_receipt` posts correct journal |

### Scene 5: Tax Rate Alignment with Xero

The org operates in NZ with 15% GST. Sarah updates the tax rate.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 5.1 | **Tax rate is configurable per org** | `org_settings.default_tax_rate` can be set via settings API |
| 5.2 | **New withdrawals use org tax rate** | Create withdrawal → `tax = subtotal × 0.15` (not hardcoded 8%) |
| 5.3 | **Returns use same tax rate** | Return tax calculation matches the org rate |
| 5.4 | **Existing withdrawals retain original tax** | Old withdrawals keep their original tax (no retroactive change) |
| 5.5 | **Xero tax type is configurable** | `xero_tax_type` (e.g. "OUTPUT2") is per-org and sent with invoice sync |

### Scene 6: Reports an Executive Trusts

Sarah reviews reports at month-end to present to the owner.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 6.1 | **Sales report shows gross, returns, net** | `/api/reports/sales` has `gross_revenue`, `returns_total`, `net_revenue` |
| 6.2 | **Product margins use historical cost** | Per-product COGS uses cost recorded at withdrawal time, not current catalog cost |
| 6.3 | **Job P&L nets returns** | Jobs with returns show lower revenue and profit; `return_count` visible |
| 6.4 | **Trends show profit over time** | `/api/reports/trends` includes `profit` per period (revenue - cost) |
| 6.5 | **Trends net returns per period** | Periods with returns show reduced revenue |
| 6.6 | **KPIs compute correctly** | Inventory turnover = COGS / inventory cost value; gross margin %; DIO |
| 6.7 | **CSV export includes cost and margin** | Downloaded CSV has Cost, Margin columns per transaction |
| 6.8 | **Department P&L in financial summary** | `by_department` section shows revenue, cost, profit, margin_pct per department |
| 6.9 | **Product performance includes margin** | `/api/reports/product-performance` shows per-product `cogs`, `gross_profit`, `margin_pct` |
| 6.10 | **Date filtering works everywhere** | All report endpoints accept `start_date`/`end_date` and return filtered data |

### Scene 7: Data Integrity Under Pressure

Sarah runs these checks because the numbers need to be defensible.

| # | Criterion | What to Verify |
|---|-----------|----------------|
| 7.1 | **Stock ledger is immutable** | Every stock change has a `stock_transactions` row with before/after quantities |
| 7.2 | **Withdrawal + return stock balances** | If product started at 200, withdrew 50, returned 20 → stock = 170 |
| 7.3 | **Invoice amounts match withdrawal totals** | Sum of invoice line items = sum of linked withdrawal subtotals |
| 7.4 | **Oversell prevention** | Withdrawal for qty > stock → 400 error, no stock change |
| 7.5 | **Over-return prevention** | Return for qty > withdrawn → 400 error, no stock change |
| 7.6 | **Multi-tenant isolation** | Org A cannot see org B's withdrawals, invoices, returns, or products |
| 7.7 | **Paid cascade works** | Mark invoice paid → all linked withdrawals become `paid` |
| 7.8 | **Invoice deletion unlinks** | Delete draft invoice → withdrawals revert to `unpaid` |

---

## Summary: What Makes This Trustworthy

1. **Accrual-accurate P&L** — Revenue is recognized at withdrawal, COGS at point-of-sale cost (not current cost), returns properly net out.

2. **Xero-ready** — Invoice line items carry the exact price and cost data Xero needs. COGS journals post correctly. Tax type and account codes are configurable per org.

3. **Returns close the loop** — The missing piece. Now material returns restock inventory, generate credit notes, and subtract from revenue/COGS in every report.

4. **Cost integrity** — Weighted average cost on PO receive keeps product costs current. Historical cost preserved on withdrawals means P&L doesn't shift retroactively.

5. **Department granularity** — The financial summary now breaks down by department, giving visibility into which product categories drive (or drain) margin.

6. **Tax alignment** — Configurable per-org tax rate means the local calculations match what Xero will compute, eliminating reconciliation gaps.

---

## How to Validate

Provision demo data and run through the scenes manually or via the backend e2e tests:

```bash
./bin/dev provision --dev
./bin/dev import --vendors --products
./bin/dev test:be backend/tests/e2e/
```

Each numbered criterion above is a pass/fail check. 46 total criteria across 7 scenes.
