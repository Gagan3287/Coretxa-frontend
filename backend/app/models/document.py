import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampUpdateMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.bot import Bot
    from app.models.document_version import DocumentVersion


class Document(Base, UUIDPKMixin, TimestampUpdateMixin):
    __tablename__ = "documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # status in {"pending", "processing", "ready", "failed"}
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    # Pointer to the currently-active version (NULL until the first successful ingestion).
    # FK defined here but added via op.create_foreign_key in 0001 after both tables exist.
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=True
    )

    # Denormalized from the latest DocumentVersion for fast list-view queries.
    # Authoritative source: document_versions.error_message.
    # Worker contract:
    #   - Set to the error string on terminal failure (attempt 3).
    #   - Cleared to NULL on subsequent successful ingestion (clear-on-success).
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # file_size_bytes and content_type live on document_versions ONLY —
    # they describe a specific upload, not the logical document grouping.
    # (columns dropped in migration 0004)

    tenant: Mapped["Tenant"] = relationship(back_populates="documents")
    bot: Mapped["Bot"] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        foreign_keys="DocumentVersion.document_id",
        order_by="DocumentVersion.version_number",
    )
