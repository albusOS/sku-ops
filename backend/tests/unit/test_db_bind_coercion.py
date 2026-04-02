"""Unit tests for asyncpg-compatible bind coercion in raw SQL layer."""

from datetime import UTC, datetime
from uuid import UUID

from shared.infrastructure.db.services.raw_sql import (
    coerce_bind_value,
    normalize_param_tuple,
    normalize_params,
    normalize_sql_value,
)


def test_coerce_iso_z_to_utc_datetime():
    out = coerce_bind_value("2026-03-24T04:00:00.000Z")
    assert isinstance(out, datetime)
    assert out.tzinfo is not None
    assert out == datetime(2026, 3, 24, 4, 0, 0, tzinfo=UTC)


def test_coerce_date_only():
    out = coerce_bind_value("2026-03-24")
    assert isinstance(out, datetime)
    assert out.year == 2026 and out.month == 3 and out.day == 24


def test_coerce_offset_string():
    out = coerce_bind_value("2026-03-24T04:00:00+05:00")
    assert isinstance(out, datetime)
    assert out.utcoffset() is not None


def test_non_iso_string_unchanged():
    assert coerce_bind_value("supply-yard") == "supply-yard"
    assert coerce_bind_value("INV-00001") == "INV-00001"
    assert coerce_bind_value("") == ""
    assert coerce_bind_value("abc-01-01") == "abc-01-01"


def test_non_string_unchanged():
    assert coerce_bind_value(42) == 42
    assert coerce_bind_value(None) is None
    dt = datetime(2025, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert coerce_bind_value(dt) is dt


def test_invalid_iso_date_fallback():
    assert coerce_bind_value("2026-13-45T00:00:00Z") == "2026-13-45T00:00:00Z"


def test_normalize_params_empty():
    assert normalize_params(()) is None
    assert normalize_params([]) is None


def test_normalize_params_mixed():
    tup = normalize_param_tuple(
        ("supply-yard", "2026-03-24T04:00:00.000Z", 1),
    )
    assert tup[0] == "supply-yard"
    assert isinstance(tup[1], datetime)
    assert tup[2] == 1

    out = normalize_params(["2026-01-01", "x"])
    assert isinstance(out[0], datetime)
    assert out[1] == "x"


def test_coerce_result_uuid_to_string():
    value = UUID("0195f2c0-89aa-7d6d-bb34-7f3b3f69c001")

    assert normalize_sql_value(value) == "0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"


def test_coerce_result_nested_uuid_structures():
    value = {
        "id": UUID("0195f2c0-89aa-7d6d-bb34-7f3b3f69c001"),
        "children": [UUID("0195f2c0-89ab-7a10-8a01-000000000001")],
    }

    assert normalize_sql_value(value) == {
        "id": "0195f2c0-89aa-7d6d-bb34-7f3b3f69c001",
        "children": ["0195f2c0-89ab-7a10-8a01-000000000001"],
    }
