"""
Tenant is the anchor of the whole multi-tenant model. It deliberately has
NO RLS policy of its own — every other tenant-scoped table filters by
tenant_id, but the tenants table has to be readable (by slug) *before*
a tenant_id is known, to solve the login bootstrapping problem. See
app/api/auth.py for how that's used safely (read-only, non-sensitive
columns only, no query-string tenant_id filtering needed since there's
nothing to leak — one tenant's row doesn't expose another's data).
"""
import uuid
from typing import Any

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Tenant(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    storage_quota_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    query_quota_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    max_bots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    branding_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
    documents: Mapped[list["Document"]] = relationship(back_populates="tenant")
    bots: Mapped[list["Bot"]] = relationship(back_populates="tenant")
