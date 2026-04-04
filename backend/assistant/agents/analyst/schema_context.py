"""Schema introspection for the analyst agent.

Parses CREATE TABLE DDL from declarative ``supabase/schemas`` files (see
``supabase/config.toml`` ``[db.migrations] schema_paths``) at import time
and builds a structured catalog the LLM can query for table/column info.
"""

from __future__ import annotations

import glob
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

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
    r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\)\s*;\s*",
    re.IGNORECASE | re.DOTALL,
)

_FK_RE = re.compile(
    r"REFERENCES\s+(\w+)\s*\(\s*(\w+)\s*\)",
    re.IGNORECASE,
)


def _split_column_definitions(body: str) -> list[str]:
    """Split CREATE TABLE column list on commas not inside parentheses (e.g. REFERENCES)."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth = max(0, depth - 1)
            current.append(char)
        elif char == "," and depth == 0:
            piece = "".join(current).strip()
            if piece:
                parts.append(piece)
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_ddl(ddl: str, context: str) -> TableInfo | None:
    """Parse a single CREATE TABLE DDL string into a TableInfo."""
    stripped = ddl.strip()
    if not stripped.endswith(";"):
        stripped += ";"
    m = _TABLE_RE.search(stripped)
    if not m:
        return None

    table_name = m.group(1)
    body = m.group(2)

    columns: list[ColumnInfo] = []
    foreign_keys: list[ForeignKey] = []
    pk_columns: set[str] = set()
    has_org_id = False

    for raw_line in _split_column_definitions(body):
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


# ── Build the catalog from declarative schema SQL ─────────────────────────────

_TABLE_CONTEXT = {
    "organizations": "shared",
    "users": "shared",
    "refresh_tokens": "shared",
    "oauth_states": "shared",
    "audit_log": "shared",
    "billing_entities": "finance",
    "addresses": "shared",
    "fiscal_periods": "finance",
    "processed_events": "shared",
    "departments": "catalog",
    "units_of_measure": "catalog",
    "vendors": "catalog",
    "products": "catalog",
    "skus": "catalog",
    "vendor_items": "catalog",
    "sku_counters": "catalog",
    "stock_transactions": "inventory",
    "cycle_counts": "inventory",
    "cycle_count_items": "inventory",
    "withdrawals": "operations",
    "material_requests": "operations",
    "material_request_items": "operations",
    "returns": "operations",
    "withdrawal_items": "operations",
    "return_items": "operations",
    "invoices": "finance",
    "invoice_withdrawals": "finance",
    "invoice_line_items": "finance",
    "invoice_counters": "finance",
    "credit_notes": "finance",
    "credit_note_line_items": "finance",
    "payments": "finance",
    "payment_withdrawals": "finance",
    "financial_ledger": "finance",
    "purchase_orders": "purchasing",
    "purchase_order_items": "purchasing",
    "documents": "documents",
    "jobs": "jobs",
    "memory_artifacts": "assistant",
    "agent_runs": "assistant",
    "embeddings": "assistant",
    "org_settings": "finance",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _load_declarative_schema_sql() -> str:
    """Concatenate SQL from ``schema_paths`` (same source Supabase uses for db diff)."""
    supabase_dir = _repo_root() / "supabase"
    config_path = supabase_dir / "config.toml"
    paths: list[Path] = []
    if config_path.is_file():
        with config_path.open("rb") as f:
            cfg = tomllib.load(f)
        raw = cfg.get("db", {}).get("migrations", {}).get("schema_paths", [])
        for entry in raw:
            e = entry.strip()
            if not e:
                continue
            if "*" in e or "?" in e:
                pattern = str(supabase_dir / e.removeprefix("./"))
                paths.extend(Path(p) for p in sorted(glob.glob(pattern)))
            else:
                rel = e.removeprefix("./")
                paths.append(supabase_dir / rel)
    if not paths:
        paths = sorted((supabase_dir / "schemas").glob("??-*-schema.sql"))
    chunks: list[str] = []
    for p in paths:
        if not p.is_file():
            raise RuntimeError(f"Schema file missing for analyst catalog: {p}")
        chunks.append(p.read_text())
    if not chunks:
        raise RuntimeError(
            "No declarative schema SQL found. Set [db.migrations] schema_paths "
            "in supabase/config.toml or add supabase/schemas/??-*-schema.sql."
        )
    return "\n".join(chunks)


def _build_catalog() -> dict[str, TableInfo]:
    sql = _load_declarative_schema_sql()
    catalog: dict[str, TableInfo] = {}
    for table_name, body in _TABLE_RE.findall(sql):
        ddl = f"CREATE TABLE IF NOT EXISTS {table_name} ({body})"
        context = _TABLE_CONTEXT.get(table_name, "shared")
        info = _parse_ddl(ddl, context)
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
- withdrawal_items.sku_id -> skus.id
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
- material_request_items.material_request_id -> material_requests.id
- skus.product_family_id -> products.id (the `products` table stores product families, not individual SKUs)
- skus.category_id -> departments.id (department)
- products.category_id -> departments.id
- vendor_items.vendor_id -> vendors.id
- vendor_items.sku_id -> skus.id
- purchase_orders.vendor_id -> vendors.id
- purchase_order_items.po_id -> purchase_orders.id
- purchase_order_items.sku_id -> skus.id
- jobs.billing_entity_id -> billing_entities.id
- financial_ledger: dimensions are department, job_id, billing_entity_id, contractor_id, sku_id, vendor_name
- stock_transactions.sku_id -> skus.id (reference_id + reference_type for traceability)
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
