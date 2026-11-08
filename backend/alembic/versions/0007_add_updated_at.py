"""add updated_at to documents and document_versions

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-23

WHY THIS MIGRATION EXISTS
--------------------------
The Document and DocumentVersion ORM models previously only had
created_at (from TimestampMixin).  The API serializer
(_doc_to_detail / _doc_to_with_versions_detail / _version_to_detail)
tries to read updated_at from those objects, causing a 500
AttributeError whenever the detail endpoints were called.

FIX
---
Add updated_at timestamptz NOT NULL column to both tables with:
  * server_default = now()        — rows inserted before this migration
                                    get the migration timestamp, which is
                                    safe: it is always >= created_at.
  * onupdate on the ORM model    — SQLAlchemy sets it automatically on
                                    every UPDATE executed through the ORM.

No RLS changes — the column is internal metadata, not tenant payload.
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # documents
    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # document_versions
    op.add_column(
        "document_versions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("document_versions", "updated_at")
    op.drop_column("documents", "updated_at")
