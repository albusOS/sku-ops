import asyncio
import os
import tempfile
from pathlib import Path

# Load .env from backend/ before any other imports that use env vars
_path = Path(__file__).resolve().parent
if (_path / ".env").exists():
    from dotenv import load_dotenv
    load_dotenv(_path / ".env")

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Request, Form
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
import logging
import json
import re
import csv
import io
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from pydantic import BaseModel

# Stripe integration (optional - not on public PyPI; used in Emergent builds)
try:
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout,
        CheckoutSessionResponse,
        CheckoutStatusResponse,
        CheckoutSessionRequest,
    )
    HAS_EMERGENT_STRIPE = True
except ImportError:
    StripeCheckout = CheckoutSessionResponse = CheckoutStatusResponse = CheckoutSessionRequest = None
    HAS_EMERGENT_STRIPE = False

from db import init_db, close_db, get_connection
from repositories import (
    user_repo,
    department_repo,
    vendor_repo,
    product_repo,
    withdrawal_repo,
    payment_repo,
    sku_repo,
    invoice_repo,
)
from auth import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    require_role,
)
from models import (
    ROLES,
    User,
    UserCreate,
    UserUpdate,
    UserLogin,
    Department,
    DepartmentCreate,
    Vendor,
    VendorCreate,
    Product,
    ProductCreate,
    ProductUpdate,
    MaterialWithdrawal,
    MaterialWithdrawalCreate,
    InvoiceCreate,
    InvoiceUpdate,
)
from models.product import ALLOWED_BASE_UNITS
from services.uom_classifier import classify_uom, classify_uom_batch
from services.sku_slug import slug_from_name
from services.inventory import (
    process_withdrawal_stock_changes,
    process_import_stock_changes,
    process_receiving_stock_changes,
    get_stock_history,
    InsufficientStockError,
)

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==================== SKU GENERATOR ====================

SKU_FORMAT = "DEPT-SLUG-XXXXX"  # dept + slug from product name + sequence

async def generate_sku(department_code: str, product_name: Optional[str] = None) -> str:
    """Generate SKU: DEPT-SLUG-00001. Slug derived from product name for readability."""
    number = await sku_repo.increment_and_get(department_code)
    slug = slug_from_name(product_name or "", max_len=6) if product_name else "ITM"
    return f"{department_code}-{slug}-{str(number).zfill(6)}"


@api_router.get("/sku/preview")
async def get_sku_preview(
    department_id: str,
    product_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Preview the next SKU for a department (without consuming it)."""
    department = await department_repo.get_by_id(department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    code = department["code"]
    next_num = await sku_repo.get_next_number(code)
    slug = slug_from_name(product_name or "", max_len=6) if product_name else "ITM"
    next_sku = f"{code}-{slug}-{str(next_num).zfill(6)}"
    return {"next_sku": next_sku, "department_code": code, "format": SKU_FORMAT, "slug": slug}


@api_router.get("/sku/overview")
async def get_sku_overview(
    product_name: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """SKU system overview: format, departments with next available SKU."""
    departments = await department_repo.list_all()
    counters = await sku_repo.get_all_counters()
    slug = slug_from_name(product_name or "", max_len=6) if product_name else "ITM"
    depts_with_next = []
    for d in departments:
        code = d["code"]
        next_num = (counters.get(code, 0) + 1)
        depts_with_next.append({
            **d,
            "next_sku": f"{code}-{slug}-{str(next_num).zfill(6)}",
        })
    return {"format": SKU_FORMAT, "departments": depts_with_next}


# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(data: UserCreate):
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {ROLES}")

    user = User(
        email=data.email,
        name=data.name,
        role=data.role,
        company=data.company,
        billing_entity=data.billing_entity,
        phone=data.phone,
    )
    user_dict = user.model_dump()
    user_dict["password"] = hash_password(data.password)

    await user_repo.insert(user_dict)

    token = create_token(user.id, user.email, user.role)
    return {"token": token, "user": user.model_dump()}


@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await user_repo.get_by_email(data.email)
    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is disabled")

    token = create_token(user["id"], user["email"], user["role"])
    user_response = {k: v for k, v in user.items() if k not in ["password"]}
    return {"token": token, "user": user_response}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== CONTRACTOR MANAGEMENT (Admin Only) ====================

@api_router.get("/contractors")
async def get_contractors(current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    return await user_repo.list_contractors()


@api_router.post("/contractors")
async def create_contractor(data: UserCreate, current_user: dict = Depends(require_role("admin"))):
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    contractor = User(
        email=data.email,
        name=data.name,
        role="contractor",
        company=data.company or "Independent",
        billing_entity=data.billing_entity or data.company or "Independent",
        phone=data.phone,
    )
    contractor_dict = contractor.model_dump()
    contractor_dict["password"] = hash_password(data.password)

    await user_repo.insert(contractor_dict)

    return {k: v for k, v in contractor_dict.items() if k != "password"}


@api_router.put("/contractors/{contractor_id}")
async def update_contractor(contractor_id: str, data: UserUpdate, current_user: dict = Depends(require_role("admin"))):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    contractor = await user_repo.get_by_id(contractor_id)
    if not contractor or contractor.get("role") != "contractor":
        raise HTTPException(status_code=404, detail="Contractor not found")

    result = await user_repo.update(contractor_id, update_data)
    return {k: v for k, v in result.items() if k != "password"}


@api_router.delete("/contractors/{contractor_id}")
async def delete_contractor(contractor_id: str, current_user: dict = Depends(require_role("admin"))):
    deleted = await user_repo.delete_contractor(contractor_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Contractor not found")
    return {"message": "Contractor deleted"}

# ==================== DEPARTMENT ROUTES ====================

@api_router.get("/departments", response_model=List[Department])
async def get_departments(current_user: dict = Depends(get_current_user)):
    return await department_repo.list_all()


@api_router.post("/departments", response_model=Department)
async def create_department(data: DepartmentCreate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    existing = await department_repo.get_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")

    dept = Department(
        name=data.name,
        code=data.code.upper(),
        description=data.description or "",
    )
    await department_repo.insert(dept.model_dump())
    return dept


@api_router.put("/departments/{dept_id}", response_model=Department)
async def update_department(dept_id: str, data: DepartmentCreate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    result = await department_repo.update(dept_id, data.name, data.description or "")
    if not result:
        raise HTTPException(status_code=404, detail="Department not found")
    return result


@api_router.delete("/departments/{dept_id}")
async def delete_department(dept_id: str, current_user: dict = Depends(require_role("admin"))):
    product_count = await department_repo.count_products_by_department(dept_id)
    if product_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete department with products")

    deleted = await department_repo.delete(dept_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"message": "Department deleted"}

# ==================== VENDOR ROUTES ====================

@api_router.get("/vendors", response_model=List[Vendor])
async def get_vendors(current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    return await vendor_repo.list_all()


@api_router.post("/vendors", response_model=Vendor)
async def create_vendor(data: VendorCreate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    vendor = Vendor(**data.model_dump())
    await vendor_repo.insert(vendor.model_dump())
    return vendor


@api_router.put("/vendors/{vendor_id}", response_model=Vendor)
async def update_vendor(vendor_id: str, data: VendorCreate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    result = await vendor_repo.update(vendor_id, data.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return result


@api_router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, current_user: dict = Depends(require_role("admin"))):
    deleted = await vendor_repo.delete(vendor_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {"message": "Vendor deleted"}

# ==================== PRODUCT ROUTES ====================

@api_router.get("/products")
async def get_products(
    department_id: Optional[str] = None,
    search: Optional[str] = None,
    low_stock: bool = False,
    limit: Optional[int] = None,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    items = await product_repo.list_products(
        department_id=department_id,
        search=search,
        low_stock=low_stock,
        limit=limit,
        offset=offset,
    )
    if limit is not None:
        total = await product_repo.count_products(
            department_id=department_id,
            search=search,
            low_stock=low_stock,
        )
        return {"items": items, "total": total}
    return items


@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@api_router.get("/products/{product_id}/stock-history")
async def get_product_stock_history(
    product_id: str,
    limit: int = 50,
    current_user: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """Get stock transaction history for a product (stock ledger)."""
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    history = await get_stock_history(product_id=product_id, limit=limit)
    return {"product_id": product_id, "sku": product.get("sku"), "history": history}


class SuggestUomRequest(BaseModel):
    name: str
    description: Optional[str] = None


@api_router.post("/products/suggest-uom")
async def suggest_uom(data: SuggestUomRequest, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    """Use AI to suggest base_unit, sell_uom, pack_qty from product name."""
    result = await classify_uom(data.name, data.description)
    return result


@api_router.post("/products", response_model=Product)
async def create_product(data: ProductCreate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    department = await department_repo.get_by_id(data.department_id)
    if not department:
        raise HTTPException(status_code=400, detail="Department not found")

    vendor_name = ""
    if data.vendor_id:
        vendor = await vendor_repo.get_by_id(data.vendor_id)
        if vendor:
            vendor_name = vendor.get("name", "")

    sku = await generate_sku(department["code"], data.name)
    barcode = (data.barcode or "").strip() or sku  # Default to SKU when barcode blank

    product = Product(
        sku=sku,
        name=data.name,
        description=data.description or "",
        price=data.price,
        cost=data.cost,
        quantity=data.quantity,
        min_stock=data.min_stock,
        department_id=data.department_id,
        department_name=department["name"],
        vendor_id=data.vendor_id,
        vendor_name=vendor_name,
        original_sku=data.original_sku,
        barcode=barcode,
        base_unit=getattr(data, "base_unit", "each"),
        sell_uom=getattr(data, "sell_uom", "each"),
        pack_qty=getattr(data, "pack_qty", 1),
    )

    await product_repo.insert(product.model_dump())
    await department_repo.increment_product_count(data.department_id, 1)

    return product


@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, data: ProductUpdate, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    if "department_id" in update_data:
        department = await department_repo.get_by_id(update_data["department_id"])
        if department:
            update_data["department_name"] = department["name"]

    if "vendor_id" in update_data:
        if update_data["vendor_id"]:
            vendor = await vendor_repo.get_by_id(update_data["vendor_id"])
            update_data["vendor_name"] = vendor.get("name", "") if vendor else ""
        else:
            update_data["vendor_name"] = ""

    result = await product_repo.update(product_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await product_repo.delete(product_id)
    await department_repo.increment_product_count(product["department_id"], -1)

    return {"message": "Product deleted"}

# ==================== MATERIAL WITHDRAWAL (POS) ====================

@api_router.post("/withdrawals", response_model=MaterialWithdrawal)
async def create_withdrawal(data: MaterialWithdrawalCreate, current_user: dict = Depends(get_current_user)):
    """Create a material withdrawal - Contractors withdraw materials charged to their account"""
    if current_user.get("role") == "contractor":
        contractor = current_user
    else:
        contractor = current_user

    subtotal = sum(item.subtotal for item in data.items)
    cost_total = sum(item.cost * item.quantity for item in data.items)
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)

    withdrawal = MaterialWithdrawal(
        items=data.items,
        job_id=data.job_id,
        service_address=data.service_address,
        notes=data.notes,
        subtotal=subtotal,
        tax=tax,
        total=total,
        cost_total=cost_total,
        contractor_id=contractor["id"],
        contractor_name=contractor.get("name", ""),
        contractor_company=contractor.get("company", ""),
        billing_entity=contractor.get("billing_entity", ""),
        payment_status="unpaid",
        processed_by_id=current_user["id"],
        processed_by_name=current_user.get("name", ""),
    )

    # Atomic stock decrement + stock ledger (rolls back on insufficient stock)
    try:
        await process_withdrawal_stock_changes(
            items=data.items,
            withdrawal_id=withdrawal.id,
            user_id=current_user["id"],
            user_name=current_user.get("name", ""),
        )
    except InsufficientStockError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    await withdrawal_repo.insert(withdrawal.model_dump())
    # Auto-create invoice for Charge to Account withdrawals
    try:
        inv = await invoice_repo.create_from_withdrawals([withdrawal.id])
        withdrawal_dict = withdrawal.model_dump()
        withdrawal_dict["invoice_id"] = inv.get("id")
        return withdrawal_dict
    except ValueError:
        pass
    return withdrawal.model_dump()


@api_router.post("/withdrawals/for-contractor")
async def create_withdrawal_for_contractor(
    contractor_id: str,
    data: MaterialWithdrawalCreate,
    current_user: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """Warehouse manager creates withdrawal on behalf of a contractor"""
    contractor = await user_repo.get_by_id(contractor_id)
    if not contractor or contractor.get("role") != "contractor":
        raise HTTPException(status_code=404, detail="Contractor not found")

    subtotal = sum(item.subtotal for item in data.items)
    cost_total = sum(item.cost * item.quantity for item in data.items)
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)

    withdrawal = MaterialWithdrawal(
        items=data.items,
        job_id=data.job_id,
        service_address=data.service_address,
        notes=data.notes,
        subtotal=subtotal,
        tax=tax,
        total=total,
        cost_total=cost_total,
        contractor_id=contractor["id"],
        contractor_name=contractor.get("name", ""),
        contractor_company=contractor.get("company", ""),
        billing_entity=contractor.get("billing_entity", ""),
        payment_status="unpaid",
        processed_by_id=current_user["id"],
        processed_by_name=current_user.get("name", ""),
    )

    try:
        await process_withdrawal_stock_changes(
            items=data.items,
            withdrawal_id=withdrawal.id,
            user_id=current_user["id"],
            user_name=current_user.get("name", ""),
        )
    except InsufficientStockError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    await withdrawal_repo.insert(withdrawal.model_dump())
    # Auto-create invoice for Charge to Account withdrawals
    try:
        inv = await invoice_repo.create_from_withdrawals([withdrawal.id])
        return {**withdrawal.model_dump(), "invoice_id": inv.get("id")}
    except ValueError:
        pass
    return withdrawal.model_dump()


@api_router.get("/withdrawals")
async def get_withdrawals(
    contractor_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    billing_entity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    cid = current_user["id"] if current_user.get("role") == "contractor" else contractor_id
    return await withdrawal_repo.list_withdrawals(
        contractor_id=cid,
        payment_status=payment_status,
        billing_entity=billing_entity,
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )


@api_router.get("/withdrawals/{withdrawal_id}")
async def get_withdrawal(withdrawal_id: str, current_user: dict = Depends(get_current_user)):
    withdrawal = await withdrawal_repo.get_by_id(withdrawal_id)
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    # Contractors can only view their own
    if current_user.get("role") == "contractor" and withdrawal.get("contractor_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return withdrawal

# ==================== FINANCIAL DASHBOARD (Admin) ====================

@api_router.get("/financials/summary")
async def get_financial_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_role("admin"))
):
    """Get financial summary for admin dashboard"""
    withdrawals = await withdrawal_repo.list_withdrawals(
        start_date=start_date, end_date=end_date, limit=10000
    )
    
    # Calculate totals
    total_unpaid = sum(w["total"] for w in withdrawals if w.get("payment_status") == "unpaid")
    total_paid = sum(w["total"] for w in withdrawals if w.get("payment_status") == "paid")
    total_invoiced = sum(w["total"] for w in withdrawals if w.get("payment_status") == "invoiced")
    total_revenue = sum(w["total"] for w in withdrawals)
    total_cost = sum(w.get("cost_total", 0) for w in withdrawals)
    
    # By billing entity
    by_entity = {}
    for w in withdrawals:
        entity = w.get("billing_entity", "Unknown")
        if entity not in by_entity:
            by_entity[entity] = {"total": 0, "unpaid": 0, "paid": 0, "count": 0}
        by_entity[entity]["total"] += w["total"]
        by_entity[entity]["count"] += 1
        if w.get("payment_status") == "unpaid":
            by_entity[entity]["unpaid"] += w["total"]
        elif w.get("payment_status") == "paid":
            by_entity[entity]["paid"] += w["total"]
    
    # By contractor
    by_contractor = {}
    for w in withdrawals:
        cid = w.get("contractor_id", "Unknown")
        cname = w.get("contractor_name", "Unknown")
        if cid not in by_contractor:
            by_contractor[cid] = {"name": cname, "company": w.get("contractor_company", ""), "total": 0, "unpaid": 0, "count": 0}
        by_contractor[cid]["total"] += w["total"]
        by_contractor[cid]["count"] += 1
        if w.get("payment_status") == "unpaid":
            by_contractor[cid]["unpaid"] += w["total"]
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "gross_margin": round(total_revenue - total_cost, 2),
        "total_unpaid": round(total_unpaid, 2),
        "total_paid": round(total_paid, 2),
        "total_invoiced": round(total_invoiced, 2),
        "transaction_count": len(withdrawals),
        "by_billing_entity": by_entity,
        "by_contractor": list(by_contractor.values())
    }

@api_router.put("/withdrawals/{withdrawal_id}/mark-paid")
async def mark_withdrawal_paid(withdrawal_id: str, current_user: dict = Depends(require_role("admin"))):
    paid_at = datetime.now(timezone.utc).isoformat()
    result = await withdrawal_repo.mark_paid(withdrawal_id, paid_at)
    if not result:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    await invoice_repo.mark_paid_for_withdrawal(withdrawal_id)
    return result


@api_router.put("/withdrawals/bulk-mark-paid")
async def bulk_mark_paid(withdrawal_ids: List[str], current_user: dict = Depends(require_role("admin"))):
    paid_at = datetime.now(timezone.utc).isoformat()
    updated = await withdrawal_repo.bulk_mark_paid(withdrawal_ids, paid_at)
    for wid in withdrawal_ids:
        await invoice_repo.mark_paid_for_withdrawal(wid)
    return {"updated": updated}

@api_router.get("/financials/export")
async def export_financials(
    format: str = "csv",
    payment_status: Optional[str] = None,
    billing_entity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_role("admin"))
):
    """Export financial data as CSV"""
    withdrawals = await withdrawal_repo.list_withdrawals(
        payment_status=payment_status,
        billing_entity=billing_entity,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Transaction ID", "Date", "Contractor", "Company", "Billing Entity",
        "Job ID", "Service Address", "Subtotal", "Tax", "Total",
        "Cost", "Margin", "Payment Status", "Items"
    ])
    
    for w in withdrawals:
        items_str = "; ".join([f"{i['name']} x{i['quantity']}" for i in w.get("items", [])])
        writer.writerow([
            w.get("id", ""),
            w.get("created_at", "")[:10],
            w.get("contractor_name", ""),
            w.get("contractor_company", ""),
            w.get("billing_entity", ""),
            w.get("job_id", ""),
            w.get("service_address", ""),
            w.get("subtotal", 0),
            w.get("tax", 0),
            w.get("total", 0),
            w.get("cost_total", 0),
            round(w.get("total", 0) - w.get("cost_total", 0), 2),
            w.get("payment_status", ""),
            items_str
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=financials_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# ==================== INVOICES ====================

@api_router.get("/invoices")
async def get_invoices(
    status: Optional[str] = None,
    billing_entity: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_role("admin")),
):
    """List invoices with optional filters."""
    return await invoice_repo.list_invoices(
        status=status,
        billing_entity=billing_entity,
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )


@api_router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, current_user: dict = Depends(require_role("admin"))):
    """Get invoice with line items and linked withdrawals."""
    inv = await invoice_repo.get_by_id(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@api_router.post("/invoices")
async def create_invoice(
    data: InvoiceCreate,
    current_user: dict = Depends(require_role("admin")),
):
    """Create invoice from selected unpaid withdrawals. All must share same billing_entity."""
    try:
        inv = await invoice_repo.create_from_withdrawals(data.withdrawal_ids)
        return inv
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    data: InvoiceUpdate,
    current_user: dict = Depends(require_role("admin")),
):
    """Update invoice fields and/or line items."""
    inv = await invoice_repo.get_by_id(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_items_data = [i.model_dump() if hasattr(i, "model_dump") else i for i in (data.line_items or [])]
    updated = await invoice_repo.update(
        invoice_id,
        billing_entity=data.billing_entity,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        status=data.status,
        notes=data.notes,
        tax=data.tax,
        line_items=line_items_data if data.line_items is not None else None,
    )
    return updated


@api_router.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, current_user: dict = Depends(require_role("admin"))):
    """Delete draft invoice and unlink withdrawals."""
    try:
        ok = await invoice_repo.delete_draft(invoice_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return {"deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/invoices/{invoice_id}/sync-xero")
async def sync_invoice_to_xero(invoice_id: str, current_user: dict = Depends(require_role("admin"))):
    """Stub for future Xero integration."""
    inv = await invoice_repo.get_by_id(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "message": "Xero integration coming soon",
        "invoice_id": invoice_id,
        "invoice_number": inv.get("invoice_number"),
    }


# ==================== REPORTS ====================

@api_router.get("/reports/sales")
async def get_sales_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(require_role("admin", "warehouse_manager"))
):
    withdrawals = await withdrawal_repo.list_withdrawals(
        start_date=start_date, end_date=end_date, limit=10000
    )

    total_revenue = sum(w.get("total", 0) for w in withdrawals)
    total_tax = sum(w.get("tax", 0) for w in withdrawals)
    total_transactions = len(withdrawals)
    
    # By payment status
    by_status = {}
    for w in withdrawals:
        status = w.get("payment_status", "unknown")
        by_status[status] = by_status.get(status, 0) + w.get("total", 0)
    
    # Top products
    product_sales = {}
    for w in withdrawals:
        for item in w.get("items", []):
            pid = item.get("product_id")
            if pid:
                if pid not in product_sales:
                    product_sales[pid] = {"name": item.get("name"), "quantity": 0, "revenue": 0}
                product_sales[pid]["quantity"] += item.get("quantity", 0)
                product_sales[pid]["revenue"] += item.get("subtotal", 0)
    
    top_products = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    
    return {
        "total_revenue": round(total_revenue, 2),
        "total_tax": round(total_tax, 2),
        "total_transactions": total_transactions,
        "average_transaction": round(total_revenue / total_transactions, 2) if total_transactions > 0 else 0,
        "by_payment_status": by_status,
        "top_products": top_products
    }

@api_router.get("/reports/inventory")
async def get_inventory_report(current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    products = await product_repo.list_products()
    
    total_products = len(products)
    total_value = sum(p.get("price", 0) * p.get("quantity", 0) for p in products)
    total_cost = sum(p.get("cost", 0) * p.get("quantity", 0) for p in products)
    low_stock = [p for p in products if p.get("quantity", 0) <= p.get("min_stock", 5)]
    out_of_stock = [p for p in products if p.get("quantity", 0) == 0]
    
    by_department = {}
    for p in products:
        dept = p.get("department_name", "Unknown")
        if dept not in by_department:
            by_department[dept] = {"count": 0, "value": 0}
        by_department[dept]["count"] += 1
        by_department[dept]["value"] += p.get("price", 0) * p.get("quantity", 0)
    
    return {
        "total_products": total_products,
        "total_retail_value": round(total_value, 2),
        "total_cost_value": round(total_cost, 2),
        "potential_profit": round(total_value - total_cost, 2),
        "low_stock_count": len(low_stock),
        "out_of_stock_count": len(out_of_stock),
        "low_stock_items": low_stock[:20],
        "by_department": by_department
    }

# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.isoformat()
    
    # For contractors, show their own stats
    if current_user.get("role") == "contractor":
        my_withdrawals = await withdrawal_repo.list_withdrawals(
            contractor_id=current_user["id"], limit=1000
        )
        
        total_spent = sum(w.get("total", 0) for w in my_withdrawals)
        unpaid = sum(w.get("total", 0) for w in my_withdrawals if w.get("payment_status") == "unpaid")
        
        return {
            "total_withdrawals": len(my_withdrawals),
            "total_spent": round(total_spent, 2),
            "unpaid_balance": round(unpaid, 2),
            "recent_withdrawals": my_withdrawals[:5]
        }
    
    # For warehouse manager / admin
    today_withdrawals = await withdrawal_repo.list_withdrawals(
        start_date=today_str, limit=1000
    )
    today_revenue = sum(w.get("total", 0) for w in today_withdrawals)
    today_transactions = len(today_withdrawals)

    # Week revenue (last 7 days)
    week_start = (datetime.now(timezone.utc) - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start_str = week_start.isoformat()
    week_withdrawals = await withdrawal_repo.list_withdrawals(
        start_date=week_start_str, limit=10000
    )
    week_revenue = sum(w.get("total", 0) for w in week_withdrawals)

    total_products = await product_repo.count_all()
    low_stock_products = await product_repo.count_low_stock()
    total_vendors = await vendor_repo.count()
    total_contractors = await user_repo.count_contractors()

    # Unpaid totals
    unpaid_withdrawals = await withdrawal_repo.list_withdrawals(
        payment_status="unpaid", limit=10000
    )
    unpaid_total = sum(w.get("total", 0) for w in unpaid_withdrawals)

    recent_withdrawals = await withdrawal_repo.list_withdrawals(limit=5)
    low_stock_items = await product_repo.list_low_stock(10)

    # Revenue by day for last 7 days (for chart)
    revenue_by_day = {}
    for i in range(7):
        d = (datetime.now(timezone.utc) - timedelta(days=6 - i)).replace(hour=0, minute=0, second=0, microsecond=0)
        key = d.strftime("%Y-%m-%d")
        revenue_by_day[key] = 0
    for w in week_withdrawals:
        created = w.get("created_at", "")[:10]
        if created in revenue_by_day:
            revenue_by_day[created] += w.get("total", 0)
    revenue_by_day_list = [{"date": k, "revenue": round(v, 2)} for k, v in sorted(revenue_by_day.items())]

    return {
        "today_revenue": round(today_revenue, 2),
        "today_transactions": today_transactions,
        "week_revenue": round(week_revenue, 2),
        "revenue_by_day": revenue_by_day_list,
        "total_products": total_products,
        "low_stock_count": low_stock_products,
        "total_vendors": total_vendors,
        "total_contractors": total_contractors,
        "unpaid_total": round(unpaid_total, 2),
        "recent_withdrawals": recent_withdrawals,
        "low_stock_alerts": low_stock_items
    }

# ==================== DOCUMENT IMPORT (Unified) ====================

_DOCUMENT_PARSE_SYSTEM = """You are a document parser for a hardware store. Extract vendor/supplier name, document date, total, and line items from receipts, invoices, or packing slips.
Per item include: name, quantity, ordered_qty, delivered_qty, price, cost, original_sku, base_unit, sell_uom, pack_qty, suggested_department.
Allowed UOM: each, case, box, pack, bag, roll, kit, gallon, quart, pint, liter, pound, ounce, foot, meter, yard, sqft.
Infer UOM from product names (e.g. "5 Gal Paint" -> base_unit gallon, pack_qty 5). Use EFFECTIVE price after discounts.
When ordered/delivered unclear, set both to quantity. Use "each", "each", 1 for base_unit, sell_uom, pack_qty when unsure.
Suggested department codes: PLU, ELE, PNT, LUM, TOL, HDW, GDN, APP.
Return ONLY valid JSON: {"vendor_name": "...", "document_date": "YYYY-MM-DD", "total": N, "products": [{"name": "...", "quantity": 1, "ordered_qty": 1, "delivered_qty": 1, "price": 9.99, "cost": 7.99, "original_sku": "...", "base_unit": "each", "sell_uom": "each", "pack_qty": 1, "suggested_department": "HDW"}]}"""


@api_router.post("/documents/parse")
async def parse_document(file: UploadFile = File(...), current_user: dict = Depends(require_role("admin", "warehouse_manager"))):
    """Parse image or PDF document; extract vendor, items, UOM, costs, ordered/delivered."""
    try:
        contents = await file.read()
        if not os.environ.get("LLM_API_KEY"):
            raise HTTPException(status_code=500, detail="LLM API key not configured")

        content_type = (file.content_type or "").lower()
        is_pdf = content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")

        if is_pdf:
            from services.llm import generate_with_pdf
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                    tf.write(contents)
                    temp_path = tf.name
                response = await asyncio.to_thread(
                    generate_with_pdf,
                    "Extract all product and vendor information. Return only valid JSON.",
                    temp_path,
                    system_instruction=_DOCUMENT_PARSE_SYSTEM,
                )
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
        else:
            from services.llm import generate_with_image
            mime = content_type or "image/jpeg"
            if "image/" not in mime:
                mime = "image/jpeg"
            response = await asyncio.to_thread(
                generate_with_image,
                "Extract all product and vendor information. Return only valid JSON.",
                contents,
                mime_type=mime,
                system_instruction=_DOCUMENT_PARSE_SYSTEM,
            )

        if not response:
            raise HTTPException(status_code=500, detail="LLM failed to process document")

        json_match = re.search(r"\{[\s\S]*\}", response)
        extracted = json.loads(json_match.group()) if json_match else json.loads(response)

        # Ensure products have ordered_qty/delivered_qty
        for p in extracted.get("products", []):
            qty = p.get("quantity", 1)
            if "ordered_qty" not in p or p["ordered_qty"] is None:
                p["ordered_qty"] = qty
            if "delivered_qty" not in p or p["delivered_qty"] is None:
                p["delivered_qty"] = qty

        return extracted
    except json.JSONDecodeError as e:
        logger.error(f"Document parse JSON error: {e}")
        raise HTTPException(status_code=422, detail="Could not parse document data")
    except Exception as e:
        logger.error(f"Document parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    message: str
    messages: Optional[List[dict]] = None  # prior conversation [{role, content}]


@api_router.post("/chat")
async def chat_assistant(
    data: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Chat with AI assistant that can search products, inventory stats, low stock, departments, vendors."""
    from services.assistant import chat
    messages = data.messages or []
    result = await chat(messages, (data.message or "").strip())
    return result


class DocumentImportRequest(BaseModel):
    vendor_name: str
    create_vendor_if_missing: bool = True
    department_id: Optional[str] = None
    products: List[dict]


@api_router.post("/documents/import")
async def import_document(
    data: DocumentImportRequest,
    current_user: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """Import parsed products; create or match vendor."""
    vendor_name = (data.vendor_name or "").strip()
    if not vendor_name:
        raise HTTPException(status_code=400, detail="Vendor name is required")

    vendor = await vendor_repo.find_by_name(vendor_name)
    if not vendor:
        if not data.create_vendor_if_missing:
            raise HTTPException(status_code=400, detail=f"Vendor '{vendor_name}' not found. Enable 'Create vendor if missing' or add vendor first.")
        vendor_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        await vendor_repo.insert({
            "id": vendor_id,
            "name": vendor_name,
            "contact_name": "",
            "email": "",
            "phone": "",
            "address": "",
            "product_count": 0,
            "created_at": now,
        })
        vendor = {"id": vendor_id, "name": vendor_name}
        vendor_created = True
    else:
        vendor_id = vendor["id"]
        vendor_created = False

    departments = await department_repo.list_all()
    default_dept = await department_repo.get_by_code("HDW") or (departments[0] if departments else None)
    dept_by_id = {d["id"]: d for d in departments}
    dept_by_code = {d["code"].upper(): d for d in departments}

    selected = [p for p in data.products if p.get("selected", True)]
    needs_uom = [p for p in selected if (p.get("base_unit") or "").lower() not in ALLOWED_BASE_UNITS or (p.get("sell_uom") or "").lower() not in ALLOWED_BASE_UNITS]
    if needs_uom:
        await classify_uom_batch(needs_uom)

    imported = []
    matched = []
    errors = []
    for item in selected:
        try:
            delivered = item.get("delivered_qty")
            if delivered is None:
                delivered = item.get("quantity", 1)
            delivered = max(0, int(delivered))

            # Match existing: ordered -> delivered -> add to inventory (align SKU/classifications with existing)
            existing = None
            if item.get("original_sku") and vendor_id:
                existing = await product_repo.find_by_original_sku_and_vendor(
                    str(item.get("original_sku")).strip(), vendor_id
                )
            if existing:
                await process_receiving_stock_changes(
                    product_id=existing["id"],
                    sku=existing["sku"],
                    product_name=existing["name"],
                    quantity=delivered,
                    user_id=current_user["id"],
                    user_name=current_user.get("name", ""),
                    reference_id=None,
                )
                updated = await product_repo.get_by_id(existing["id"])
                matched.append(updated)
                continue

            # No match: create new product with parsed classifications
            dept = None
            if data.department_id and data.department_id in dept_by_id:
                dept = dept_by_id[data.department_id]
            if not dept:
                code = (item.get("suggested_department") or "HDW").upper()
                dept = dept_by_code.get(code) or default_dept
            if not dept:
                errors.append({"product": item.get("name"), "error": "No valid department"})
                continue

            sku = await generate_sku(dept["code"], item.get("name", "Unknown"))
            bu, su, pq = _resolve_uom(item)
            cost_val = float(item.get("cost") or 0) or float(item.get("price", 0)) * 0.7

            product = Product(
                sku=sku,
                name=item.get("name", "Unknown"),
                description=item.get("description", ""),
                price=float(item.get("price", 0)),
                cost=round(cost_val, 2),
                quantity=delivered,
                min_stock=5,
                department_id=dept["id"],
                department_name=dept["name"],
                vendor_id=vendor_id,
                vendor_name=vendor.get("name", ""),
                original_sku=item.get("original_sku"),
                base_unit=bu,
                sell_uom=su,
                pack_qty=pq,
            )
            await product_repo.insert(product.model_dump())
            await process_import_stock_changes(
                product_id=product.id,
                sku=product.sku,
                product_name=product.name,
                quantity=product.quantity,
                user_id=current_user["id"],
                user_name=current_user.get("name", ""),
            )
            imported.append(product)
            await department_repo.increment_product_count(dept["id"], 1)
            await vendor_repo.increment_product_count(vendor_id, 1)
        except Exception as e:
            errors.append({"product": item.get("name"), "error": str(e)})

    return {
        "vendor_id": vendor_id,
        "vendor_created": vendor_created,
        "imported": len(imported),
        "matched": len(matched),
        "errors": len(errors),
        "products": imported,
        "matched_products": matched,
        "error_details": errors,
    }


def _resolve_uom(item: dict) -> Tuple[str, str, int]:
    """Resolve base_unit, sell_uom, pack_qty from item, validating against allowed units."""
    bu = (item.get("base_unit") or "each").lower().strip()
    su = (item.get("sell_uom") or item.get("base_unit") or "each").lower().strip()
    pq = item.get("pack_qty")
    try:
        pq = max(1, int(pq)) if pq is not None else 1
    except (ValueError, TypeError):
        pq = 1
    bu = bu if bu in ALLOWED_BASE_UNITS else "each"
    su = su if su in ALLOWED_BASE_UNITS else "each"
    return bu, su, pq


# Keyword hints for auto-department from product name (Supply Yard style)
_DEPT_KEYWORDS = {
    "PLU": ["pex", "pvc", "cpvc", "pipe", "valve", "elbow", "coupling", "adapter", "sweat", "press", "crimp", "tailpiece", "drain", "faucet", "toilet", "sink"],
    "ELE": ["wire", "cable", "connector", "emt", "conduit", "outlet", "switch", "breaker", "led", "light", "lamp", "box", "strap", "clamp", "knockout"],
    "PNT": ["paint", "brush", "roller", "stain", "primer", "caulk", "spray", "sanding", "sandpaper"],
    "LUM": ["lumber", "board", "stud", "plywood", "2x4", "2x6", "trim", "furring", "door", "slab", "moulding"],
    "TOL": ["tool", "drill", "saw", "sander", "bit", "blade", "hammer", "screwdriver", "wrench", "level"],
    "HDW": ["screw", "nail", "bolt", "anchor", "hinge", "lock", "bracket", "fastener"],
    "GDN": ["garden", "plant", "soil", "fertilizer", "hose", "sprinkler"],
    "APP": ["appliance", "furnace", "range", "hood", "filter", "hvac"],
}


def _suggest_department(name: str, departments_by_code: dict) -> Optional[str]:
    """Suggest department code from product name using keyword matching."""
    if not name:
        return None
    name_lower = name.lower()
    for code, keywords in _DEPT_KEYWORDS.items():
        if code in departments_by_code and any(kw in name_lower for kw in keywords):
            return code
    return None


# UOM inference from product name (e.g. "5 Gal Paint" -> gallon, 5)
def _infer_uom(name: str) -> tuple[str, str, int]:
    """Infer base_unit, sell_uom, pack_qty from product name."""
    n = name.lower()
    # (pattern, unit) - pattern has optional (\d+) capture for pack_qty
    for pattern, unit in [
        (r"(\d+)\s*gal", "gallon"),
        (r"gal(?:lon)?\b", "gallon"),
        (r"(\d+)\s*pk\b", "each"),
        (r"(\d+)pk\b", "each"),
        (r"(\d+)\s*pack", "each"),
        (r"(\d+)\s*ft\b", "foot"),
        (r"(\d+)\s*'\s*", "foot"),
        (r"x(\d+)'", "foot"),
        (r"(\d+)\s*box", "box"),
        (r"(\d+)\s*roll", "roll"),
        (r"(\d+)\s*case", "case"),
        (r"(\d+)\s*lb", "pound"),
        (r"sq\s*ft", "sqft"),
    ]:
        m = re.search(pattern, n, re.IGNORECASE)
        if m and unit in ALLOWED_BASE_UNITS:
            pq = 1
            if m.groups() and m.group(1):
                try:
                    pq = max(1, int(m.group(1)))
                except (ValueError, TypeError):
                    pass
            return unit, unit, pq
    return "each", "each", 1


def _parse_dollar(val: str) -> float:
    """Parse '$2.73' or '2.73' to float."""
    if not val or not str(val).strip():
        return 0.0
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return round(float(s), 2)
    except (ValueError, TypeError):
        return 0.0


def _parse_csv_products(content: bytes) -> list[dict]:
    """
    Parse Supply Yard inventory CSV format.
    Columns: Product, SKU, Barcode, On hand, Reorder qty, Reorder point,
             Unit cost, Total cost, Retail price, Retail (Ex. Tax), Retail (Inc. Tax), Department/Category
    """
    decoded = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(decoded))

    # Find header row (first row containing 'Product' in first column)
    header = None
    header_idx = -1
    for i, row in enumerate(reader):
        if row and str(row[0]).strip().lower() == "product":
            header = [c.strip() for c in row]
            header_idx = i
            break

    if not header:
        raise ValueError("CSV must have a header row with 'Product' in first column")

    # Build column indices (handle slight variants)
    col_map = {}
    for idx, name in enumerate(header):
        n = name.lower()
        if "product" in n:
            col_map["name"] = idx
        elif "sku" in n and "barcode" not in n:
            col_map["sku"] = idx
        elif "on hand" in n or "quantity" in n:
            col_map["quantity"] = idx
        elif "reorder point" in n:
            col_map["min_stock"] = idx
        elif "unit cost" in n or "cost" in n:
            col_map["cost"] = idx
        elif "retail price" in n and "ex" not in n and "inc" not in n:
            col_map["price"] = idx
        elif "department" in n or "category" in n:
            col_map["department"] = idx
        elif "barcode" in n:
            col_map["barcode"] = idx

    if "name" not in col_map:
        raise ValueError("CSV must have a Product/name column")

    # Re-read from start to get data rows
    decoded2 = content.decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(decoded2)))

    products = []
    for i, row in enumerate(rows):
        if i <= header_idx or len(row) <= col_map["name"]:
            continue
        name = (row[col_map["name"]] or "").strip()
        if not name:
            continue
        # Skip meta rows
        if name.lower().startswith("current inventory") or name.lower().startswith("for the period"):
            continue

        qty = 0
        try:
            qty = int(float((row[col_map.get("quantity", 3)] or "0").replace(",", "")))
        except (ValueError, TypeError, IndexError):
            pass

        cost = _parse_dollar(row[col_map.get("cost", 6)] if col_map.get("cost", 6) < len(row) else "0")
        price = _parse_dollar(row[col_map.get("price", 8)] if col_map.get("price", 8) < len(row) else "0")
        if price <= 0 and cost > 0:
            price = round(cost * 1.4, 2)
        elif cost <= 0 and price > 0:
            cost = round(price * 0.7, 2)

        min_stock = 5
        try:
            min_stock = max(0, int(float((row[col_map.get("min_stock", 5)] or "0").replace(",", ""))))
        except (ValueError, TypeError, IndexError):
            pass
        if min_stock == 0:
            min_stock = 5

        products.append({
            "name": name,
            "quantity": qty,
            "cost": cost,
            "price": price,
            "min_stock": min_stock,
            "original_sku": (row[col_map["sku"]] or "").strip() or None if col_map.get("sku") is not None and col_map["sku"] < len(row) else None,
            "barcode": (row[col_map["barcode"]] or "").strip() or None if col_map.get("barcode") is not None and col_map["barcode"] < len(row) else None,
            "department": (row[col_map["department"]] or "").strip() or None if col_map.get("department") is not None and col_map["department"] < len(row) else None,
        })

    return products


@api_router.post("/products/import-csv")
async def import_products_csv(
    file: UploadFile = File(...),
    department_id: str = Form(...),
    vendor_id: Optional[str] = Form(None),
    current_user: dict = Depends(require_role("admin", "warehouse_manager")),
):
    """
    Bulk import products from a Supply Yard–style CSV.
    CSV columns: Product, SKU, Barcode, On hand, Reorder qty, Reorder point, Unit cost, Retail price, Department/Category
    """
    department = await department_repo.get_by_id(department_id)
    if not department:
        raise HTTPException(status_code=400, detail="Department not found")

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        rows = _parse_csv_products(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not rows:
        raise HTTPException(status_code=400, detail="No valid product rows found in CSV")

    vendor_name = ""
    if vendor_id:
        vendor = await vendor_repo.get_by_id(vendor_id)
        if vendor:
            vendor_name = vendor.get("name", "")

    # Build department lookup: by code, and for auto-suggest
    all_depts = await department_repo.list_all()
    dept_cache = {department["code"]: department, department["id"]: department}
    dept_by_code = {d["code"]: d for d in all_depts}
    for d in all_depts:
        dept_cache[d["code"]] = d
        dept_cache[d["name"].lower()] = d

    imported = []
    errors = []

    for item in rows:
        try:
            dept = department
            if item.get("department"):
                # CSV has department: match by code or name
                raw = item["department"].strip()
                key = raw.upper()[:3] if len(raw) >= 3 else raw.lower()
                dept = dept_cache.get(key) or dept_cache.get(raw.lower()) or department
            else:
                # Auto-suggest department from product name
                suggested_code = _suggest_department(item["name"], dept_by_code)
                if suggested_code:
                    dept = dept_by_code.get(suggested_code) or department

            sku = await generate_sku(dept["code"], item["name"])
            barcode = item.get("barcode") or sku  # Use SKU as barcode when CSV has none
            bu, su, pq = _infer_uom(item["name"])

            product = Product(
                sku=sku,
                name=item["name"],
                description="",
                price=item["price"],
                cost=item["cost"],
                quantity=item["quantity"],
                min_stock=item["min_stock"],
                department_id=dept["id"],
                department_name=dept["name"],
                vendor_id=vendor_id,
                vendor_name=vendor_name,
                original_sku=item.get("original_sku"),
                barcode=barcode,
                base_unit=bu,
                sell_uom=su,
                pack_qty=pq,
            )
            await product_repo.insert(product.model_dump())
            await process_import_stock_changes(
                product_id=product.id,
                sku=product.sku,
                product_name=product.name,
                quantity=product.quantity,
                user_id=current_user["id"],
                user_name=current_user.get("name", ""),
            )
            imported.append({"id": product.id, "sku": product.sku, "name": product.name, "quantity": product.quantity})
            await department_repo.increment_product_count(dept["id"], 1)
            if vendor_id:
                await vendor_repo.increment_product_count(vendor_id, 1)
        except Exception as e:
            errors.append({"product": item["name"], "error": str(e)})

    return {
        "imported": len(imported),
        "errors": len(errors),
        "products": imported,
        "error_details": errors[:20],
    }


# ==================== STRIPE PAYMENTS ====================

class CreatePaymentRequest(BaseModel):
    withdrawal_id: str
    origin_url: str

@api_router.post("/payments/create-checkout")
async def create_payment_checkout(data: CreatePaymentRequest, request: Request, current_user: dict = Depends(get_current_user)):
    """Create a Stripe checkout session for a withdrawal"""
    
    # Fetch the withdrawal
    withdrawal = await withdrawal_repo.get_by_id(data.withdrawal_id)
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    
    # Only allow payment for unpaid withdrawals
    if withdrawal.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="This withdrawal is already paid")
    
    if not HAS_EMERGENT_STRIPE:
        raise HTTPException(status_code=503, detail="Stripe integration not installed (emergentintegrations)")
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    # Build URLs using the origin provided by frontend
    origin = data.origin_url.rstrip("/")
    success_url = f"{origin}/pos?payment=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pos?payment=cancelled"
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Create checkout session - amount is from the server (withdrawal total), not from frontend
    amount = float(withdrawal.get("total", 0))
    
    metadata = {
        "withdrawal_id": data.withdrawal_id,
        "contractor_id": withdrawal.get("contractor_id", ""),
        "job_id": withdrawal.get("job_id", ""),
        "user_id": current_user["id"]
    }
    
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata
    )
    
    try:
        session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
        
        # Create payment transaction record
        payment_record = {
            "id": str(uuid.uuid4()),
            "session_id": session.session_id,
            "withdrawal_id": data.withdrawal_id,
            "user_id": current_user["id"],
            "contractor_id": withdrawal.get("contractor_id", ""),
            "amount": amount,
            "currency": "usd",
            "metadata": metadata,
            "payment_status": "pending",
            "status": "initiated",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await payment_repo.insert(payment_record)
        
        return {
            "checkout_url": session.url,
            "session_id": session.session_id
        }
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Check the status of a payment session and update records"""
    if not HAS_EMERGENT_STRIPE:
        raise HTTPException(status_code=503, detail="Stripe integration not installed (emergentintegrations)")
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    try:
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        
        # Find the payment transaction
        payment = await payment_repo.get_by_session_id(session_id)

        if payment and status.payment_status == "paid" and payment.get("payment_status") != "paid":
            paid_at = datetime.now(timezone.utc).isoformat()
            await payment_repo.update_status(session_id, "paid", "complete", paid_at)
            if payment.get("withdrawal_id"):
                await withdrawal_repo.mark_paid(payment["withdrawal_id"], paid_at)
                await invoice_repo.mark_paid_for_withdrawal(payment["withdrawal_id"])
        elif status.status == "expired":
            await payment_repo.update_status(session_id, "expired", "expired")
        
        return {
            "status": status.status,
            "payment_status": status.payment_status,
            "amount_total": status.amount_total,
            "currency": status.currency,
            "withdrawal_id": payment.get("withdrawal_id") if payment else None
        }
    except Exception as e:
        logger.error(f"Payment status check error: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking payment status: {str(e)}")

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    if not HAS_EMERGENT_STRIPE:
        raise HTTPException(status_code=503, detail="Stripe integration not installed (emergentintegrations)")
    stripe_api_key = os.environ.get("STRIPE_API_KEY")
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        host_url = str(request.base_url)
        webhook_url = f"{host_url}api/webhook/stripe"
        stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
        
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            
            # Update payment transaction
            payment = await payment_repo.get_by_session_id(session_id)

            if payment and payment.get("payment_status") != "paid":
                paid_at = datetime.now(timezone.utc).isoformat()
                await payment_repo.update_status(session_id, "paid", "complete", paid_at)
                if payment.get("withdrawal_id"):
                    await withdrawal_repo.mark_paid(payment["withdrawal_id"], paid_at)
                    await invoice_repo.mark_paid_for_withdrawal(payment["withdrawal_id"])

        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True, "error": str(e)}

# ==================== SEED DATA ====================

DEMO_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "SY Inventory - Sheet1 (1).csv")
DEMO_PRODUCT_LIMIT = 2000  # Full CSV (~1270 products)


async def _seed_standard_departments() -> None:
    """Seed standard departments if not present."""
    standard = [
        {"name": "Lumber", "code": "LUM", "description": "Wood, plywood, boards"},
        {"name": "Plumbing", "code": "PLU", "description": "Pipes, fittings, fixtures"},
        {"name": "Electrical", "code": "ELE", "description": "Wiring, outlets, switches"},
        {"name": "Paint", "code": "PNT", "description": "Paint, stains, brushes"},
        {"name": "Tools", "code": "TOL", "description": "Hand tools, power tools"},
        {"name": "Hardware", "code": "HDW", "description": "Fasteners, hinges, locks"},
        {"name": "Garden", "code": "GDN", "description": "Plants, soil, fertilizers"},
        {"name": "Appliances", "code": "APP", "description": "Home appliances"},
    ]
    for d in standard:
        if not await department_repo.get_by_code(d["code"]):
            await department_repo.insert(Department(**d).model_dump())


async def seed_demo_inventory() -> None:
    """Seed ~150 products from CSV on first run for full demo experience."""
    try:
        count = await product_repo.count_all()
        if count > 0:
            return
        if not os.path.exists(DEMO_CSV_PATH):
            logger.warning(f"Demo CSV not found: {DEMO_CSV_PATH}")
            return

        await _seed_standard_departments()
        demo_user = await user_repo.get_by_email(MOCK_USER_EMAIL)
        if not demo_user:
            logger.warning("Demo user not found, skipping inventory seed")
            return

        with open(DEMO_CSV_PATH, "rb") as f:
            content = f.read()
        rows = _parse_csv_products(content)
        all_depts = await department_repo.list_all()
        dept_by_code = {d["code"]: d for d in all_depts}

        imported = 0
        for i, item in enumerate(rows):
            if imported >= DEMO_PRODUCT_LIMIT:
                break
            try:
                dept = None
                if item.get("department"):
                    raw = item["department"].strip()
                    key = raw.upper()[:3] if len(raw) >= 3 else raw.lower()
                    dept = next((d for d in all_depts if d["code"] == key or d["name"].lower() == raw.lower()), None)
                if not dept:
                    suggested = _suggest_department(item["name"], dept_by_code)
                    dept = dept_by_code.get(suggested) if suggested else None
                if not dept:
                    dept = all_depts[0]

                sku = await generate_sku(dept["code"], item["name"])
                barcode = item.get("barcode") or sku
                bu, su, pq = _infer_uom(item["name"])

                # Company's own inventory – no vendor (vendor = who we buy FROM)
                product = Product(
                    sku=sku,
                    name=item["name"],
                    description="",
                    price=item["price"],
                    cost=item["cost"],
                    quantity=item["quantity"],
                    min_stock=max(5, item["min_stock"]),
                    department_id=dept["id"],
                    department_name=dept["name"],
                    vendor_id=None,
                    vendor_name="",
                    original_sku=item.get("original_sku"),
                    barcode=barcode,
                    base_unit=bu,
                    sell_uom=su,
                    pack_qty=pq,
                )
                await product_repo.insert(product.model_dump())
                await process_import_stock_changes(
                    product_id=product.id,
                    sku=product.sku,
                    product_name=product.name,
                    quantity=product.quantity,
                    user_id=demo_user["id"],
                    user_name=demo_user.get("name", "Demo"),
                )
                await department_repo.increment_product_count(dept["id"], 1)
                imported += 1
            except Exception as e:
                logger.debug(f"Demo seed skip {item.get('name')}: {e}")

        logger.info(f"Demo inventory seeded: {imported} products")
    except Exception as e:
        logger.warning(f"Demo inventory seed: {e}")


@api_router.post("/seed/departments")
async def seed_departments():
    await _seed_standard_departments()
    return {"message": "Departments ready"}


@api_router.post("/seed/reset-inventory")
async def reset_and_reseed_inventory(current_user: dict = Depends(require_role("admin"))):
    """Reset products and stock, then re-run demo seed. For assessment with fresh data."""
    conn = get_connection()
    try:
        await conn.execute("DELETE FROM stock_transactions")
        await conn.execute("DELETE FROM products")
        await conn.execute("DELETE FROM sku_counters")
        await conn.execute("UPDATE departments SET product_count = 0")
        await conn.execute("UPDATE vendors SET product_count = 0")
        await conn.commit()
        logger.info("Inventory reset complete")
        await seed_demo_inventory()
        count = await product_repo.count_all()
        return {"message": f"Inventory reset and reseeded with {count} products"}
    except Exception as e:
        logger.error(f"Reset inventory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MAIN ====================

@api_router.get("/")
async def root():
    return {"message": "Supply Yard API - Material Management System"}

app.include_router(api_router)


MOCK_USER_EMAIL = "admin@demo.local"
MOCK_USER_PASSWORD = "demo123"


async def seed_mock_user():
    """Create a demo admin user if none exists."""
    try:
        existing = await user_repo.get_by_email(MOCK_USER_EMAIL)
        if not existing:
            user = User(
                email=MOCK_USER_EMAIL,
                name="Demo Admin",
                role="admin",
            )
            user_dict = user.model_dump()
            user_dict["password"] = hash_password(MOCK_USER_PASSWORD)
            await user_repo.insert(user_dict)
            logger.info(f"Mock user created: {MOCK_USER_EMAIL}")
    except Exception as e:
        logger.warning(f"Mock user seed: {e}")


@app.on_event("startup")
async def startup():
    """Initialize SQLite database on startup."""
    try:
        await init_db()
        logger.info("Database initialized")
        await seed_mock_user()
        await _seed_standard_departments()
        await seed_demo_inventory()
    except Exception as e:
        logger.warning(f"Database init: {e}")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_db()
