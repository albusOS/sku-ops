"""Unit tests for the TypeScript relationship parser."""

from __future__ import annotations

from backend.scripts.supabase_type_generation.supabase_ts_relationship_parser import (
    parse_ts_relationships,
)


class TestSingleFK:
    def test_extracts_single_fk(self, sample_ts_single_fk):
        result = parse_ts_relationships(sample_ts_single_fk, "public")
        assert len(result.foreign_keys) == 1
        fk = result.foreign_keys[0]
        assert fk.source_table == "products"
        assert fk.source_columns == ["category_id"]
        assert fk.target_table == "departments"
        assert fk.target_columns == ["id"]
        assert fk.is_one_to_one is False
        assert fk.constraint_name == "products_category_id_fkey"

    def test_no_link_tables(self, sample_ts_single_fk):
        result = parse_ts_relationships(sample_ts_single_fk, "public")
        assert len(result.link_tables) == 0


class TestEmptyRelationships:
    def test_empty_rels_returns_no_fks(self, sample_ts_empty_rels):
        result = parse_ts_relationships(sample_ts_empty_rels, "public")
        assert len(result.foreign_keys) == 0
        assert len(result.link_tables) == 0

    def test_schema_name_propagated(self, sample_ts_empty_rels):
        result = parse_ts_relationships(sample_ts_empty_rels, "public")
        assert result.schema == "public"


class TestM2MLinkTable:
    def test_detects_link_table(self, sample_ts_m2m):
        result = parse_ts_relationships(sample_ts_m2m, "public")
        assert "invoice_withdrawals" in result.link_tables

    def test_extracts_both_fks(self, sample_ts_m2m):
        result = parse_ts_relationships(sample_ts_m2m, "public")
        fk_sources = {fk.source_table for fk in result.foreign_keys}
        assert "invoice_withdrawals" in fk_sources
        iw_fks = [fk for fk in result.foreign_keys if fk.source_table == "invoice_withdrawals"]
        assert len(iw_fks) == 2
        targets = {fk.target_table for fk in iw_fks}
        assert targets == {"invoices", "withdrawals"}


class TestMultipleFKs:
    def test_table_with_two_fks(self):
        ts_content = '\nexport type Database = {\n  public: {\n    Tables: {\n      skus: {\n        Row: {\n          id: string\n          category_id: string\n          product_family_id: string\n        }\n        Relationships: [\n          {\n            foreignKeyName: "skus_category_id_fkey"\n            columns: ["category_id"]\n            isOneToOne: false\n            referencedRelation: "departments"\n            referencedColumns: ["id"]\n          },\n          {\n            foreignKeyName: "skus_product_family_id_fkey"\n            columns: ["product_family_id"]\n            isOneToOne: false\n            referencedRelation: "products"\n            referencedColumns: ["id"]\n          },\n        ]\n      }\n    }\n    Views: {}\n    Functions: {}\n    Enums: {}\n    CompositeTypes: {}\n  }\n}\n'
        result = parse_ts_relationships(ts_content, "public")
        assert len(result.foreign_keys) == 2
        targets = {fk.target_table for fk in result.foreign_keys}
        assert targets == {"departments", "products"}


class TestIsOneToOne:
    def test_propagates_one_to_one_flag(self):
        ts_content = '\nexport type Database = {\n  public: {\n    Tables: {\n      user_profiles: {\n        Row: {\n          user_id: string\n          bio: string\n        }\n        Relationships: [\n          {\n            foreignKeyName: "user_profiles_user_id_fkey"\n            columns: ["user_id"]\n            isOneToOne: true\n            referencedRelation: "users"\n            referencedColumns: ["id"]\n          },\n        ]\n      }\n    }\n    Views: {}\n    Functions: {}\n    Enums: {}\n    CompositeTypes: {}\n  }\n}\n'
        result = parse_ts_relationships(ts_content, "public")
        assert len(result.foreign_keys) == 1
        assert result.foreign_keys[0].is_one_to_one is True


class TestNonexistentSchema:
    def test_returns_empty_for_unknown_schema(self, sample_ts_single_fk):
        result = parse_ts_relationships(sample_ts_single_fk, "nonexistent")
        assert len(result.foreign_keys) == 0
        assert result.schema == "nonexistent"
