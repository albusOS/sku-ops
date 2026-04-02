"""Schema configuration for SQLModel generation pipeline.

Lists Postgres schemas to process. Extend when adding new schemas.
Resolution priority order matters for cross-schema FK resolution:
if a FK target table is not found in the current schema, schemas
earlier in this list are searched first.
"""

SCHEMAS: list[str] = ["public"]

SCHEMA_CLASS_PREFIX: dict[str, str] = {
    "public": "Public",
}
