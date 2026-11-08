"""add phone to users table

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-27

WHY THIS MIGRATION EXISTS
--------------------------
Registration requires an optional/nullable phone number on the User record,
enabling contact details collection during tenant admin registration.
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "phone")
