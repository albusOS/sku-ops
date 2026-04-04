"""Unit tests for DB boundary helpers."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from shared.infrastructure.db.orm_utils import parse_date_param


def test_parse_date_param_none_and_empty():
    assert parse_date_param(None) is None
    assert parse_date_param("") is None
    assert parse_date_param("   ") is None

def test_parse_date_param_z_suffix_timezone():
    dt = parse_date_param("2026-03-27T04:00:00.000Z")
    assert dt is not None
    assert dt == datetime(2026, 3, 27, 4, 0, 0, tzinfo=UTC)

def test_parse_date_param_offset():
    dt = parse_date_param("2026-04-02T12:30:45-07:00")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4

def test_parse_date_param_naive_date_string():
    dt = parse_date_param("2026-01-15")
    assert dt is not None
    assert dt == datetime.fromisoformat("2026-01-15")

def test_parse_date_param_invalid_raises():
    with pytest.raises(ValueError):
        parse_date_param("not-a-date")
