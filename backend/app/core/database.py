"""
Database engine + the tenant-context session pattern.

The core idea: every query that touches tenant-scoped data runs inside a
transaction where we've executed `SET LOCAL app.tenant_id = '<uuid>'`.
Postgres RLS policies (see sql/rls_policies.sql) key off that setting.
`SET LOCAL` only lasts for the current transaction — it can never leak
across requests, even on a pooled connection.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# statement_cache_size=0 is required when connecting through a PgBouncer-style
# transaction pooler (e.g. Supabase's port-6543 pooler) — without it, asyncpg's
# prepared-statement caching breaks against the pooler.
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    hide_parameters=True,
    connect_args={"statement_cache_size": 0},
)

SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


@asynccontextmanager
async def tenant_session(tenant_id: UUID | None) -> AsyncIterator[AsyncSession]:
    """
    Yield a session scoped to a single tenant via Postgres RLS.

    If tenant_id is None, no `app.tenant_id` is set — only tables with no
    RLS policy (like `tenants` itself, or `platform_admins`) are safely
    queryable in that state. Every tenant-scoped table's RLS policy will
    simply match zero rows if this isn't set, which is a safe failure mode
    (empty result, not a leak) but you should always pass a real tenant_id
    once one is known.
    """
    async with SessionLocal() as session:
        async with session.begin():
            if settings.APP_DB_ROLE:
                # Drop from superuser to app role so RLS policies are enforced.
                # SET LOCAL is transaction-scoped — resets automatically on commit/rollback.
                # Role name comes from settings, never from user input, so no injection risk.
                await session.execute(text(f"SET LOCAL ROLE {settings.APP_DB_ROLE}"))
            if tenant_id is not None:
                # Parameterized — never string-format a UUID into raw SQL.
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(tenant_id)},
                )
            yield session


@asynccontextmanager
async def platform_session() -> AsyncIterator[AsyncSession]:
    """Session with no tenant context — for tenant provisioning and platform-admin auth only."""
    async with SessionLocal() as session:
        async with session.begin():
            if settings.APP_DB_ROLE:
                await session.execute(text(f"SET LOCAL ROLE {settings.APP_DB_ROLE}"))
            yield session


def get_migration_url() -> str:
    """
    Resolve the database URL for Alembic migrations.

    Priority:
    1. settings.MIGRATE_URL or os.environ.get("MIGRATE_URL")
    2. settings.DATABASE_URL

    Host guard:
    Rejects port 6543 (PgBouncer transaction pooler) with a clear error.
    Transaction poolers do not support session-level locks, prepared transactions,
    or DDL operations that Alembic migrations require.
    """
    import os
    url = getattr(settings, "MIGRATE_URL", None) or os.environ.get("MIGRATE_URL") or settings.DATABASE_URL
    if ":6543" in url:
        raise RuntimeError(
            "Cannot run Alembic migrations through a transaction pooler (port 6543). "
            "Use MIGRATE_URL pointing to the direct connection or session pooler (port 5432)."
        )
    return url

