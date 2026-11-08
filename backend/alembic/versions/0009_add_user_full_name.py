"""add full_name to users table

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-27

WHY THIS MIGRATION EXISTS
--------------------------
The frontend onboarding and user profile require storing and displaying the
user's full name. Added as nullable so existing users are unaffected.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "full_name")
