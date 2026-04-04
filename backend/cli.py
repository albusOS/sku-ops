"""
SKU-Ops CLI — terminal observability for multi-tenant operations.

Usage:
    uv run python -m cli db:status          # DB connection + table sizes
    uv run python -m cli db:check [org_id]  # Integrity checks
    uv run python -m cli tenant:list        # All tenants with stats
    uv run python -m cli tenant:health ID   # Deep tenant health
    uv run python -m cli tx:audit [org_id]  # Stock ledger verification
    uv run python -m cli tx:recent [org_id] # Recent transactions
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from rich.console import Console
from rich.table import Table

console = Console()
err = Console(stderr=True)


def _resolve_db_url() -> str:
    backend_env = Path(__file__).resolve().parent / ".env"
    root_env = Path(__file__).resolve().parent.parent / ".env"

    # Simple .env loader (no dotenv dependency at CLI level)
    for envfile in [root_env, backend_env]:
        if envfile.exists():
            for line in envfile.read_text().splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, v = stripped.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k not in os.environ:
                    os.environ[k] = v

    return os.environ.get("DATABASE_URL", "postgresql://sku_ops:localdev@localhost:5433/sku_ops")


async def get_conn(url: str) -> asyncpg.Connection:
    return await asyncpg.connect(url)


# ── db:status ────────────────────────────────────────────────────────────────


async def cmd_db_status(conn: asyncpg.Connection, _args: argparse.Namespace):
    """Database connection health, version, and table sizes."""
    console.rule("[bold]Database Status")

    # Connection info
    version = await conn.fetchval("SELECT version()")
    db_name = await conn.fetchval("SELECT current_database()")
    db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
    active = await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
    console.print(f"  Database : [cyan]{db_name}[/]")
    console.print(f"  Size     : [cyan]{db_size}[/]")
    console.print(f"  Active   : [cyan]{active}[/] connections")
    console.print(f"  Version  : [dim]{version[:60]}…[/]")

    # Table sizes
    rows = await conn.fetch("""
        SELECT relname AS name,
               n_live_tup AS rows,
               pg_size_pretty(pg_total_relation_size(c.oid)) AS size
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
        ORDER BY pg_total_relation_size(c.oid) DESC
    """)

    if not rows:
        console.print("\n[yellow]No tables found.[/]")
        return

    t = Table(title="Table Sizes", show_lines=False)
    t.add_column("Table", style="cyan")
    t.add_column("Rows", justify="right", style="green")
    t.add_column("Size", justify="right", style="yellow")

    for r in rows:
        t.add_row(r["name"], str(r["rows"] or 0), r["size"])

    console.print()
    console.print(t)


# ── db:check ─────────────────────────────────────────────────────────────────

INTEGRITY_CHECKS = [
    {
        "name": "Orphan SKUs (no product family)",
        "sql": """
            SELECT count(*) FROM skus s
            LEFT JOIN products p ON p.id = s.product_family_id
            WHERE s.product_family_id IS NOT NULL AND p.id IS NULL
            {org_filter_s}
        """,
        "expect": 0,
    },
    {
        "name": "Orphan withdrawal items (no withdrawal)",
        "sql": """
            SELECT count(*) FROM withdrawal_items wi
            LEFT JOIN withdrawals w ON w.id = wi.withdrawal_id
            WHERE w.id IS NULL
        """,
        "expect": 0,
    },
    {
        "name": "Orphan return items (no return)",
        "sql": """
            SELECT count(*) FROM return_items ri
            LEFT JOIN returns r ON r.id = ri.return_id
            WHERE r.id IS NULL
        """,
        "expect": 0,
    },
    {
        "name": "Orphan PO items (no PO)",
        "sql": """
            SELECT count(*) FROM purchase_order_items poi
            LEFT JOIN purchase_orders po ON po.id = poi.po_id
            WHERE po.id IS NULL
        """,
        "expect": 0,
    },
    {
        "name": "Orphan invoice line items (no invoice)",
        "sql": """
            SELECT count(*) FROM invoice_line_items ili
            LEFT JOIN invoices i ON i.id = ili.invoice_id
            WHERE i.id IS NULL
        """,
        "expect": 0,
    },
    {
        "name": "Invoice-withdrawal links pointing to missing records",
        "sql": """
            SELECT count(*) FROM invoice_withdrawals iw
            LEFT JOIN invoices i ON i.id = iw.invoice_id
            LEFT JOIN withdrawals w ON w.id = iw.withdrawal_id
            WHERE i.id IS NULL OR w.id IS NULL
        """,
        "expect": 0,
    },
    {
        "name": "Withdrawals with payment_status='invoiced' but no invoice",
        "sql": """
            SELECT count(*) FROM withdrawals w
            WHERE w.payment_status = 'invoiced' AND w.invoice_id IS NULL
            {org_filter_w}
        """,
        "expect": 0,
    },
    {
        "name": "Negative SKU quantities",
        "sql": """
            SELECT count(*) FROM skus
            WHERE quantity < 0 AND deleted_at IS NULL
            {org_filter}
        """,
        "expect": 0,
    },
    {
        "name": "Stock transactions with zero delta",
        "sql": """
            SELECT count(*) FROM stock_transactions
            WHERE quantity_delta = 0
            {org_filter}
        """,
        "expect": 0,
    },
    {
        "name": "Duplicate SKU codes (same org)",
        "sql": """
            SELECT count(*) FROM (
                SELECT sku, organization_id, count(*) c
                FROM skus WHERE deleted_at IS NULL
                GROUP BY sku, organization_id HAVING count(*) > 1
            ) dupes
        """,
        "expect": 0,
    },
    {
        "name": "Invoices with total != sum of line items",
        "sql": """
            SELECT count(*) FROM invoices i
            JOIN (
                SELECT invoice_id, ROUND(SUM(amount)::numeric, 2) AS item_total
                FROM invoice_line_items GROUP BY invoice_id
            ) li ON li.invoice_id = i.id
            WHERE ABS(i.subtotal - li.item_total) > 0.01
            {org_filter_i}
        """,
        "expect": 0,
    },
]


async def cmd_db_check(conn: asyncpg.Connection, args: argparse.Namespace):
    """Run integrity checks against the database."""
    org_id = args.org_id
    console.rule(f"[bold]Integrity Checks{f' (org: {org_id[:8]}…)' if org_id else ''}")

    passed = 0
    failed = 0

    for check in INTEGRITY_CHECKS:
        sql = check["sql"]
        # Apply org filter if org_id provided
        if org_id:
            sql = sql.replace("{org_filter_s}", f"AND s.organization_id = '{org_id}'")
            sql = sql.replace("{org_filter_w}", f"AND w.organization_id = '{org_id}'")
            sql = sql.replace("{org_filter_i}", f"AND i.organization_id = '{org_id}'")
            sql = sql.replace("{org_filter}", f"AND organization_id = '{org_id}'")
        else:
            sql = sql.replace("{org_filter_s}", "")
            sql = sql.replace("{org_filter_w}", "")
            sql = sql.replace("{org_filter_i}", "")
            sql = sql.replace("{org_filter}", "")

        try:
            result = await conn.fetchval(sql)
            ok = result == check["expect"]
            if ok:
                console.print(f"  [green]✓[/] {check['name']}")
                passed += 1
            else:
                console.print(f"  [red]✗[/] {check['name']} — found [red]{result}[/] (expected {check['expect']})")
                failed += 1
        except Exception as e:
            console.print(f"  [yellow]?[/] {check['name']} — [yellow]{e}[/]")

    console.print()
    if failed:
        console.print(f"  [red]{failed} failed[/], {passed} passed")
    else:
        console.print(f"  [green]All {passed} checks passed[/]")


# ── tenant:list ──────────────────────────────────────────────────────────────


async def cmd_tenant_list(conn: asyncpg.Connection, _args: argparse.Namespace):
    """List all organizations with key stats."""
    console.rule("[bold]Tenants")

    orgs = await conn.fetch("SELECT id, name, slug, created_at FROM organizations ORDER BY created_at")

    if not orgs:
        console.print("[yellow]No organizations found.[/]")
        return

    t = Table(title="Organizations", show_lines=True)
    t.add_column("Name", style="cyan")
    t.add_column("Slug", style="dim")
    t.add_column("SKUs", justify="right")
    t.add_column("Vendors", justify="right")
    t.add_column("Withdrawals", justify="right")
    t.add_column("Invoices", justify="right")
    t.add_column("POs", justify="right")
    t.add_column("Stock Txns", justify="right")
    t.add_column("Created", style="dim")

    for org in orgs:
        oid = org["id"]
        skus = await conn.fetchval("SELECT count(*) FROM skus WHERE organization_id = $1 AND deleted_at IS NULL", oid)
        vendors = await conn.fetchval(
            "SELECT count(*) FROM vendors WHERE organization_id = $1 AND deleted_at IS NULL", oid
        )
        withdrawals = await conn.fetchval("SELECT count(*) FROM withdrawals WHERE organization_id = $1", oid)
        invoices = await conn.fetchval(
            "SELECT count(*) FROM invoices WHERE organization_id = $1 AND deleted_at IS NULL", oid
        )
        pos = await conn.fetchval("SELECT count(*) FROM purchase_orders WHERE organization_id = $1", oid)
        txns = await conn.fetchval("SELECT count(*) FROM stock_transactions WHERE organization_id = $1", oid)

        t.add_row(
            org["name"],
            org["slug"],
            str(skus),
            str(vendors),
            str(withdrawals),
            str(invoices),
            str(pos),
            str(txns),
            org["created_at"].strftime("%Y-%m-%d") if org["created_at"] else "—",
        )

    console.print(t)


# ── tenant:health ────────────────────────────────────────────────────────────


async def cmd_tenant_health(conn: asyncpg.Connection, args: argparse.Namespace):
    """Deep health check for a specific tenant."""
    org_id = args.org_id
    if not org_id:
        err.print("[red]org_id required for tenant:health[/]")
        sys.exit(1)

    # Resolve org
    org = await conn.fetchrow("SELECT id, name, slug FROM organizations WHERE id = $1 OR slug = $1", org_id)
    if not org:
        err.print(f"[red]Organization not found: {org_id}[/]")
        sys.exit(1)

    oid = org["id"]
    console.rule(f"[bold]Tenant Health: {org['name']} ({org['slug']})")

    # Catalog stats
    console.print("\n[bold]Catalog[/]")
    skus = await conn.fetchval("SELECT count(*) FROM skus WHERE organization_id = $1 AND deleted_at IS NULL", oid)
    products = await conn.fetchval(
        "SELECT count(*) FROM products WHERE organization_id = $1 AND deleted_at IS NULL", oid
    )
    vendors = await conn.fetchval("SELECT count(*) FROM vendors WHERE organization_id = $1 AND deleted_at IS NULL", oid)
    departments = await conn.fetchval(
        "SELECT count(*) FROM departments WHERE organization_id = $1 AND deleted_at IS NULL", oid
    )
    vendor_items = await conn.fetchval(
        "SELECT count(*) FROM vendor_items WHERE organization_id = $1 AND deleted_at IS NULL", oid
    )
    console.print(
        f"  Products: [cyan]{products}[/]  SKUs: [cyan]{skus}[/]  "
        f"Vendors: [cyan]{vendors}[/]  Departments: [cyan]{departments}[/]  "
        f"Vendor-Items: [cyan]{vendor_items}[/]"
    )

    # SKU health
    zero_qty = await conn.fetchval(
        "SELECT count(*) FROM skus WHERE organization_id = $1 AND deleted_at IS NULL AND quantity = 0",
        oid,
    )
    negative_qty = await conn.fetchval(
        "SELECT count(*) FROM skus WHERE organization_id = $1 AND deleted_at IS NULL AND quantity < 0",
        oid,
    )
    below_min = await conn.fetchval(
        "SELECT count(*) FROM skus WHERE organization_id = $1 AND deleted_at IS NULL "
        "AND quantity < min_stock AND min_stock > 0",
        oid,
    )
    no_vendor = await conn.fetchval(
        """
        SELECT count(*) FROM skus s
        WHERE s.organization_id = $1 AND s.deleted_at IS NULL
        AND NOT EXISTS (SELECT 1 FROM vendor_items vi WHERE vi.sku_id = s.id AND vi.deleted_at IS NULL)
    """,
        oid,
    )
    neg_color = "red" if negative_qty else "green"
    console.print(
        f"  Zero stock: [yellow]{zero_qty}[/]  Negative: [{neg_color}]{negative_qty}[/]  "
        f"Below min: [yellow]{below_min}[/]  No vendor link: [yellow]{no_vendor}[/]"
    )

    # Operations stats
    console.print("\n[bold]Operations[/]")
    withdrawals = await conn.fetchval("SELECT count(*) FROM withdrawals WHERE organization_id = $1", oid)
    unpaid = await conn.fetchval(
        "SELECT count(*) FROM withdrawals WHERE organization_id = $1 AND payment_status = 'unpaid'",
        oid,
    )
    invoiced = await conn.fetchval(
        "SELECT count(*) FROM withdrawals WHERE organization_id = $1 AND payment_status = 'invoiced'",
        oid,
    )
    paid = await conn.fetchval(
        "SELECT count(*) FROM withdrawals WHERE organization_id = $1 AND payment_status = 'paid'",
        oid,
    )
    returns = await conn.fetchval("SELECT count(*) FROM returns WHERE organization_id = $1", oid)
    console.print(
        f"  Withdrawals: [cyan]{withdrawals}[/] (unpaid: [yellow]{unpaid}[/], "
        f"invoiced: [cyan]{invoiced}[/], paid: [green]{paid}[/])"
    )
    console.print(f"  Returns: [cyan]{returns}[/]")

    # Finance stats
    console.print("\n[bold]Finance[/]")
    inv_draft = await conn.fetchval(
        "SELECT count(*) FROM invoices WHERE organization_id = $1 AND status = 'draft' AND deleted_at IS NULL",
        oid,
    )
    inv_final = await conn.fetchval(
        "SELECT count(*) FROM invoices WHERE organization_id = $1 AND status = 'finalized' AND deleted_at IS NULL",
        oid,
    )
    inv_paid = await conn.fetchval(
        "SELECT count(*) FROM invoices WHERE organization_id = $1 AND status = 'paid' AND deleted_at IS NULL",
        oid,
    )
    total_invoiced = await conn.fetchval(
        "SELECT COALESCE(SUM(total), 0) FROM invoices WHERE organization_id = $1 AND deleted_at IS NULL",
        oid,
    )
    total_paid_amt = await conn.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE organization_id = $1", oid
    )
    console.print(
        f"  Invoices: draft [yellow]{inv_draft}[/], finalized [cyan]{inv_final}[/], paid [green]{inv_paid}[/]"
    )
    console.print(f"  Total invoiced: [cyan]${total_invoiced:,.2f}[/]  Total paid: [green]${total_paid_amt:,.2f}[/]")

    overdue = await conn.fetch(
        """
        SELECT invoice_number, billing_entity, total, due_date
        FROM invoices
        WHERE organization_id = $1 AND status = 'finalized' AND deleted_at IS NULL
          AND due_date < CURRENT_DATE
        ORDER BY due_date
        LIMIT 10
    """,
        oid,
    )
    if overdue:
        console.print(f"\n  [red]Overdue invoices ({len(overdue)}):[/]")
        for inv in overdue:
            days = (datetime.now(tz=UTC).date() - inv["due_date"]).days
            console.print(
                f"    {inv['invoice_number']} — {inv['billing_entity']} — ${inv['total']:,.2f} — {days}d overdue"
            )

    # Purchasing
    console.print("\n[bold]Purchasing[/]")
    po_ordered = await conn.fetchval(
        "SELECT count(*) FROM purchase_orders WHERE organization_id = $1 AND status = 'ordered'",
        oid,
    )
    po_received = await conn.fetchval(
        "SELECT count(*) FROM purchase_orders WHERE organization_id = $1 AND status = 'received'",
        oid,
    )
    po_closed = await conn.fetchval(
        "SELECT count(*) FROM purchase_orders WHERE organization_id = $1 AND status = 'closed'", oid
    )
    console.print(
        f"  POs: ordered [yellow]{po_ordered}[/], received [cyan]{po_received}[/], closed [green]{po_closed}[/]"
    )

    # Stock transaction volume (last 7 days)
    console.print("\n[bold]Activity (last 7 days)[/]")
    recent_txns = await conn.fetchval(
        """
        SELECT count(*) FROM stock_transactions
        WHERE organization_id = $1 AND created_at > NOW() - INTERVAL '7 days'
    """,
        oid,
    )
    recent_withdrawals = await conn.fetchval(
        """
        SELECT count(*) FROM withdrawals
        WHERE organization_id = $1 AND created_at > NOW() - INTERVAL '7 days'
    """,
        oid,
    )
    console.print(f"  Stock transactions: [cyan]{recent_txns}[/]  Withdrawals: [cyan]{recent_withdrawals}[/]")


# ── tx:audit ─────────────────────────────────────────────────────────────────


async def cmd_tx_audit(conn: asyncpg.Connection, args: argparse.Namespace):
    """Verify stock transaction ledger integrity."""
    org_id = args.org_id
    console.rule(f"[bold]Stock Ledger Audit{f' (org: {org_id[:8]}…)' if org_id else ''}")

    org_filter = "AND organization_id = $1" if org_id else ""
    params: list = [org_id] if org_id else []

    # Check 1: quantity_after = quantity_before + quantity_delta
    bad_math = await conn.fetchval(
        f"""
        SELECT count(*) FROM stock_transactions
        WHERE quantity_after != quantity_before + quantity_delta
        {org_filter}
    """,
        *params,
    )
    _check_print("Ledger math (before + delta = after)", bad_math == 0, bad_math)

    # Check 2: Final SKU quantity matches last stock transaction
    mismatches = await conn.fetch(
        f"""
        WITH latest AS (
            SELECT DISTINCT ON (sku) sku, quantity_after
            FROM stock_transactions
            WHERE 1=1 {org_filter}
            ORDER BY sku, created_at DESC
        )
        SELECT s.sku, s.quantity AS sku_qty, l.quantity_after AS ledger_qty
        FROM skus s
        JOIN latest l ON l.sku = s.sku
        WHERE s.quantity != l.quantity_after AND s.deleted_at IS NULL
        {org_filter.replace("organization_id", "s.organization_id") if org_filter else ""}
        LIMIT 20
    """,
        *params,
    )

    if mismatches:
        console.print(f"  [red]✗[/] SKU qty vs ledger — [red]{len(mismatches)} mismatches[/]:")
        for m in mismatches[:10]:
            console.print(f"    {m['sku']}: SKU={m['sku_qty']} ledger={m['ledger_qty']}")
    else:
        console.print("  [green]✓[/] SKU quantities match latest ledger entries")

    # Check 3: Gaps in ledger (same SKU, non-contiguous before/after)
    gaps = await conn.fetchval(
        f"""
        WITH ordered AS (
            SELECT sku, quantity_before, quantity_after,
                   LAG(quantity_after) OVER (PARTITION BY sku ORDER BY created_at) AS prev_after
            FROM stock_transactions
            WHERE 1=1 {org_filter}
        )
        SELECT count(*) FROM ordered
        WHERE prev_after IS NOT NULL AND quantity_before != prev_after
    """,
        *params,
    )
    _check_print("Ledger continuity (no gaps)", gaps == 0, gaps)

    # Check 4: Withdrawal totals vs withdrawal_items sum
    wtotal_mismatches = await conn.fetchval(
        f"""
        SELECT count(*) FROM withdrawals w
        JOIN (
            SELECT withdrawal_id, ROUND(SUM(amount)::numeric, 2) AS item_total
            FROM withdrawal_items GROUP BY withdrawal_id
        ) wi ON wi.withdrawal_id = w.id
        WHERE ABS(w.subtotal - wi.item_total) > 0.01
        {org_filter.replace("organization_id", "w.organization_id") if org_filter else ""}
    """,
        *params,
    )
    _check_print("Withdrawal subtotals match line items", wtotal_mismatches == 0, wtotal_mismatches)

    console.print()


def _check_print(name: str, ok: bool, count: int):
    if ok:
        console.print(f"  [green]✓[/] {name}")
    else:
        console.print(f"  [red]✗[/] {name} — [red]{count} issues[/]")


# ── tx:recent ────────────────────────────────────────────────────────────────


async def cmd_tx_recent(conn: asyncpg.Connection, args: argparse.Namespace):
    """Show recent stock transactions."""
    org_id = args.org_id
    limit = getattr(args, "limit", 20) or 20
    console.rule("[bold]Recent Stock Transactions")

    org_filter = "AND organization_id = $1" if org_id else ""
    params: list = [org_id] if org_id else []

    rows = await conn.fetch(
        f"""
        SELECT sku, product_name, quantity_delta, quantity_before, quantity_after,
               unit, transaction_type, reason, user_name, created_at
        FROM stock_transactions
        WHERE 1=1 {org_filter}
        ORDER BY created_at DESC
        LIMIT {limit}
    """,
        *params,
    )

    if not rows:
        console.print("[yellow]No transactions found.[/]")
        return

    t = Table(show_lines=False)
    t.add_column("Time", style="dim", max_width=16)
    t.add_column("SKU", style="cyan", max_width=14)
    t.add_column("Product", max_width=25)
    t.add_column("Delta", justify="right")
    t.add_column("Before→After", justify="right")
    t.add_column("Type", style="dim")
    t.add_column("User", style="dim", max_width=12)

    for r in rows:
        delta = r["quantity_delta"]
        delta_style = "green" if delta > 0 else "red" if delta < 0 else "dim"
        t.add_row(
            r["created_at"].strftime("%m-%d %H:%M"),
            r["sku"] or "—",
            (r["product_name"] or "—")[:25],
            f"[{delta_style}]{delta:+.1f}[/]",
            f"{r['quantity_before']:.0f}→{r['quantity_after']:.0f}",
            r["transaction_type"] or "—",
            (r["user_name"] or "—")[:12],
        )

    console.print(t)


# ── Main ─────────────────────────────────────────────────────────────────────

COMMANDS = {
    "db:status": cmd_db_status,
    "db:check": cmd_db_check,
    "tenant:list": cmd_tenant_list,
    "tenant:health": cmd_tenant_health,
    "tx:audit": cmd_tx_audit,
    "tx:recent": cmd_tx_recent,
}


def main():
    parser = argparse.ArgumentParser(
        prog="ops",
        description="SKU-Ops terminal observability",
    )
    parser.add_argument(
        "command",
        choices=list(COMMANDS.keys()),
        help="Command to run",
    )
    parser.add_argument("org_id", nargs="?", default=None, help="Organization ID or slug (optional)")
    parser.add_argument("--limit", type=int, default=20, help="Row limit for tx:recent")
    parser.add_argument("--db-url", default=None, help="Override DATABASE_URL")

    args = parser.parse_args()

    db_url = args.db_url or _resolve_db_url()

    parsed = urlparse(db_url)
    console.print(f"[dim]→ {parsed.hostname}:{parsed.port or 5432}{parsed.path}[/]\n")

    async def run():
        conn = await get_conn(db_url)
        try:
            await COMMANDS[args.command](conn, args)
        finally:
            await conn.close()

    asyncio.run(run())


if __name__ == "__main__":
    main()
