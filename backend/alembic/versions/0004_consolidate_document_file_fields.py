"""consolidate file fields: drop file_size_bytes/content_type from documents

file_size_bytes and content_type describe a specific uploaded file, not the
logical document grouping.  They belong exclusively on document_versions
(already added there in 0003).  Keeping them on documents would force
callers to decide which table is authoritative when versions disagree.

error_message STAYS on documents as an intentional denormalization:
  - The list-documents endpoint needs to surface "this document failed"
    without joining to document_versions on every row.
  - The worker clears it to NULL on success and sets it on failure —
    documented in app/worker/ingestion.py.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the two columns that are authoritative on document_versions only.
    # error_message (added in 0003) is intentionally kept on documents.
    op.drop_column("documents", "file_size_bytes")
    op.drop_column("documents", "content_type")


def downgrade() -> None:
    # Re-add in the same order they appeared in 0003 — nullable so
    # the back-fill problem doesn't block the rollback.
    op.add_column(
        "documents",
        sa.Column("content_type", sa.String(128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
    )
