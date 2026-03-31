"""Load default units of measure seed SQL (single source: supabase/seeds/02_units_of_measure.sql)."""

from pathlib import Path

from shared.kernel.constants import DEFAULT_ORG_ID


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def uom_seed_sql(org_id: str) -> list[str]:
    """Return INSERT statements for default UOM rows, scoped to org_id.

    Canonical definitions live in ``supabase/seeds/02_units_of_measure.sql``.
    """
    path = _repo_root() / "supabase" / "seeds" / "02_units_of_measure.sql"
    text = path.read_text()
    out: list[str] = []
    for line in text.splitlines():
        stmt = line.strip()
        if not stmt or stmt.startswith("--"):
            continue
        if org_id != DEFAULT_ORG_ID:
            stmt = stmt.replace(DEFAULT_ORG_ID, org_id)
        out.append(stmt)
    return out
