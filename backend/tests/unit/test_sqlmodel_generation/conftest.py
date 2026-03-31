"""Shared fixtures for SQLModel generation tests."""

from __future__ import annotations

import pytest

SAMPLE_TS_SINGLE_FK = """
export type Database = {
  public: {
    Tables: {
      departments: {
        Row: {
          id: string
          name: string
          organization_id: string | null
        }
        Insert: {
          id: string
          name: string
          organization_id?: string | null
        }
        Update: {
          id?: string
          name?: string
          organization_id?: string | null
        }
        Relationships: []
      }
      products: {
        Row: {
          id: string
          name: string
          category_id: string
        }
        Insert: {
          id: string
          name: string
          category_id: string
        }
        Update: {
          id?: string
          name?: string
          category_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "products_category_id_fkey"
            columns: ["category_id"]
            isOneToOne: false
            referencedRelation: "departments"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {}
    Functions: {}
    Enums: {}
    CompositeTypes: {}
  }
}
"""

SAMPLE_TS_M2M = """
export type Database = {
  public: {
    Tables: {
      invoices: {
        Row: {
          id: string
          total: number
        }
        Insert: {
          id: string
          total: number
        }
        Update: {
          id?: string
          total?: number
        }
        Relationships: []
      }
      withdrawals: {
        Row: {
          id: string
          amount: number
        }
        Insert: {
          id: string
          amount: number
        }
        Update: {
          id?: string
          amount?: number
        }
        Relationships: []
      }
      invoice_withdrawals: {
        Row: {
          invoice_id: string
          withdrawal_id: string
        }
        Insert: {
          invoice_id: string
          withdrawal_id: string
        }
        Update: {
          invoice_id?: string
          withdrawal_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "invoice_withdrawals_invoice_id_fkey"
            columns: ["invoice_id"]
            isOneToOne: false
            referencedRelation: "invoices"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "invoice_withdrawals_withdrawal_id_fkey"
            columns: ["withdrawal_id"]
            isOneToOne: false
            referencedRelation: "withdrawals"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {}
    Functions: {}
    Enums: {}
    CompositeTypes: {}
  }
}
"""

SAMPLE_TS_EMPTY_RELS = """
export type Database = {
  public: {
    Tables: {
      simple_table: {
        Row: {
          id: string
          name: string
        }
        Insert: {
          id: string
          name: string
        }
        Update: {
          id?: string
          name?: string
        }
        Relationships: []
      }
    }
    Views: {}
    Functions: {}
    Enums: {}
    CompositeTypes: {}
  }
}
"""

SAMPLE_PYDANTIC_OUTPUT = """
from __future__ import annotations
import datetime
from pydantic import BaseModel, Field

class PublicDepartments(BaseModel):
    id: str = Field(alias="id")
    name: str = Field(alias="name")
    organization_id: str | None = Field(alias="organization_id")

class PublicDepartmentsInsert(TypedDict):
    id: str
    name: str

class PublicDepartmentsUpdate(TypedDict):
    id: str

class PublicProducts(BaseModel):
    category_id: str = Field(alias="category_id")
    id: str = Field(alias="id")
    name: str = Field(alias="name")

class PublicProductsInsert(TypedDict):
    category_id: str
    id: str

class PublicProductsUpdate(TypedDict):
    category_id: str
"""

SAMPLE_SQL_MIGRATION = """
CREATE TABLE IF NOT EXISTS departments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category_id TEXT NOT NULL REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    total NUMERIC(18,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id TEXT PRIMARY KEY,
    amount NUMERIC(18,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_withdrawals (
    invoice_id TEXT NOT NULL REFERENCES invoices(id),
    withdrawal_id TEXT NOT NULL REFERENCES withdrawals(id),
    PRIMARY KEY (invoice_id, withdrawal_id)
);
"""


@pytest.fixture
def sample_ts_single_fk():
    return SAMPLE_TS_SINGLE_FK


@pytest.fixture
def sample_ts_m2m():
    return SAMPLE_TS_M2M


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
