"""End-to-end tests for the SQLModel code generation pipeline."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import textwrap

from backend.scripts.supabase_type_generation.supabase_pydantic_models_to_sql_models import (
    generate_sqlmodel_code,
)
from backend.scripts.supabase_type_generation.supabase_ts_relationship_parser import (
    parse_ts_relationships,
)
from backend.scripts.supabase_type_generation.supabase_types_to_pydantic_models import (
    parse_pydantic_types,
)


class TestSimpleModelGeneration:

    def test_generates_valid_python(self, sample_pydantic_output, sample_ts_empty_rels):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "simple_table"): ["id"]}
        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)
        tree = ast.parse(code)
        assert tree is not None

    def test_does_not_emit_future_annotations_import(self, sample_pydantic_output, sample_ts_empty_rels):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {("public", "departments"): ["id"]}
        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)
        assert "from __future__ import annotations" not in code

    def test_simple_model_fields(self, sample_pydantic_output, sample_ts_empty_rels):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {("public", "departments"): ["id"]}
        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)
        assert "class Departments(SQLModel, table=True):" in code
        assert '__tablename__ = "departments"' in code
        assert "primary_key=True" in code
        assert "id: str" in code

class TestOneToManyGeneration:

    def test_generates_fk_field(self, sample_pydantic_output, sample_ts_single_fk):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "products"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        assert 'foreign_key="public.departments.id"' in code

    def test_generates_relationship_attrs(self, sample_pydantic_output, sample_ts_single_fk):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "products"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        assert "Relationship(back_populates=" in code

    def test_back_populates_symmetry(self, sample_pydantic_output, sample_ts_single_fk):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "products"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        assert 'back_populates="products"' in code
        assert 'back_populates="category"' in code

    def test_generated_one_to_many_code_configures_mappers(self, sample_pydantic_output, sample_ts_single_fk):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "products"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        script = f"\n{code}\n\nfrom sqlalchemy.orm import configure_mappers\n\nconfigure_mappers()\n"
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr

class TestM2MGeneration:

    def test_generates_link_model(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicInvoices(BaseModel):\n                id: str = Field(alias="id")\n                total: float = Field(alias="total")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                amount: float = Field(alias="amount")\n\n            class PublicInvoiceWithdrawals(BaseModel):\n                invoice_id: str = Field(alias="invoice_id")\n                withdrawal_id: str = Field(alias="withdrawal_id")\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {("public", "invoices"): ["id"], ("public", "withdrawals"): ["id"], ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        assert "class InvoiceWithdrawals(SQLModel, table=True):" in code
        assert "link_model=InvoiceWithdrawals" in code

    def test_m2m_bidirectional(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicInvoices(BaseModel):\n                id: str = Field(alias="id")\n                total: float = Field(alias="total")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                amount: float = Field(alias="amount")\n\n            class PublicInvoiceWithdrawals(BaseModel):\n                invoice_id: str = Field(alias="invoice_id")\n                withdrawal_id: str = Field(alias="withdrawal_id")\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {("public", "invoices"): ["id"], ("public", "withdrawals"): ["id"], ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        assert 'back_populates="invoices"' in code
        assert 'back_populates="withdrawals"' in code

class TestRelationshipDisambiguation:

    def test_deduped_relationship_name_stays_in_sync_for_back_populates(self):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicBillingEntities(BaseModel):\n                id: str = Field(alias="id")\n                name: str = Field(alias="name")\n\n            class PublicCreditNotes(BaseModel):\n                id: str = Field(alias="id")\n                billing_entity: str = Field(alias="billing_entity")\n                billing_entity_id: str = Field(alias="billing_entity_id")\n        ')
        ts_content = textwrap.dedent('\n            export type Database = {\n              public: {\n                Tables: {\n                  billing_entities: {\n                    Row: { id: string, name: string }\n                    Relationships: []\n                  }\n                  credit_notes: {\n                    Row: { id: string, billing_entity: string, billing_entity_id: string }\n                    Relationships: [\n                      {\n                        foreignKeyName: "credit_notes_billing_entity_id_fkey"\n                        columns: ["billing_entity_id"]\n                        isOneToOne: false\n                        referencedRelation: "billing_entities"\n                        referencedColumns: ["id"]\n                      }\n                    ]\n                  }\n                }\n                Views: {}\n                Functions: {}\n                Enums: {}\n                CompositeTypes: {}\n              }\n            }\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(ts_content, "public")
        pk_map = {("public", "billing_entities"): ["id"], ("public", "credit_notes"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        script = f"\n{code}\n\nfrom sqlalchemy.orm import configure_mappers\n\nconfigure_mappers()\n"
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr

    def test_multiple_foreign_keys_emit_disambiguated_relationships(self):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicUsers(BaseModel):\n                id: str = Field(alias="id")\n                name: str = Field(alias="name")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                contractor_id: str = Field(alias="contractor_id")\n                processed_by_id: str = Field(alias="processed_by_id")\n        ')
        ts_content = textwrap.dedent('\n            export type Database = {\n              public: {\n                Tables: {\n                  users: {\n                    Row: { id: string, name: string }\n                    Relationships: []\n                  }\n                  withdrawals: {\n                    Row: { id: string, contractor_id: string, processed_by_id: string }\n                    Relationships: [\n                      {\n                        foreignKeyName: "withdrawals_contractor_id_fkey"\n                        columns: ["contractor_id"]\n                        isOneToOne: false\n                        referencedRelation: "users"\n                        referencedColumns: ["id"]\n                      },\n                      {\n                        foreignKeyName: "withdrawals_processed_by_id_fkey"\n                        columns: ["processed_by_id"]\n                        isOneToOne: false\n                        referencedRelation: "users"\n                        referencedColumns: ["id"]\n                      }\n                    ]\n                  }\n                }\n                Views: {}\n                Functions: {}\n                Enums: {}\n                CompositeTypes: {}\n              }\n            }\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(ts_content, "public")
        pk_map = {("public", "users"): ["id"], ("public", "withdrawals"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        script = f"\n{code}\n\nfrom sqlalchemy.orm import configure_mappers\n\nconfigure_mappers()\n"
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr

class TestModelOrdering:

    def test_parents_before_children(self, sample_pydantic_output, sample_ts_single_fk):
        models = parse_pydantic_types(sample_pydantic_output, "public", "Public")
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {("public", "departments"): ["id"], ("public", "products"): ["id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        dept_pos = code.index("class Departments")
        prod_pos = code.index("class Products")
        assert dept_pos < prod_pos

    def test_link_tables_before_referencing_models(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicInvoices(BaseModel):\n                id: str = Field(alias="id")\n                total: float = Field(alias="total")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                amount: float = Field(alias="amount")\n\n            class PublicInvoiceWithdrawals(BaseModel):\n                invoice_id: str = Field(alias="invoice_id")\n                withdrawal_id: str = Field(alias="withdrawal_id")\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {("public", "invoices"): ["id"], ("public", "withdrawals"): ["id"], ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        link_pos = code.index("class InvoiceWithdrawals")
        inv_pos = code.index("class Invoices")
        assert link_pos < inv_pos

class TestM2MPlusDirectFK:
    """When a table has both a direct FK and an M2M link to the same target,
    the generated relationship names must not collide."""

    def test_no_duplicate_attribute_names(self, sample_ts_m2m_plus_direct_fk):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicInvoices(BaseModel):\n                id: str = Field(alias="id")\n                total: float = Field(alias="total")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                amount: float = Field(alias="amount")\n                invoice_id: str | None = Field(alias="invoice_id")\n\n            class PublicInvoiceWithdrawals(BaseModel):\n                invoice_id: str = Field(alias="invoice_id")\n                withdrawal_id: str = Field(alias="withdrawal_id")\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m_plus_direct_fk, "public")
        pk_map = {("public", "invoices"): ["id"], ("public", "withdrawals"): ["id"], ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        inv_block_start = code.index("class Invoices(")
        inv_block_end = code.index("\n\n\nclass ", inv_block_start + 1)
        inv_block = code[inv_block_start:inv_block_end]
        attr_lines = [line.strip().split(":")[0] for line in inv_block.split("\n") if "Relationship(" in line]
        assert len(attr_lines) == len(set(attr_lines)), f"Duplicate relationship attribute names on Invoices: {attr_lines}"

    def test_back_populates_symmetric(self, sample_ts_m2m_plus_direct_fk):
        pydantic_content = textwrap.dedent('\n            from pydantic import BaseModel, Field\n\n            class PublicInvoices(BaseModel):\n                id: str = Field(alias="id")\n                total: float = Field(alias="total")\n\n            class PublicWithdrawals(BaseModel):\n                id: str = Field(alias="id")\n                amount: float = Field(alias="amount")\n                invoice_id: str | None = Field(alias="invoice_id")\n\n            class PublicInvoiceWithdrawals(BaseModel):\n                invoice_id: str = Field(alias="invoice_id")\n                withdrawal_id: str = Field(alias="withdrawal_id")\n        ')
        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m_plus_direct_fk, "public")
        pk_map = {("public", "invoices"): ["id"], ("public", "withdrawals"): ["id"], ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"]}
        code = generate_sqlmodel_code("public", models, rels, pk_map)
        bp_pairs = re.findall('back_populates="(\\w+)"', code)
        for name in bp_pairs:
            assert f"{name}:" in code or f"{name} :" in code, f'back_populates="{name}" has no matching attribute in the code'
