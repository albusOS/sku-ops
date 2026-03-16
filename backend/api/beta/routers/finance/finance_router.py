"""Finance context router - billing entities, credit notes, financials, fiscal periods, invoices, payments, settings, xero."""

from fastapi import APIRouter

from api.beta.routers.finance.sub_routers import (
    billing_entities_router,
    credit_notes_router,
    financials_router,
    fiscal_periods_router,
    invoices_router,
    payments_router,
    settings_router,
    xero_router,
)

router = APIRouter(prefix="/finance", tags=["finance"])

SUB_ROUTERS = (
    billing_entities_router,
    credit_notes_router,
    financials_router,
    fiscal_periods_router,
    invoices_router,
    payments_router,
    settings_router,
    xero_router,
)

for sub_router in SUB_ROUTERS:
    router.include_router(sub_router)
