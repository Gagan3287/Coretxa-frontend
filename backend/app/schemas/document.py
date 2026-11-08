"""
API response schemas for document-related endpoints.

Design note (A6):
-----------------
file_path is intentionally ABSENT from all response models.
The DB column is an internal storage key; it must never appear in API
responses to avoid leaking OS paths, Windows separators, or internal
directory layout to the client.  The DB keeps it; the API does not expose it.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    version_id: UUID
    version_number: int
    original_filename: str
    status: str
    created_at: datetime


class DocumentVersionDetail(BaseModel):
    """Version metadata — intentionally omits file_path (see module docstring)."""
    version_id: UUID
    document_id: UUID
    version_number: int
    status: str
    file_size_bytes: int | None
    content_type: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(BaseModel):
    document_id: UUID
    bot_id: UUID
    tenant_id: UUID
    original_filename: str
    status: str
    current_version_id: UUID | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentWithVersionsDetail(DocumentDetail):
    versions: list[DocumentVersionDetail]


class DocumentListResponse(BaseModel):
    documents: list[DocumentDetail]
    total: int


class ChunkDetail(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    chunk_index: int
    content: str
    section_title: str | None
    token_count: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkListResponse(BaseModel):
    chunks: list[ChunkDetail]
    total: int
