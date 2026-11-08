import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampUpdateMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.chunk import Chunk


class DocumentVersion(Base, UUIDPKMixin, TimestampUpdateMixin):
    __tablename__ = "document_versions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # status in {"pending", "processing", "ready", "failed"}
    # Old versions remain "ready" and queryable until a newer version is confirmed healthy.
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    # Authoritative per-upload metadata — these describe this specific uploaded file.
    # (document.file_size_bytes / document.content_type were dropped in migration 0004)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Set on terminal ingestion failure; cleared by re-reading after success is not needed
    # (a failed version stays "failed" forever — success creates a NEW version row).
    # The Document.error_message is the denormalized copy shown in list views.
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SHA-256 hex digest of the raw file bytes. Nullable for legacy rows.
    # Used for duplicate content detection: re-uploading the same content to the
    # same document returns 409 unless force=true is passed.
    # See migration 0008. Indexed via (document_id, content_sha256).
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    document: Mapped["Document"] = relationship(
        back_populates="versions",
        foreign_keys=[document_id],
    )
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document_version")
