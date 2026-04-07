---
name: Fix e2e test failures
overview: Fix all 7 failing Playwright e2e tests. Eliminate pytest_minimal.sql by switching backend tests to selective truncation (keep seed reference data intact). Fix networkidle timeouts, SKU collision handling, and material request transaction boundary.
todos:
  - id: kill-pytest-minimal
    content: Replace TRUNCATE ALL + pytest_minimal.sql with selective truncation of transactional tables only. Delete pytest_minimal.sql. Backend tests run against full seed data from `supabase db reset`.
    status: completed
  - id: db-reset-e2e
    content: Add `supabase db reset` to `test:e2e` in bin/dev so e2e always runs against full seed data.
    status: completed
  - id: category-fallbacks
    content: Add `?? Object.values(ctx.categoryIds)[0]` fallback to withdrawal-financials, ledger-integrity, and stock-adjustments specs.
    status: completed
  - id: vendor-fallback
    content: Add vendor name fallback in po-receiving-stock.spec.ts for when listVendors returns empty.
    status: completed
  - id: networkidle-fix
    content: Replace all `waitForLoadState('networkidle')` with `domcontentloaded` in reports.page.ts, sidebar.component.ts, and contractor-material-request.spec.ts.
    status: completed
  - id: sku-collision
    content: Harden generate_sku() in sku_service.py with longer suffix and extra collision check.
    status: completed
  - id: mr-transaction
    content: Wrap create_material_request insert in a transaction() block.
    status: completed
  - id: verify-all-green
    content: Run ./bin/dev test && ./bin/dev test:e2e to verify all tests pass.
    status: in_progress
isProject: false
---

# Fix All 7 Failing Playwright E2E Tests

## Root Cause Analysis

All 7 failures trace to **two root causes** and **two secondary bugs**:

### Root Cause 1: DB state corruption between test suites (5 of 7 failures)

Backend tests (`_truncate_and_seed` in `conftest.py`) TRUNCATE every table and re-seed from `pytest_minimal.sql` - a stripped-down file with only 1 department (HDW), 0 vendors, and 4 users. After pytest finishes, this degraded state is what e2e tests inherit, since `./bin/dev test:e2e` does not reset the DB.

This causes:
- `ctx.categoryIds["ELE"]` / `["PNT"]` = `undefined` -> `category_id` omitted -> **422**
- `listVendors()` returns `[]` -> `vendors[0].name` -> **TypeError**

**Affected specs:** `withdrawal-financials`, `ledger-integrity`, `stock-adjustments`, `po-receiving-stock`, `inventory-api-guardrails`

### Root Cause 2: `networkidle` incompatible with persistent WebSocket (1 of 7)

`useRealtimeSync()` keeps a WebSocket open permanently. Playwright's `networkidle` needs zero connections for 500ms - never happens. `ReportsPage` and `SidebarNav` both use `waitForLoadState("networkidle")`.

**Affected spec:** `margin-accuracy` test 5d (60s timeout)

### Secondary Bug 1: SKU code collision not retry-safe (contributes to 1 of 7)

`generate_sku()` uses check-then-insert with `product_family_id[:4]` disambiguation - can still collide for UUIDv7 IDs generated in the same second, especially when all tests fall back to the same department.

**Affected spec:** `inventory-api-guardrails` (500 duplicate key on `idx_skus_sku`)

### Secondary Bug 2: `create_material_request` insert not in a transaction

`_db_operations().insert_material_request()` is called outside a `transaction()` block - a real code defect per project conventions.

---

## Fix Plan (single block of work)

### 1. Eliminate `pytest_minimal.sql` - selective truncation instead

**Core change:** Backend tests should run against the full seed data from `supabase db reset` (which `./bin/dev test` already runs before pytest). Instead of TRUNCATE ALL + re-seed a minimal file before each test, we only truncate the **transactional** tables that tests write to. Reference/config tables stay intact from the seed chain.

**Files:**
- [backend/tests/conftest.py](backend/tests/conftest.py) - replace `_truncate_and_seed()`
- [supabase/seeds/pytest_minimal.sql](supabase/seeds/pytest_minimal.sql) - **delete**

Replace the current `_truncate_and_seed`:

```python
async def _truncate_and_seed():
    from shared.infrastructure.db import transaction
    from shared.infrastructure.logging_config import org_id_var, user_id_var

    org_id_var.set(DEFAULT_ORG_ID)
    user_id_var.set(ADMIN_USER_ID)

    from shared.infrastructure.db import sql_execute

    async with transaction():
        await sql_execute(
            """TRUNCATE
                skus, product_families, sku_counters,
                withdrawals, invoices, invoice_line_items, invoice_counters,
                payments, returns, return_line_items,
                stock_transactions,
                purchase_orders, purchase_order_items,
                material_requests, material_request_items,
                fiscal_periods,
                cycle_counts, cycle_count_items,
                vendor_items
            CASCADE""",
            read_only=False,
        )
        # Reset department sku_count to 0 (tests create SKUs that increment it)
        await sql_execute(
            "UPDATE departments SET sku_count = 0",
            read_only=False,
        )
```

This preserves: `organizations`, `org_settings`, `departments`, `users`, `vendors`, `jobs`, `billing_entities`, `addresses`, `units_of_measure` - all from the real seed files.

The constants in [backend/tests/helpers/auth.py](backend/tests/helpers/auth.py) (`SEEDED_DEPT_ID`, `SEEDED_JOB_ID`, `SEEDED_VENDOR_ID`) already use IDs that match both `pytest_minimal.sql` AND the real seeds (`03_departments.sql`, `05_demo_business_data.sql`). No changes needed there.

Also remove the `_seed_sql_statements` helper and the UOM seed call (UOM data comes from `02_units_of_measure.sql` via `supabase db reset` and won't be truncated).

### 2. Add `supabase db reset` to `test:e2e` in `bin/dev`

**File:** [bin/dev](bin/dev) lines 61-65

```bash
test:e2e)
  _ensure_supabase
  supabase db reset --local --yes >/dev/null
  _load_supabase_env
  echo "Running e2e tests..."
  (cd e2e && npx playwright test "${@:2}")
  ;;
```

### 3. Add defensive fallbacks in e2e specs that lack them

Even with DB reset, these are a safety net:

- [e2e/specs/operations/withdrawal-financials.spec.ts](e2e/specs/operations/withdrawal-financials.spec.ts) line 53: `ctx.categoryIds["ELE"]` -> `ctx.categoryIds["ELE"] ?? Object.values(ctx.categoryIds)[0]`
- [e2e/specs/reports/ledger-integrity.spec.ts](e2e/specs/reports/ledger-integrity.spec.ts) line 44: same
- [e2e/specs/inventory/stock-adjustments.spec.ts](e2e/specs/inventory/stock-adjustments.spec.ts) line 33: `ctx.categoryIds["PNT"]` -> `ctx.categoryIds["PNT"] ?? Object.values(ctx.categoryIds)[0]`

### 4. Fix `po-receiving-stock` vendor dependency

**File:** [e2e/specs/purchasing/po-receiving-stock.spec.ts](e2e/specs/purchasing/po-receiving-stock.spec.ts) line 32

```typescript
vendorName = vendors[0]?.name ?? "E2E Test Vendor";
```

Safe because PO creation already uses `create_vendor_if_missing: true`.

### 5. Replace `networkidle` with DOM-based waits

**Files:**
- [e2e/pages/reports.page.ts](e2e/pages/reports.page.ts): replace `"networkidle"` with `"domcontentloaded"` in both methods
- [e2e/pages/sidebar.component.ts](e2e/pages/sidebar.component.ts): same in `navigateTo()`
- [e2e/specs/operations/contractor-material-request.spec.ts](e2e/specs/operations/contractor-material-request.spec.ts): lines 42, 50, 67

The WebSocket from `useRealtimeSync()` means `networkidle` will never resolve. Tests already assert specific DOM elements after navigation, which is the real readiness signal.

### 6. Harden `generate_sku()` collision handling

**File:** [backend/catalog/application/sku_service.py](backend/catalog/application/sku_service.py) lines 37-71

Use last 6 chars of family ID (instead of first 4) for disambiguation, and add a second fallback check:

```python
# Collision - use family ID tail for uniqueness (avoids UUIDv7 prefix overlap)
suffix = product_family_id.replace("-", "")[-6:].upper()
slug = slug_from_name(family_name or "", max_len=4) if family_name else _DEFAULT_SLUG
disambiguated = f"{department_code}-{slug}{suffix}-{str(number).zfill(2)}"

existing2 = await _db_catalog().find_sku_by_code(org_id, disambiguated)
if existing2 is None:
    return disambiguated

# Final fallback
return f"{department_code}-{slug}{suffix}-{str(number).zfill(2)}X"
```

### 7. Wrap `create_material_request` insert in a transaction

**File:** [backend/operations/application/material_request_service.py](backend/operations/application/material_request_service.py) lines 88-90

```python
async with transaction():
    await _db_operations().insert_material_request(
        current_user.organization_id, mat_request
    )
```

### 8. Verify all green

Run `./bin/dev test && ./bin/dev test:e2e` to confirm:
- All 716+ backend tests pass
- All 20 frontend tests pass
- All 85 Playwright e2e tests pass (0 failed, 0 skipped)
