"""Unit tests for the data analyst agent — SQL validation, schema context, and wiring."""

import pytest

from assistant.agents.analyst.schema_context import (
    _parse_ddl,
    format_detail,
    format_overview,
)
from assistant.agents.analyst.sql_executor import (
    AnalystQueryError,
    _ensure_limit,
    _validate_org_filter,
    _validate_sql,
)

# ── SQL validation ───────────────────────────────────────────────────────────


class TestSQLValidation:
    """Validates that the SQL sandbox rejects dangerous queries."""

    def test_select_allowed(self):
        _validate_sql("SELECT id, name FROM skus WHERE organization_id = $1")

    def test_with_cte_allowed(self):
        _validate_sql(
            "WITH recent AS (SELECT * FROM withdrawals WHERE organization_id = $1) "
            "SELECT * FROM recent LIMIT 100"
        )

    def test_empty_rejected(self):
        with pytest.raises(AnalystQueryError, match="Empty query"):
            _validate_sql("")

    def test_insert_rejected(self):
        with pytest.raises(AnalystQueryError, match="INSERT"):
            _validate_sql("INSERT INTO skus (id) VALUES ('x')")

    def test_update_rejected(self):
        with pytest.raises(AnalystQueryError, match="UPDATE"):
            _validate_sql("UPDATE skus SET name = 'x' WHERE id = '1'")

    def test_delete_rejected(self):
        with pytest.raises(AnalystQueryError, match="DELETE"):
            _validate_sql("DELETE FROM skus WHERE id = '1'")

    def test_drop_rejected(self):
        with pytest.raises(AnalystQueryError, match="DROP"):
            _validate_sql("DROP TABLE skus")

    def test_alter_rejected(self):
        with pytest.raises(AnalystQueryError, match="ALTER"):
            _validate_sql("ALTER TABLE skus ADD COLUMN foo TEXT")

    def test_truncate_rejected(self):
        with pytest.raises(AnalystQueryError, match="TRUNCATE"):
            _validate_sql("TRUNCATE TABLE skus")

    def test_grant_rejected(self):
        with pytest.raises(AnalystQueryError, match="GRANT"):
            _validate_sql("GRANT ALL ON skus TO public")

    def test_copy_rejected(self):
        with pytest.raises(AnalystQueryError, match="COPY"):
            _validate_sql("COPY skus TO '/tmp/out.csv'")

    def test_create_rejected(self):
        with pytest.raises(AnalystQueryError, match="CREATE"):
            _validate_sql("CREATE TABLE evil (id TEXT)")

    def test_set_rejected(self):
        with pytest.raises(AnalystQueryError, match="SET"):
            _validate_sql("SET role = 'superuser'")

    def test_multi_statement_rejected(self):
        with pytest.raises(AnalystQueryError, match="Multi-statement"):
            _validate_sql("SELECT 1; SELECT 2")

    def test_non_select_prefix_rejected(self):
        with pytest.raises(AnalystQueryError, match="Only SELECT"):
            _validate_sql("EXPLAIN SELECT 1")


class TestOrgFilter:
    """Validates that org isolation is enforced."""

    def test_dollar_one_required(self):
        with pytest.raises(AnalystQueryError, match="organization_id"):
            _validate_org_filter("SELECT * FROM skus")

    def test_dollar_one_present(self):
        _validate_org_filter("SELECT * FROM skus WHERE organization_id = $1")


class TestLimitInjection:
    """Validates that LIMIT is injected when missing."""

    def test_adds_limit(self):
        result = _ensure_limit("SELECT * FROM skus WHERE organization_id = $1")
        assert "LIMIT 500" in result

    def test_preserves_existing_limit(self):
        sql = "SELECT * FROM skus WHERE organization_id = $1 LIMIT 10"
        result = _ensure_limit(sql)
        assert "LIMIT 500" not in result
        assert "LIMIT 10" in result


# ── Schema context ───────────────────────────────────────────────────────────


class TestDDLParsing:
    """Validates that DDL strings are correctly parsed into TableInfo."""

    def test_simple_table(self):
        ddl = """CREATE TABLE IF NOT EXISTS skus (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            organization_id TEXT
        )"""
        info = _parse_ddl(ddl, "catalog")
        assert info is not None
        assert info.name == "skus"
        assert info.context == "catalog"
        assert info.has_org_id is True
        col_names = [c.name for c in info.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "price" in col_names

    def test_foreign_keys_parsed(self):
        ddl = """CREATE TABLE IF NOT EXISTS vendor_items (
            id TEXT PRIMARY KEY,
            vendor_id TEXT NOT NULL REFERENCES vendors(id),
            sku_id TEXT NOT NULL REFERENCES skus(id),
            cost REAL NOT NULL DEFAULT 0,
            organization_id TEXT
        )"""
        info = _parse_ddl(ddl, "catalog")
        assert info is not None
        fk_cols = [fk.column for fk in info.foreign_keys]
        assert "vendor_id" in fk_cols
        assert "sku_id" in fk_cols
        vendor_fk = next(fk for fk in info.foreign_keys if fk.column == "vendor_id")
        assert vendor_fk.ref_table == "vendors"
        assert vendor_fk.ref_column == "id"

    def test_no_org_id(self):
        ddl = """CREATE TABLE IF NOT EXISTS sku_counters (
            department_code TEXT PRIMARY KEY,
            counter INTEGER NOT NULL DEFAULT 0
        )"""
        info = _parse_ddl(ddl, "catalog")
        assert info is not None
        assert info.has_org_id is False

    def test_invalid_ddl_returns_none(self):
        assert _parse_ddl("NOT A DDL STATEMENT", "test") is None


class TestSchemaFormatting:
    """Validates schema formatting for the LLM."""

    def test_overview_includes_tables(self):
        overview = format_overview()
        assert "skus" in overview
        assert "withdrawals" in overview
        assert "financial_ledger" in overview
        assert "invoices" in overview

    def test_overview_excludes_internal_tables(self):
        overview = format_overview()
        assert "agent_runs" not in overview
        assert "refresh_tokens" not in overview
        assert "embeddings" not in overview

    def test_detail_includes_columns(self):
        detail = format_detail(["skus"])
        assert "price" in detail
        assert "cost" in detail
        assert "quantity" in detail

    def test_detail_unknown_table(self):
        detail = format_detail(["nonexistent_table"])
        assert "not found" in detail

    def test_overview_includes_relationships(self):
        overview = format_overview()
        assert "Relationships" in overview
        assert "withdrawals.job_id" in overview
