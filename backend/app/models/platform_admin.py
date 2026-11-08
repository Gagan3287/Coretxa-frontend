"""
Platform (super) admins live entirely outside the tenant boundary — no
tenant_id, no RLS. This is deliberate: mixing a "global" role into the
tenant-scoped `users` table would force RLS policies to special-case
NULL tenant_id everywhere, which is exactly the kind of edge case that
causes isolation bugs. Keeping super-admin auth in its own small table
means the RLS policies on every other table can stay a single simple rule.
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PlatformAdmin(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "platform_admins"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
