import os
import pytest
from unittest.mock import patch

from app.core.config import settings
from app.core.database import get_migration_url


def test_alembic_host_guard_rejects_transaction_pooler_port_6543():
    """Host guard must raise RuntimeError if URL points to port 6543."""
    with patch.object(settings, "MIGRATE_URL", None), patch.object(
        settings,
        "DATABASE_URL",
        "postgresql+asyncpg://postgres.test:secret@aws-0-pooler.supabase.com:6543/postgres",
    ):
        with pytest.raises(RuntimeError) as exc_info:
            get_migration_url()

        assert "6543" in str(exc_info.value)
        assert "transaction pooler" in str(exc_info.value).lower()


def test_alembic_host_guard_prefers_migrate_url_over_database_url():
    """get_migration_url prefers MIGRATE_URL (e.g. port 5432) even if DATABASE_URL has 6543."""
    migrate_url = "postgresql+asyncpg://postgres.test:secret@aws-0-pooler.supabase.com:5432/postgres"
    tx_url = "postgresql+asyncpg://postgres.test:secret@aws-0-pooler.supabase.com:6543/postgres"

    with patch.object(settings, "MIGRATE_URL", migrate_url), patch.object(
        settings, "DATABASE_URL", tx_url
    ):
        resolved = get_migration_url()
        assert resolved == migrate_url


def test_alembic_host_guard_allows_valid_direct_database_url():
    """get_migration_url allows direct connection when MIGRATE_URL is unset."""
    direct_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/cortexa"
    with patch.object(settings, "MIGRATE_URL", None), patch.object(
        settings, "DATABASE_URL", direct_url
    ):
        resolved = get_migration_url()
        assert resolved == direct_url
