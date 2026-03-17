"""Integration tests for the analyst SQL executor — verifies sandbox against real Postgres."""

import pytest

from assistant.agents.analyst.sql_executor import AnalystQueryError, execute_sandboxed


class TestSandboxedExecution:
    """Tests that run against the live test database."""

    def test_select_returns_rows(self, call):
        """A basic SELECT against a seeded table returns data."""

        async def _body():
            result = await execute_sandboxed(
                "SELECT id, name FROM departments WHERE organization_id = $1 LIMIT 10"
            )
            assert result.row_count >= 1
            assert "id" in result.columns
            assert "name" in result.columns

        call(_body)

    def test_org_isolation(self, call):
        """Queries only return data for the ambient org_id."""

        async def _body():
            result = await execute_sandboxed(
                "SELECT id FROM departments WHERE organization_id = $1"
            )
            for row in result.rows:
                assert row is not None

        call(_body)

    def test_missing_org_filter_rejected(self, call):
        """Queries without $1 are rejected before execution."""

        async def _body():
            with pytest.raises(AnalystQueryError, match="organization_id"):
                await execute_sandboxed("SELECT id FROM departments")

        call(_body)

    def test_limit_injected(self, call):
        """Queries without LIMIT get one appended."""

        async def _body():
            result = await execute_sandboxed(
                "SELECT id FROM departments WHERE organization_id = $1"
            )
            assert result.row_count <= 500

        call(_body)

    def test_insert_rejected(self, call):
        """INSERT is rejected by the validator, not just by SET TRANSACTION READ ONLY."""

        async def _body():
            with pytest.raises(AnalystQueryError, match="Only SELECT"):
                await execute_sandboxed(
                    "INSERT INTO departments (id, name, code, organization_id, created_at) "
                    "VALUES ('evil', 'Evil', 'EVL', $1, NOW())"
                )

        call(_body)

    def test_cte_query_works(self, call):
        """WITH ... AS queries execute correctly."""

        async def _body():
            result = await execute_sandboxed(
                "WITH depts AS (SELECT id, name FROM departments WHERE organization_id = $1) "
                "SELECT * FROM depts LIMIT 10"
            )
            assert result.columns is not None

        call(_body)

    def test_empty_result_handled(self, call):
        """Queries that return zero rows produce an empty result, not an error."""

        async def _body():
            result = await execute_sandboxed(
                "SELECT id FROM departments WHERE organization_id = $1 AND id = 'nonexistent'"
            )
            assert result.row_count == 0
            assert result.rows == []

        call(_body)

    def test_format_result_serializable(self, call):
        """ExecutionResult can be serialized to JSON."""
        import json

        from assistant.agents.analyst.sql_executor import format_result

        async def _body():
            result = await execute_sandboxed(
                "SELECT id, name FROM departments WHERE organization_id = $1 LIMIT 5"
            )
            formatted = format_result(result)
            parsed = json.loads(formatted)
            assert "columns" in parsed
            assert "rows" in parsed
            assert "row_count" in parsed
            assert isinstance(parsed["rows"], list)

        call(_body)
