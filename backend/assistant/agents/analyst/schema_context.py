"""Schema introspection for the analyst agent.

Parses CREATE TABLE DDL from all context schema.py files at import time
and builds a structured catalog the LLM can query for table/column info.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Structured schema types ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    is_pk: bool


@dataclass(frozen=True)
class ForeignKey:
    column: str
    ref_table: str
    ref_column: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    context: str
    columns: tuple[ColumnInfo, ...]
    foreign_keys: tuple[ForeignKey, ...]
    has_org_id: bool


# ── DDL parsing ──────────────────────────────────────────────────────────────

_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*)\)",
    re.IGNORECASE | re.DOTALL,
)

_FK_RE = re.compile(
    r"REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
    re.IGNORECASE,
)


def _parse_ddl(ddl: str, context: str) -> TableInfo | None:
    """Parse a single CREATE TABLE DDL string into a TableInfo."""
    m = _TABLE_RE.search(ddl)
    if not m:
        return None

    table_name = m.group(1)
    body = m.group(2)

    columns: list[ColumnInfo] = []
    foreign_keys: list[ForeignKey] = []
    pk_columns: set[str] = set()
    has_org_id = False

    for raw_line in body.split(","):
        line = raw_line.strip()
        if not line:
            continue

        upper = line.upper()

        if upper.startswith("PRIMARY KEY"):
            pk_match = re.search(r"\(([^)]+)\)", line)
            if pk_match:
                pk_columns.update(c.strip() for c in pk_match.group(1).split(","))
            continue

        if upper.startswith(("UNIQUE", "CHECK", "CONSTRAINT", "FOREIGN KEY")):
            continue

        col_match = re.match(r"(\w+)\s+(.+)", line)
        if not col_match:
            continue

        col_name = col_match.group(1)
        rest = col_match.group(2)

        col_upper = col_name.upper()
        if col_upper in ("PRIMARY", "UNIQUE", "CHECK", "CONSTRAINT", "FOREIGN"):
            continue

        col_type = rest.split()[0] if rest.split() else "TEXT"
        rest_upper = rest.upper()
        nullable = "NOT NULL" not in rest_upper
        is_pk = "PRIMARY KEY" in rest_upper

        fk_match = _FK_RE.search(rest)
        if fk_match:
            foreign_keys.append(ForeignKey(col_name, fk_match.group(1), fk_match.group(2)))

        if col_name in ("organization_id", "org_id"):
            has_org_id = True

        columns.append(ColumnInfo(col_name, col_type, nullable, is_pk))

    for col in columns:
        if col.name in pk_columns:
            idx = columns.index(col)
            columns[idx] = ColumnInfo(col.name, col.type, col.nullable, True)

    return TableInfo(
        name=table_name,
        context=context,
        columns=tuple(columns),
        foreign_keys=tuple(foreign_keys),
        has_org_id=has_org_id,
    )


# ── Build the catalog at import time ─────────────────────────────────────────


def _build_catalog() -> dict[str, TableInfo]:
    from shared.infrastructure.full_schema import TABLES_BY_CONTEXT

    catalog: dict[str, TableInfo] = {}
    for ctx_name, tables in TABLES_BY_CONTEXT.items():
        for ddl in tables:
            info = _parse_ddl(ddl, ctx_name)
            if info:
                catalog[info.name] = info
    return catalog


_catalog: dict[str, TableInfo] | None = None


def _get_catalog() -> dict[str, TableInfo]:
    global _catalog
    if _catalog is None:
        _catalog = _build_catalog()
    return _catalog


# ── Key relationships (hand-curated for accuracy) ───────────────────────────

_RELATIONSHIPS = """
## Key Relationships (JOIN paths)
- withdrawals.job_id -> jobs.id (withdrawal for a job)
- withdrawals.billing_entity_id -> billing_entities.id
- withdrawals.contractor_id -> users.id (contractor user)
- withdrawal_items.withdrawal_id -> withdrawals.id
- withdrawal_items.product_id -> skus.id
- invoice_withdrawals links invoices.id <-> withdrawals.id (many-to-many)
- invoice_line_items.invoice_id -> invoices.id
- invoice_line_items.job_id -> jobs.id (optional)
- invoices.billing_entity_id -> billing_entities.id
- payments.invoice_id -> invoices.id
- payment_withdrawals links payments.id <-> withdrawals.id (many-to-many)
- credit_notes.invoice_id -> invoices.id
- credit_notes.return_id -> returns.id
- returns.withdrawal_id -> withdrawals.id
- return_items.return_id -> returns.id
- skus.product_id -> products.id
- skus.category_id -> departments.id (department)
- products.category_id -> departments.id
- vendor_items.vendor_id -> vendors.id
- vendor_items.sku_id -> skus.id
- purchase_orders.vendor_id -> vendors.id
- purchase_order_items.po_id -> purchase_orders.id
- purchase_order_items.product_id -> skus.id
- jobs.billing_entity_id -> billing_entities.id
- financial_ledger: dimensions are department, job_id, billing_entity_id, contractor_id, product_id, vendor_name
- stock_transactions.product_id -> skus.id (reference_id + reference_type for traceability)
"""


# ── Public API ───────────────────────────────────────────────────────────────

# Tables not useful for business analysis
_EXCLUDED_TABLES = frozenset(
    {
        "refresh_tokens",
        "oauth_states",
        "processed_events",
        "sku_counters",
        "invoice_counters",
        "org_settings",
        "memory_artifacts",
        "agent_runs",
        "embeddings",
        "audit_log",
    }
)


def format_overview() -> str:
    """Condensed overview of all analyst-relevant tables (~2KB).

    Returns table names with column names only — enough for query planning.
    """
    catalog = _get_catalog()
    lines = ["# Database Schema Overview\n"]

    current_ctx = ""
    for table in catalog.values():
        if table.name in _EXCLUDED_TABLES:
            continue
        if table.context != current_ctx:
            current_ctx = table.context
            lines.append(f"\n## {current_ctx.title()} Context")
        col_names = ", ".join(c.name for c in table.columns)
        org_marker = " [org-scoped]" if table.has_org_id else ""
        lines.append(f"- **{table.name}**{org_marker}: {col_names}")

    lines.append(_RELATIONSHIPS)
    return "\n".join(lines)


def format_detail(table_names: list[str]) -> str:
    """Full column detail for specific tables — types, PKs, FKs, nullability."""
    catalog = _get_catalog()
    parts: list[str] = []

    for name in table_names:
        info = catalog.get(name)
        if not info:
            parts.append(
                f"Table '{name}' not found. Available: {', '.join(sorted(catalog.keys()))}"
            )
            continue

        lines = [f"## {info.name} ({info.context} context)"]
        lines.append("| Column | Type | PK | Nullable | FK |")
        lines.append("|--------|------|----|----------|----|")

        fk_map = {fk.column: fk for fk in info.foreign_keys}
        for col in info.columns:
            fk = fk_map.get(col.name)
            fk_str = f"{fk.ref_table}({fk.ref_column})" if fk else ""
            lines.append(
                f"| {col.name} | {col.type} | {'Y' if col.is_pk else ''} "
                f"| {'Y' if col.nullable else ''} | {fk_str} |"
            )

        if info.has_org_id:
            lines.append("\n*Org-scoped: filter by organization_id = $1*")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)
