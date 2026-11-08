"""add content_sha256 to document_versions for duplicate detection

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-25

WHY THIS MIGRATION EXISTS
--------------------------
When a document is re-uploaded with identical content, we want to detect this
and return 409 {"error":"duplicate_content"} rather than silently creating a
redundant version. SHA-256 of the file bytes is a reliable content fingerprint.

COLUMNS ADDED
-------------
document_versions.content_sha256  — hex-encoded SHA-256 digest of the raw
                                     file bytes (64 characters). Nullable so
                                     existing rows are unaffected.

INDEX
-----
(document_id, content_sha256) — supports the "is this content already present
                                  in this document?" lookup efficiently.

NOTES
-----
* Applied to LOCAL TEST DB only. Migration 0007 is on Supabase; 0008 must NOT
  be applied there without deliberate deploy steps.
* Nullable column — old versions have NULL, new uploads have the digest.
* The application layer (upload endpoint) sets this before creating the row,
  so the index is useful from the moment of the first new upload.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_versions",
        sa.Column("content_sha256", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_document_versions_document_id_content_sha256",
        "document_versions",
        ["document_id", "content_sha256"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_versions_document_id_content_sha256", table_name="document_versions")
    op.drop_column("document_versions", "content_sha256")
