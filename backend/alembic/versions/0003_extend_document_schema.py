"""extend document schema + add bot_id to documents, document_versions, chunks, queries

Adds:
  - documents:         file_size_bytes, content_type, error_message, bot_id
  - document_versions: file_size_bytes, content_type, error_message, bot_id
  - chunks:            chunk_index, section_title, token_count, bot_id
  - queries:           bot_id
  - Composite indexes on (tenant_id, bot_id) for all four tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # documents                                                            #
    # ------------------------------------------------------------------ #
    op.add_column("documents", sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "fk_documents_bot_id", "documents", "bots", ["bot_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_documents_bot_id", "documents", ["bot_id"])
    op.create_index("ix_documents_tenant_bot", "documents", ["tenant_id", "bot_id"])

    op.add_column(
        "documents",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("content_type", sa.String(128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # document_versions                                                    #
    # ------------------------------------------------------------------ #
    op.add_column(
        "document_versions",
        sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_document_versions_bot_id",
        "document_versions",
        "bots",
        ["bot_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_document_versions_bot_id", "document_versions", ["bot_id"])
    op.create_index(
        "ix_document_versions_tenant_bot", "document_versions", ["tenant_id", "bot_id"]
    )

    op.add_column(
        "document_versions",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("content_type", sa.String(128), nullable=True),
    )
    op.add_column(
        "document_versions",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # chunks                                                               #
    # ------------------------------------------------------------------ #
    op.add_column("chunks", sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "fk_chunks_bot_id", "chunks", "bots", ["bot_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_chunks_bot_id", "chunks", ["bot_id"])
    op.create_index("ix_chunks_tenant_bot", "chunks", ["tenant_id", "bot_id"])

    op.add_column(
        "chunks",
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("chunks", sa.Column("section_title", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("token_count", sa.Integer(), nullable=True))

    # ------------------------------------------------------------------ #
    # queries                                                              #
    # ------------------------------------------------------------------ #
    op.add_column("queries", sa.Column("bot_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "fk_queries_bot_id", "queries", "bots", ["bot_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_queries_bot_id", "queries", ["bot_id"])
    op.create_index("ix_queries_tenant_bot", "queries", ["tenant_id", "bot_id"])


def downgrade() -> None:
    # queries
    op.drop_index("ix_queries_tenant_bot", table_name="queries")
    op.drop_index("ix_queries_bot_id", table_name="queries")
    op.drop_constraint("fk_queries_bot_id", "queries", type_="foreignkey")
    op.drop_column("queries", "bot_id")

    # chunks
    op.drop_column("chunks", "token_count")
    op.drop_column("chunks", "section_title")
    op.drop_column("chunks", "chunk_index")
    op.drop_index("ix_chunks_tenant_bot", table_name="chunks")
    op.drop_index("ix_chunks_bot_id", table_name="chunks")
    op.drop_constraint("fk_chunks_bot_id", "chunks", type_="foreignkey")
    op.drop_column("chunks", "bot_id")

    # document_versions
    op.drop_column("document_versions", "error_message")
    op.drop_column("document_versions", "content_type")
    op.drop_column("document_versions", "file_size_bytes")
    op.drop_index("ix_document_versions_tenant_bot", table_name="document_versions")
    op.drop_index("ix_document_versions_bot_id", table_name="document_versions")
    op.drop_constraint("fk_document_versions_bot_id", "document_versions", type_="foreignkey")
    op.drop_column("document_versions", "bot_id")

    # documents
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "content_type")
    op.drop_column("documents", "file_size_bytes")
    op.drop_index("ix_documents_tenant_bot", table_name="documents")
    op.drop_index("ix_documents_bot_id", table_name="documents")
    op.drop_constraint("fk_documents_bot_id", "documents", type_="foreignkey")
    op.drop_column("documents", "bot_id")
