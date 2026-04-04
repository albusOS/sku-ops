"""Documents persistence via SQLModel."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select

from documents.domain.document import Document
from shared.infrastructure.db.orm_utils import as_uuid_required
from shared.infrastructure.db.services._base import DomainDatabaseService
from shared.infrastructure.types.public_sql_model_models import Documents

logger = logging.getLogger(__name__)


class DocumentsDatabaseService(DomainDatabaseService):
    def _row_to_document(self, row: Documents) -> Document:
        pd = row.parsed_data
        if pd and not isinstance(pd, str):
            pd = json.dumps(pd)
        return Document(
            id=str(row.id),
            organization_id=str(row.organization_id),
            created_at=row.created_at,
            updated_at=row.updated_at,
            filename=row.filename,
            document_type=row.document_type,
            vendor_name=row.vendor_name,
            file_hash=row.file_hash,
            file_size=row.file_size,
            mime_type=row.mime_type,
            parsed_data=pd,
            po_id=str(row.po_id) if row.po_id else None,
            status=row.status,
            uploaded_by_id=str(row.uploaded_by_id),
        )

    async def insert_document(self, doc: Document) -> None:
        d = doc.model_dump()
        parsed = d.get("parsed_data")
        if parsed and not isinstance(parsed, str):
            parsed = json.dumps(parsed)
        row = Documents(
            id=as_uuid_required(d["id"]),
            filename=d["filename"],
            document_type=d.get("document_type", "other"),
            vendor_name=d.get("vendor_name"),
            file_hash=d.get("file_hash", "") or "",
            file_size=int(d.get("file_size", 0) or 0),
            mime_type=d.get("mime_type", "") or "",
            parsed_data=parsed,
            po_id=as_uuid_required(d["po_id"]) if d.get("po_id") else None,
            status=d.get("status", "parsed"),
            uploaded_by_id=as_uuid_required(d["uploaded_by_id"]),
            organization_id=as_uuid_required(d["organization_id"]),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
        )
        async with self.session() as session:
            session.add(row)
            await self.end_write_session(session)

    async def insert_parsed_document(
        self,
        org_id: str,
        extracted: dict,
        filename: str,
        content_type: str,
        file_size: int,
        uploaded_by_id: str,
    ) -> dict:
        """Build Document from parse output, persist, return extracted dict with document_id."""
        doc = Document(
            filename=filename,
            document_type="other",
            vendor_name=extracted.get("vendor_name"),
            file_hash=hashlib.sha256(filename.encode()).hexdigest()[:16],
            file_size=file_size,
            mime_type=content_type,
            parsed_data=json.dumps(extracted),
            status="parsed",
            uploaded_by_id=uploaded_by_id,
            organization_id=org_id,
        )
        await self.insert_document(doc)
        out = {**extracted, "document_id": doc.id}
        logger.info(
            "document.parsed_and_persisted",
            extra={
                "org_id": org_id,
                "document_id": doc.id,
                "doc_filename": filename,
            },
        )
        return out

    async def get_document_by_id(self, doc_id: str, org_id: str) -> Document | None:
        did = as_uuid_required(doc_id)
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            result = await session.execute(
                select(Documents).where(Documents.id == did, Documents.organization_id == oid)
            )
            row = result.scalar_one_or_none()
            return self._row_to_document(row) if row else None

    async def list_documents(
        self,
        org_id: str,
        *,
        status: str | None = None,
        vendor_name: str | None = None,
        po_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        oid = as_uuid_required(org_id)
        async with self.session() as session:
            stmt = select(Documents).where(Documents.organization_id == oid)
            if status:
                stmt = stmt.where(Documents.status == status)
            if vendor_name:
                like = f"%{vendor_name.lower()}%"
                stmt = stmt.where(func.lower(Documents.vendor_name).like(like))
            if po_id:
                stmt = stmt.where(Documents.po_id == as_uuid_required(po_id))
            stmt = stmt.order_by(Documents.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [self._row_to_document(r) for r in rows]

    async def update_document_status(self, doc_id: str, org_id: str, status: str, po_id: str | None = None) -> None:
        did = as_uuid_required(doc_id)
        oid = as_uuid_required(org_id)
        now = datetime.now(UTC)
        async with self.session() as session:
            result = await session.execute(
                select(Documents).where(Documents.id == did, Documents.organization_id == oid)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return
            row.status = status
            row.updated_at = now
            if po_id is not None:
                row.po_id = as_uuid_required(po_id)
            await self.end_write_session(session)
