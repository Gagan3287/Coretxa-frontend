"""
Document management & ingestion triggering — tenant_admin only.

POST /api/v1/bots/{bot_id}/documents          — upload file (new document or re-upload new version)
GET  /api/v1/bots/{bot_id}/documents          — list all documents for a bot
GET  /api/v1/bots/{bot_id}/documents/{doc_id} — get single document details with version history
GET  /api/v1/bots/{bot_id}/documents/{doc_id}/chunks — get chunk list for a specific document version

Upload validation (WP-A)
-------------------------
Content is validated BY BYTES, never by extension or client Content-Type:
  1. Read the whole file.
  2. sniff_content_type() checks the magic bytes.
  3. validate_upload() confirms it parses, is not encrypted, has 1-MAX_PDF_PAGES pages.
  4. If validation fails → 400 with specific error code; nothing is written.
  5. Quota check → 413 if exceeded; nothing is written.
  6. Only after validation passes: write to storage, insert DB rows, enqueue.

Storage key (A5)
----------------
The object stored is f"{version_id}.pdf" — no client filename in the path.
Document.original_filename stores the sanitized client name for display only.

API responses (A6)
------------------
file_path is absent from all response schemas. The DB keeps it internally.

Duplicate content (A8)
-----------------------
SHA-256 of the file bytes is stored in document_versions.content_sha256.
Re-uploading to an existing document with the same hash as its current ready
version returns 409 {"error":"duplicate_content"} unless force=true.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import tenant_session
from app.core.storage import build_storage_key, get_storage
from app.core.upload_validation import UploadValidationError, sanitize_filename, validate_upload
from app.deps import require_role
from app.models import AuditLog, Bot, Chunk, Document, DocumentVersion, Tenant
from app.schemas.document import (
    ChunkDetail,
    ChunkListResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentVersionDetail,
    DocumentWithVersionsDetail,
)
from app.worker.queue import enqueue, get_redis

router = APIRouter(prefix="/bots/{bot_id}/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _version_to_detail(ver: DocumentVersion) -> DocumentVersionDetail:
    return DocumentVersionDetail(
        version_id=ver.id,
        document_id=ver.document_id,
        version_number=ver.version_number,
        status=ver.status,
        file_size_bytes=ver.file_size_bytes,
        content_type=ver.content_type,
        error_message=ver.error_message,
        created_at=ver.created_at,
        updated_at=ver.updated_at,
    )


def _doc_to_detail(doc: Document) -> DocumentDetail:
    return DocumentDetail(
        document_id=doc.id,
        bot_id=doc.bot_id,
        tenant_id=doc.tenant_id,
        original_filename=doc.original_filename,
        status=doc.status,
        current_version_id=doc.current_version_id,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _doc_to_with_versions_detail(doc: Document) -> DocumentWithVersionsDetail:
    return DocumentWithVersionsDetail(
        document_id=doc.id,
        bot_id=doc.bot_id,
        tenant_id=doc.tenant_id,
        original_filename=doc.original_filename,
        status=doc.status,
        current_version_id=doc.current_version_id,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        versions=[_version_to_detail(v) for v in doc.versions],
    )


def _chunk_to_detail(chunk: Chunk) -> ChunkDetail:
    return ChunkDetail(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        document_version_id=chunk.document_version_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        section_title=chunk.section_title,
        token_count=chunk.token_count,
        created_at=chunk.created_at,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/bots/{bot_id}/documents — upload file / re-upload version
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document or new document version for ingestion",
)
async def upload_document(
    bot_id: UUID,
    file: UploadFile = File(...),
    document_id: UUID | None = Form(None),
    force: bool = Form(False),
    claims: dict = Depends(require_role("tenant_admin")),
) -> DocumentUploadResponse:
    tenant_id = UUID(claims["tenant_id"])
    version_id = uuid.uuid4()

    # ---- 1. Read file content ----
    file_content = await file.read()
    file_size_bytes = len(file_content)

    # ---- 2. Content-based validation (BEFORE any side effect) ----
    # validate_upload() raises UploadValidationError on any failure.
    # We run pypdf off the event loop.
    try:
        sniffed_content_type = await asyncio.get_event_loop().run_in_executor(
            None, validate_upload, file_content
        )
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail=exc.to_detail(),
        ) from None

    # ---- 3. Sanitize original filename for display (A5) ----
    original_filename = sanitize_filename(file.filename)

    # ---- 4. Compute SHA-256 for duplicate detection (A8) ----
    content_sha256 = hashlib.sha256(file_content).hexdigest()

    async with tenant_session(tenant_id) as session:
        # ---- 5. Verify Tenant & storage quota ----
        tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")

        usage_result = await session.execute(
            select(func.coalesce(func.sum(DocumentVersion.file_size_bytes), 0)).where(
                DocumentVersion.tenant_id == tenant_id
            )
        )
        current_usage_bytes: int = int(usage_result.scalar_one())
        quota_bytes = tenant.storage_quota_mb * 1024 * 1024

        if current_usage_bytes + file_size_bytes > quota_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "storage_quota_exceeded",
                    "message": f"Storage quota of {tenant.storage_quota_mb}MB exceeded",
                    "current_usage_bytes": current_usage_bytes,
                    "quota_mb": tenant.storage_quota_mb,
                },
            )

        # ---- 6. Verify Bot exists and belongs to this tenant ----
        bot_result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.tenant_id == tenant_id)
        )
        bot = bot_result.scalar_one_or_none()
        if bot is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        # ---- 7. Re-upload or New Upload logic ----
        if document_id is not None:
            # Re-upload: verify Document exists for this bot
            doc_result = await session.execute(
                select(Document).where(Document.id == document_id, Document.bot_id == bot_id)
            )
            doc = doc_result.scalar_one_or_none()
            if doc is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "Document not found for this bot"
                )

            # Duplicate content check (A8): compare sha256 against current ready version
            if not force and doc.current_version_id is not None:
                cur_ver_result = await session.execute(
                    select(DocumentVersion).where(
                        DocumentVersion.id == doc.current_version_id,
                        DocumentVersion.status == "ready",
                    )
                )
                cur_ver = cur_ver_result.scalar_one_or_none()
                if cur_ver is not None and cur_ver.content_sha256 == content_sha256:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "duplicate_content",
                            "message": "File content is identical to the current ready version. Use force=true to re-ingest anyway.",
                        },
                    )

            # Determine next version number
            max_ver_result = await session.execute(
                select(func.max(DocumentVersion.version_number)).where(
                    DocumentVersion.document_id == document_id
                )
            )
            max_ver = max_ver_result.scalar_one()
            version_number = (max_ver or 0) + 1
            doc.status = "pending"
        else:
            # New document creation
            doc = Document(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                bot_id=bot_id,
                original_filename=original_filename,
                status="pending",
                current_version_id=None,
                error_message=None,
            )
            session.add(doc)
            await session.flush()
            version_number = 1

        # ---- 8. Build storage key (A5, D1-D3): {version_id}.pdf only ----
        storage = get_storage()
        storage_key = build_storage_key(tenant_id, bot_id, version_id)
        storage.write(storage_key, file_content)

        # ---- 9. Create DocumentVersion record ----
        ver = DocumentVersion(
            id=version_id,
            tenant_id=tenant_id,
            bot_id=bot_id,
            document_id=doc.id,
            version_number=version_number,
            file_path=storage_key,  # POSIX key, not OS path
            status="pending",
            file_size_bytes=file_size_bytes,
            content_type=sniffed_content_type,  # A3: always use sniffed type
            error_message=None,
            content_sha256=content_sha256,
        )
        session.add(ver)
        await session.flush()

        # ---- 10. Write audit log ----
        audit = AuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_id=UUID(claims["sub"]),
            action="document.uploaded",
            details={
                "bot_id": str(bot_id),
                "document_id": str(doc.id),
                "version_id": str(ver.id),
                "version_number": version_number,
                "filename": doc.original_filename,
            },
        )
        session.add(audit)

    # ---- 11. Enqueue ingestion task to Redis stream ----
    r = get_redis()
    await enqueue(
        r,
        document_version_id=ver.id,
        tenant_id=tenant_id,
        bot_id=bot_id,
        attempt=1,
    )

    return DocumentUploadResponse(
        document_id=doc.id,
        version_id=ver.id,
        version_number=ver.version_number,
        original_filename=doc.original_filename,
        status=ver.status,
        created_at=ver.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bots/{bot_id}/documents — list documents
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents for a bot",
)
async def list_documents(
    bot_id: UUID,
    claims: dict = Depends(require_role("tenant_admin")),
) -> DocumentListResponse:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        # Check bot exists
        bot_result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.tenant_id == tenant_id)
        )
        if bot_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        docs_result = await session.execute(
            select(Document)
            .where(Document.bot_id == bot_id)
            .order_by(Document.created_at.desc())
        )
        docs = docs_result.scalars().all()

    return DocumentListResponse(
        documents=[_doc_to_detail(d) for d in docs],
        total=len(docs),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/bots/{bot_id}/documents/{doc_id} — document detail with version history
# ---------------------------------------------------------------------------


@router.get(
    "/{doc_id}",
    response_model=DocumentWithVersionsDetail,
    summary="Get document details including version history",
)
async def get_document(
    bot_id: UUID,
    doc_id: UUID,
    claims: dict = Depends(require_role("tenant_admin")),
) -> DocumentWithVersionsDetail:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        # Check bot exists
        bot_result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.tenant_id == tenant_id)
        )
        if bot_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        doc_result = await session.execute(
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == doc_id, Document.bot_id == bot_id)
        )
        doc = doc_result.scalar_one_or_none()

    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

    return _doc_to_with_versions_detail(doc)


# ---------------------------------------------------------------------------
# GET /api/v1/bots/{bot_id}/documents/{doc_id}/chunks — list chunks
# ---------------------------------------------------------------------------


@router.get(
    "/{doc_id}/chunks",
    response_model=ChunkListResponse,
    summary="List chunks for a specific document version (defaults to current version)",
)
async def list_chunks(
    bot_id: UUID,
    doc_id: UUID,
    version_id: UUID | None = None,
    claims: dict = Depends(require_role("tenant_admin")),
) -> ChunkListResponse:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        # Check bot exists
        bot_result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.tenant_id == tenant_id)
        )
        if bot_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        doc_result = await session.execute(
            select(Document).where(Document.id == doc_id, Document.bot_id == bot_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

        target_version_id = version_id or doc.current_version_id
        if target_version_id is None:
            return ChunkListResponse(chunks=[], total=0)

        chunks_result = await session.execute(
            select(Chunk)
            .where(
                Chunk.document_id == doc_id,
                Chunk.document_version_id == target_version_id,
            )
            .order_by(Chunk.chunk_index.asc())
        )
        chunks = chunks_result.scalars().all()

    return ChunkListResponse(
        chunks=[_chunk_to_detail(c) for c in chunks],
        total=len(chunks),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/bots/{bot_id}/documents/{doc_id} — delete document and files
# ---------------------------------------------------------------------------


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a document, its versions, chunks/embeddings, and stored files",
)
async def delete_document(
    bot_id: UUID,
    doc_id: UUID,
    claims: dict = Depends(require_role("tenant_admin")),
) -> Response:
    tenant_id = UUID(claims["tenant_id"])

    async with tenant_session(tenant_id) as session:
        # Check bot exists and belongs to tenant
        bot_result = await session.execute(
            select(Bot).where(Bot.id == bot_id, Bot.tenant_id == tenant_id)
        )
        if bot_result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Bot not found")

        # Load document with versions
        doc_result = await session.execute(
            select(Document)
            .options(selectinload(Document.versions))
            .where(Document.id == doc_id, Document.bot_id == bot_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")

        # Collect file paths to delete via storage seam
        file_paths = [ver.file_path for ver in doc.versions if ver.file_path]

        # Break circular reference between Document and DocumentVersion before deleting
        doc.current_version_id = None
        await session.flush()

        # Delete chunks for this document
        await session.execute(delete(Chunk).where(Chunk.document_id == doc_id))

        # Delete document versions
        await session.execute(delete(DocumentVersion).where(DocumentVersion.document_id == doc_id))

        # Delete document
        await session.delete(doc)

        # Audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_id=UUID(claims["sub"]),
            action="document.deleted",
            details={
                "document_id": str(doc_id),
                "bot_id": str(bot_id),
                "original_filename": doc.original_filename,
                "version_count": len(doc.versions),
            },
        )
        session.add(audit)

    # Clean up storage files after DB transaction completes
    storage = get_storage()
    for fp in file_paths:
        storage.delete(fp)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

