"""End-to-end tests for the SQLModel code generation pipeline."""

from __future__ import annotations

import ast
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
    def test_generates_valid_python(
        self, sample_pydantic_output, sample_ts_empty_rels
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {
            ("public", "departments"): ["id"],
            ("public", "simple_table"): ["id"],
        }

        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)

        tree = ast.parse(code)
        assert tree is not None

    def test_has_future_annotations(
        self, sample_pydantic_output, sample_ts_empty_rels
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {("public", "departments"): ["id"]}

        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)

        assert "from __future__ import annotations" in code

    def test_simple_model_fields(
        self, sample_pydantic_output, sample_ts_empty_rels
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_empty_rels, "public")
        pk_map = {("public", "departments"): ["id"]}

        dept_models = [m for m in models if m.table_name == "departments"]
        code = generate_sqlmodel_code("public", dept_models, rels, pk_map)

        assert "class Departments(SQLModel, table=True):" in code
        assert '__tablename__ = "departments"' in code
        assert "primary_key=True" in code
        assert "id: str" in code


class TestOneToManyGeneration:
    def test_generates_fk_field(
        self, sample_pydantic_output, sample_ts_single_fk
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {
            ("public", "departments"): ["id"],
            ("public", "products"): ["id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        assert 'foreign_key="departments.id"' in code

    def test_generates_relationship_attrs(
        self, sample_pydantic_output, sample_ts_single_fk
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {
            ("public", "departments"): ["id"],
            ("public", "products"): ["id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        assert "Relationship(back_populates=" in code

    def test_back_populates_symmetry(
        self, sample_pydantic_output, sample_ts_single_fk
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {
            ("public", "departments"): ["id"],
            ("public", "products"): ["id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        assert 'back_populates="products"' in code
        assert 'back_populates="category"' in code


class TestM2MGeneration:
    def test_generates_link_model(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent("""
            from pydantic import BaseModel, Field

            class PublicInvoices(BaseModel):
                id: str = Field(alias="id")
                total: float = Field(alias="total")

            class PublicWithdrawals(BaseModel):
                id: str = Field(alias="id")
                amount: float = Field(alias="amount")

            class PublicInvoiceWithdrawals(BaseModel):
                invoice_id: str = Field(alias="invoice_id")
                withdrawal_id: str = Field(alias="withdrawal_id")
        """)

        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {
            ("public", "invoices"): ["id"],
            ("public", "withdrawals"): ["id"],
            ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        assert "class InvoiceWithdrawals(SQLModel, table=True):" in code
        assert "link_model=InvoiceWithdrawals" in code

    def test_m2m_bidirectional(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent("""
            from pydantic import BaseModel, Field

            class PublicInvoices(BaseModel):
                id: str = Field(alias="id")
                total: float = Field(alias="total")

            class PublicWithdrawals(BaseModel):
                id: str = Field(alias="id")
                amount: float = Field(alias="amount")

            class PublicInvoiceWithdrawals(BaseModel):
                invoice_id: str = Field(alias="invoice_id")
                withdrawal_id: str = Field(alias="withdrawal_id")
        """)

        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {
            ("public", "invoices"): ["id"],
            ("public", "withdrawals"): ["id"],
            ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        assert 'back_populates="invoices"' in code
        assert 'back_populates="withdrawals"' in code


class TestModelOrdering:
    def test_parents_before_children(
        self, sample_pydantic_output, sample_ts_single_fk
    ):
        models = parse_pydantic_types(
            sample_pydantic_output, "public", "Public"
        )
        rels = parse_ts_relationships(sample_ts_single_fk, "public")
        pk_map = {
            ("public", "departments"): ["id"],
            ("public", "products"): ["id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        dept_pos = code.index("class Departments")
        prod_pos = code.index("class Products")
        assert dept_pos < prod_pos

    def test_link_tables_before_referencing_models(self, sample_ts_m2m):
        pydantic_content = textwrap.dedent("""
            from pydantic import BaseModel, Field

            class PublicInvoices(BaseModel):
                id: str = Field(alias="id")
                total: float = Field(alias="total")

            class PublicWithdrawals(BaseModel):
                id: str = Field(alias="id")
                amount: float = Field(alias="amount")

            class PublicInvoiceWithdrawals(BaseModel):
                invoice_id: str = Field(alias="invoice_id")
                withdrawal_id: str = Field(alias="withdrawal_id")
        """)

        models = parse_pydantic_types(pydantic_content, "public", "Public")
        rels = parse_ts_relationships(sample_ts_m2m, "public")
        pk_map = {
            ("public", "invoices"): ["id"],
            ("public", "withdrawals"): ["id"],
            ("public", "invoice_withdrawals"): ["invoice_id", "withdrawal_id"],
        }

        code = generate_sqlmodel_code("public", models, rels, pk_map)

        link_pos = code.index("class InvoiceWithdrawals")
        inv_pos = code.index("class Invoices")
        assert link_pos < inv_pos
