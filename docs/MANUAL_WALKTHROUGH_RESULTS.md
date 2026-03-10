# Manual Walkthrough Results

**Date:** 2026-03-05  
**Method:** Live API calls via curl (backend at localhost:8000)  
**Reference:** [Manual Walkthrough Checklist](./MANUAL_WALKTHROUGH_CHECKLIST.md), [Day in the Life User Story](./DAY_IN_LIFE_USER_STORY.md)

---

## Summary

| Outcome | Count |
|---------|-------|
| Pass | 15 |
| Pass with caveats | 2 |
| Fail / Issue | 5 |
| Not tested (needs UI or file) | 4 |

---

## What Worked

### Auth & Dashboard
- **Login** — `POST /api/auth/login` returns JWT + user for admin and contractor
- **Wrong password** — Returns `{"detail": "Invalid credentials"}` as expected
- **Dashboard stats** — Returns revenue, products, low_stock_count, recent_withdrawals, low_stock_alerts

### Inventory
- **Products** — `GET /api/products` with pagination, search, department filter
- **Stock adjustment** — `POST /api/stock/{id}/adjust` with quantity_delta + reason works

### Material Requests (Async Flow)
- **Contractor creates request** — `POST /api/material-requests` with full item payload (product_id, sku, name, quantity, price, subtotal, unit)
- **Admin processes request** — `POST /api/material-requests/{id}/process` creates withdrawal, decrements stock, creates draft invoice

### POS / Withdrawals
- **Insufficient stock** — Returns 400: `"Insufficient stock for TOL-20VCOR-000001: requested 50, available 2"`
- **Correct API format** — `POST /api/withdrawals/for-contractor?contractor_id=<id>` with body (contractor_id must be **query param**, not in body)

### Financials & Reports
- **Financials summary** — Returns totals, by_billing_entity, by_contractor
- **Withdrawals** — List with filters
- **Invoices** — List
- **Reports** — Sales report returns data

---

## Issues Found

### 1. Material Request API: Incomplete Payload Rejected

**Scene 7a — Contractor Request Materials**

| Sent | Error |
|------|-------|
| `{ items: [{ product_id, quantity, price, subtotal }] }` | `Field required` for `items[0].sku` and `items[0].name` |

**Cause:** `WithdrawalItem` / `MaterialRequestCreate` requires `sku` and `name` in every item.

**Impact:** If the frontend ever sends a minimal payload (e.g. from a simplified flow), the request fails. The current `RequestMaterials.jsx` sends full cart items including sku/name, so it works in the UI. API-first or headless clients would need to include these fields.

**Recommendation:** Document the required fields clearly, or consider making sku/name optional and looked up from product_id on the backend.

---

### 2. "Invalid Token" When Using Shell Variables

**Scene 7b & 8 — Process Request, POS Withdrawal**

When passing the JWT via a shell variable (`$TOKEN`), some requests returned `401 Unauthorized` with `{"detail": "Invalid token"}`. The same token worked when passed inline via `$(jq -r '.token' /tmp/login.json)`.

**Cause:** Shell variable handling (e.g. newlines, truncation, or quoting) can corrupt the token when it’s long or contains special characters.

**Impact:** Scripts or tools that store the token in a variable and reuse it may see intermittent auth failures.

**Recommendation:** Use inline expansion or write the token to a temp file and read from it, rather than storing in a shell variable for multiple commands.

---

### 3. POS `for-contractor`: `contractor_id` Must Be Query Param

**Scene 8 — Walk-Up POS**

| Sent | Error |
|------|-------|
| `contractor_id` in JSON body | `Field required` for `contractor_id` (in query) |

**Cause:** The route is defined as:

```python
async def create_withdrawal_for_contractor(
    contractor_id: str,  # No Body() → query param
    data: MaterialWithdrawalCreate,
    ...
):
```

**Impact:** The frontend already uses `?contractor_id=${selectedContractor}` and works. Any client that puts `contractor_id` in the request body will get 401/400. This is an API contract quirk.

**Recommendation:** Document that `contractor_id` must be a query parameter for `POST /api/withdrawals/for-contractor`.

---

### 4. AI Assistant Route (Resolved)

**Scene 14 — AI Chat**

| Called | Result |
|--------|--------|
| `POST /api/assistant/chat` | `{"detail": "Not Found"}` |
| `POST /api/chat` | 200, returns response, agent, usage, etc. |

**Cause:** The correct route is `POST /api/chat`, not `/api/assistant/chat`.

**Impact:** Any client or docs using `/api/assistant/chat` would get 404. The frontend uses the correct path.

---

### 5. Document Parse: Tiny/Invalid Image

**Scene 3 — Receipt Import**

A minimal valid PNG (1x1) was sent with `use_ai=true`. The external AI provider returned:

```
"Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Could not process image'}}"
```

**Impact:** Expected for an unusable image. Real receipt PDFs/images need to be tested; the user story calls out possible “silent failures” in the parse→PO→receive flow that should be traced end-to-end.

---

## Not Tested (Require UI or Files)

| Flow | Reason |
|------|--------|
| Receipt Import → Save as PO | Needs real PDF/image |
| Purchase Order delivery/receive | No POs in seed (empty list) |
| Create Invoice from Financials | UI workflow |
| Xero sync | Integration |
| Contractor self-checkout (Scene 9) | POS gated by admin role — contractor cannot access |

---

## Edge Cases Verified

| Case | Result |
|------|--------|
| Wrong password | 401, "Invalid credentials" |
| Material request with missing sku/name | 400, validation error |
| Withdraw more than stock | 400, "Insufficient stock for X: requested 50, available 2" |
| Stock adjustment | 200, "Stock adjusted" |

---

## Recommendations

1. **Material Request schema** — Clarify or relax `sku`/`name` requirements for API consumers.
2. **API docs** — Add OpenAPI examples for `/material-requests` and `/withdrawals/for-contractor` (query vs body).
3. **E2E trace** — Manually run Document Parse → PO → Mark at Dock → Receive with a real receipt.
4. **Contractor POS** — Revisit whether contractors should have self-checkout; currently blocked by admin role.
5. **Chat route** — Fix any references to `/api/assistant/chat`; correct route is `/api/chat`.
