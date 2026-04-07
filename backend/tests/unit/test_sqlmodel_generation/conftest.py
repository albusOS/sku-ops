"""Shared fixtures for SQLModel generation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _fixture_text(name: str) -> str:
    return (_FIXTURE_DIR / f"{name}.txt").read_text()


SAMPLE_TS_SINGLE_FK = _fixture_text("sample_ts_single_fk")
SAMPLE_TS_M2M = _fixture_text("sample_ts_m2m")
SAMPLE_TS_M2M_PLUS_DIRECT_FK = _fixture_text("sample_ts_m2m_plus_direct_fk")
SAMPLE_TS_EMPTY_RELS = _fixture_text("sample_ts_empty_rels")
SAMPLE_PYDANTIC_OUTPUT = _fixture_text("sample_pydantic_output")
SAMPLE_SQL_MIGRATION = _fixture_text("sample_sql_migration")


@pytest.fixture
def sample_ts_single_fk():
    return SAMPLE_TS_SINGLE_FK


@pytest.fixture
def sample_ts_m2m():
    return SAMPLE_TS_M2M


@pytest.fixture
def sample_ts_m2m_plus_direct_fk():
    return SAMPLE_TS_M2M_PLUS_DIRECT_FK


@pytest.fixture
def sample_ts_empty_rels():
    return SAMPLE_TS_EMPTY_RELS


@pytest.fixture
def sample_pydantic_output():
    return SAMPLE_PYDANTIC_OUTPUT


@pytest.fixture
def sample_sql_migration(tmp_path):
    migration_file = tmp_path / "001_test.sql"
    migration_file.write_text(SAMPLE_SQL_MIGRATION)
    return tmp_path
