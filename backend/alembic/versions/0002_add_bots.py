"""add bots table and tenants.max_bots

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add max_bots to tenants table
    op.add_column(
        "tenants",
        sa.Column("max_bots", sa.Integer(), nullable=False, server_default="1"),
    )

    # 2. Create bots table
    op.create_table(
        "bots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("widget_key_hash", sa.String(64), nullable=False),
        sa.Column("branding_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("llm_overrides", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_bots_tenant_slug"),
    )

    op.create_index("ix_bots_tenant_id", "bots", ["tenant_id"])
    # UNIQUE index — the sole lookup path for widget-key auth (O(1), no table scan).
    # SHA-256 hex is always exactly 64 chars; the column was sized to match.
    op.create_index(
        "ix_bots_widget_key_hash", "bots", ["widget_key_hash"], unique=True
    )

    # 3. Row-Level Security for bots table
    op.execute("ALTER TABLE bots ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bots FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_bots ON bots
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_bots ON bots")
    op.drop_index("ix_bots_widget_key_hash", table_name="bots")
    op.drop_index("ix_bots_tenant_id", table_name="bots")
    op.drop_table("bots")
    op.drop_column("tenants", "max_bots")
