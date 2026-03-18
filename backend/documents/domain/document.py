"""Document domain models for vendor bill/receipt parsing and archival."""

from enum import StrEnum

from shared.kernel.entity import AuditedEntity


class DocumentType(StrEnum):
    RECEIPT = "receipt"
    VENDOR_BILL = "vendor_bill"
    PACKING_SLIP = "packing_slip"
    OTHER = "other"


class DocumentStatus(StrEnum):
    PARSED = "parsed"
    IMPORTED = "imported"
    REJECTED = "rejected"


class Document(AuditedEntity):
    """Persisted record of an uploaded and parsed document."""

    filename: str
    document_type: str = DocumentType.OTHER
    vendor_name: str | None = None
    file_hash: str = ""
    file_size: int = 0
    mime_type: str = ""
    parsed_data: str | None = None
    po_id: str | None = None
    status: str = DocumentStatus.PARSED
    uploaded_by_id: str
