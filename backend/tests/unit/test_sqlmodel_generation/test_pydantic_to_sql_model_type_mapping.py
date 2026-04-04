"""Unit tests for the Pydantic-to-SQLModel type mapping."""
from __future__ import annotations

from backend.scripts.supabase_type_generation.pydantic_to_sql_model_type_mapping import (
    map_pydantic_type,
)


class TestBasicTypes:

    def test_str(self):
        result = map_pydantic_type("str", is_optional=False)
        assert result.python_type == "str"
        assert result.sa_type is None

    def test_int(self):
        result = map_pydantic_type("int", is_optional=False)
        assert result.python_type == "int"
        assert result.sa_type is None

    def test_float(self):
        result = map_pydantic_type("float", is_optional=False)
        assert result.python_type == "float"
        assert result.sa_type == "Float"

    def test_bool(self):
        result = map_pydantic_type("bool", is_optional=False)
        assert result.python_type == "bool"
        assert result.sa_type is None

class TestOptionalTypes:

    def test_optional_str(self):
        result = map_pydantic_type("str | None", is_optional=True)
        assert result.python_type == "str | None"

    def test_optional_int(self):
        result = map_pydantic_type("int", is_optional=True)
        assert result.python_type == "int | None"

    def test_optional_float(self):
        result = map_pydantic_type("float | None", is_optional=True)
        assert result.python_type == "float | None"
        assert result.sa_type == "Float"

class TestDatetimeTypes:

    def test_datetime(self):
        result = map_pydantic_type("datetime.datetime", is_optional=False)
        assert result.python_type == "datetime.datetime"
        assert result.sa_type == "DateTime(timezone=True)"
        assert "DateTime" in result.needs_import

    def test_optional_datetime(self):
        result = map_pydantic_type("datetime.datetime | None", is_optional=True)
        assert result.python_type == "datetime.datetime | None"
        assert result.sa_type == "DateTime(timezone=True)"

    def test_date(self):
        result = map_pydantic_type("datetime.date", is_optional=False)
        assert result.python_type == "datetime.date"
        assert result.sa_type == "Date"

class TestJsonTypes:

    def test_json_any(self):
        result = map_pydantic_type("Json[Any]", is_optional=False)
        assert "dict" in result.python_type
        assert result.sa_type == "JSONB"

    def test_optional_json(self):
        result = map_pydantic_type("Optional[Json[Any]]", is_optional=True)
        assert result.sa_type == "JSONB"

    def test_json_bare(self):
        result = map_pydantic_type("Json", is_optional=False)
        assert result.sa_type == "JSONB"

class TestUuidTypes:

    def test_uuid(self):
        result = map_pydantic_type("uuid.UUID", is_optional=False)
        assert result.python_type == "uuid.UUID"
        assert result.sa_type == "PG_UUID(as_uuid=True)"
        assert result.needs_import == {"PG_UUID"}

    def test_optional_uuid(self):
        result = map_pydantic_type("uuid.UUID | None", is_optional=True)
        assert result.python_type == "uuid.UUID | None"
        assert result.sa_type == "PG_UUID(as_uuid=True)"
