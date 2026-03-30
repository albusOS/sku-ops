"""Load default units of measure seed SQL (single source: supabase/seeds/02_units_of_measure.sql)."""

from pathlib import Path


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
        if org_id != "supply-yard":
            stmt = stmt.replace("supply-yard", org_id)
        out.append(stmt)
    return out
