import uuid
from typing import Any, TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.document import Document


class Bot(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "bots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False)
    widget_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    branding_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    llm_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    tenant: Mapped["Tenant"] = relationship(back_populates="bots")
    documents: Mapped[list["Document"]] = relationship(back_populates="bot")
