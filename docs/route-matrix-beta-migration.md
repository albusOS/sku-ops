# Route Matrix: Old to Beta Migration

## Exceptions (unchanged)

- `devtools/api/seed.py` -> stays at `/api/seed/...` (not versioned in this refactor)

## Context-by-context mapping

### assistant (multi-file -> sub_routers)


| Old file                    | Old path                                             | New path                                                                                          |
| --------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| assistant/api/chat.py       | /api/chat/status, /api/chat, /api/chat/sessions/{id} | /api/beta/assistant/chat/status, /api/beta/assistant/chat, /api/beta/assistant/chat/sessions/{id} |
| assistant/api/monitoring.py | /api/admin/agents/*                                  | /api/beta/assistant/admin/agents/*                                                                |
| assistant/api/ws_chat.py    | /api/ws/chat                                         | /api/beta/assistant/ws/chat                                                                       |


### catalog (multi-file -> sub_routers)


| Old file                        | Old path                            | New path                                                      |
| ------------------------------- | ----------------------------------- | ------------------------------------------------------------- |
| catalog/api/departments.py      | /api/departments                    | /api/beta/catalog/departments                                 |
| catalog/api/product_families.py | /api/catalog/products               | /api/beta/catalog/products                                    |
| catalog/api/products.py         | /api/catalog/skus                   | /api/beta/catalog/skus                                        |
| catalog/api/vendor_items.py     | /api/catalog/skus/{id}/vendors      | /api/beta/catalog/skus/{id}/vendors                           |
| catalog/api/sku.py              | /api/sku/preview, /api/sku/overview | /api/beta/catalog/sku/preview, /api/beta/catalog/sku/overview |
| catalog/api/vendors.py          | /api/vendors                        | /api/beta/catalog/vendors                                     |


### documents (single-file -> parent router)


| Old file                   | Old path       | New path                      |
| -------------------------- | -------------- | ----------------------------- |
| documents/api/documents.py | /api/documents | /api/beta/documents/documents |


### finance (multi-file -> sub_routers)


| Old file                        | Old path              | New path                                            |
| ------------------------------- | --------------------- | --------------------------------------------------- |
| finance/api/billing_entities.py | /api/billing-entities | /api/beta/finance/billing-entities                  |
| finance/api/credit_notes.py     | /api/credit-notes     | /api/beta/finance/credit-notes                      |
| finance/api/financials.py       | /api/financials       | /api/beta/finance/financials                        |
| finance/api/fiscal_periods.py   | /api/fiscal-periods   | /api/beta/finance/fiscal-periods                    |
| finance/api/invoices.py         | /api/invoices         | /api/beta/finance/invoices                          |
| finance/api/payments.py         | /api/payments         | /api/beta/finance/payments                          |
| finance/api/settings.py         | /api/settings         | /api/beta/finance/settings                          |
| finance/api/xero_auth.py        | /api/xero             | /api/beta/finance/xero                              |
| finance/api/xero_health.py      | /api/xero             | /api/beta/finance/xero (merge into xero sub-router) |


### inventory (multi-file -> sub_routers)


| Old file                      | Old path          | New path                         |
| ----------------------------- | ----------------- | -------------------------------- |
| inventory/api/cycle_counts.py | /api/cycle-counts | /api/beta/inventory/cycle-counts |
| inventory/api/stock.py        | /api/stock        | /api/beta/inventory/stock        |


### jobs (single-file -> parent router)


| Old file         | Old path  | New path            |
| ---------------- | --------- | ------------------- |
| jobs/api/jobs.py | /api/jobs | /api/beta/jobs/jobs |


### operations (multi-file -> sub_routers)


| Old file                            | Old path               | New path                               |
| ----------------------------------- | ---------------------- | -------------------------------------- |
| operations/api/contractors.py       | /api/contractors       | /api/beta/operations/contractors       |
| operations/api/material_requests.py | /api/material-requests | /api/beta/operations/material-requests |
| operations/api/returns.py           | /api/returns           | /api/beta/operations/returns           |
| operations/api/withdrawals.py       | /api/withdrawals       | /api/beta/operations/withdrawals       |


### purchasing (single-file -> parent router)


| Old file                          | Old path             | New path                             |
| --------------------------------- | -------------------- | ------------------------------------ |
| purchasing/api/purchase_orders.py | /api/purchase-orders | /api/beta/purchasing/purchase-orders |


### reports (multi-file -> sub_routers)


| Old file                 | Old path       | New path                    |
| ------------------------ | -------------- | --------------------------- |
| reports/api/dashboard.py | /api/dashboard | /api/beta/reports/dashboard |
| reports/api/reports.py   | /api/reports   | /api/beta/reports/reports   |


### shared (multi-file -> sub_routers)


| Old file                | Old path                                | New path                                                                    |
| ----------------------- | --------------------------------------- | --------------------------------------------------------------------------- |
| shared/api/addresses.py | /api/addresses                          | /api/beta/shared/addresses                                                  |
| shared/api/audit.py     | /api/audit-log                          | /api/beta/shared/audit-log                                                  |
| shared/api/auth.py      | /api/auth                               | /api/beta/shared/auth                                                       |
| shared/api/health.py    | /api/health, /api/ready, /api/health/ai | /api/beta/shared/health, /api/beta/shared/ready, /api/beta/shared/health/ai |
| shared/api/websocket.py | /api/ws                                 | /api/beta/shared/ws                                                         |


