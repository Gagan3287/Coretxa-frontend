"""
Requires a real Postgres+pgvector database with the schema already migrated
(alembic upgrade head) — RLS can only be proven against real Postgres, never
mocked, since the whole point is that the DB engine itself enforces it.

Point DATABASE_URL (via .env or env var) at a disposable test database
before running these tests. Never point this at production data.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env.test into os.environ NOW — before any `from app...` import
# triggers app.core.config.Settings() instantiation.
# pydantic-settings reads os.environ at Settings() construction time, so
# these values must be present before that first import.
load_dotenv(Path(__file__).parent.parent / ".env.test", override=True)

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.core.database import engine, platform_session, tenant_session
from app.core.security import hash_password
from app.models import Document, Tenant, User
import app.worker.queue as _queue_module


@pytest.fixture(scope="session", autouse=True)
def setup_app_role():
    """
    Ensure the non-superuser 'cortexa_app' role exists and has minimum
    privileges, so RLS policies apply during tests.

    RELATIONSHIP WITH MIGRATION 0005
    ---------------------------------
    Migration 0005 (0005_create_app_role.py) performs the same role setup
    in production.  This fixture exists so tests work even on a freshly
    created test database where alembic upgrade head was run BEFORE
    migration 0005 existed -- or where the test runner does its own
    alembic upgrade head that includes 0005 already.

    Non-conflict guarantee:
      * Every statement in this fixture is idempotent (IF NOT EXISTS, OR
        REPLACE, etc.).
      * Migration 0005 is also idempotent.
      * Running both in order is safe: the fixture runs after alembic
        upgrade head, so if 0005 already ran, all the DO blocks here are
        no-ops.

    GRANT cortexa_app TO postgres
    ------------------------------
    Same as migration 0005 step 1b.  Required on Supabase (where postgres
    is not a true superuser) so that SET LOCAL ROLE cortexa_app succeeds.
    On local Docker where postgres IS a real superuser this is a no-op.

    resolve_widget_key() SECURITY DEFINER function
    -----------------------------------------------
    Same as migration 0005 step 8.  Ensures get_bot_context() works in
    the test environment (platform_session() does SET LOCAL ROLE
    cortexa_app; bots has FORCE RLS; without the function every widget
    auth test would 401).

    Runs ONCE per test session (not per test function).  Uses asyncio.run()
    inside a sync fixture so it is compatible with
    asyncio_default_fixture_loop_scope = function -- session-scoped ASYNC
    fixtures conflict with per-function event loops in pytest-asyncio.
    """
    import asyncio
    import asyncpg
    from app.core.config import settings

    async def _setup():
        url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        try:
            conn = await asyncpg.connect(url)
        except (OSError, asyncpg.PostgresError) as exc:
            # If test database is not reachable, skip DB fixture setup so unit tests can run
            return

        try:
            # 1. Create the role if it doesn't exist.
            await conn.execute(
                "DO $$ BEGIN "
                "  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cortexa_app') THEN "
                "    CREATE ROLE cortexa_app NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "                            NOINHERIT NOLOGIN NOBYPASSRLS; "
                "  ELSE "
                "    ALTER ROLE cortexa_app NOBYPASSRLS NOSUPERUSER; "
                "  END IF; "
                "END $$"
            )

            # 2. GRANT cortexa_app TO postgres -- required for SET LOCAL ROLE on
            #    Supabase where postgres is not a true superuser.  No-op locally.
            await conn.execute("GRANT cortexa_app TO postgres;")

            # 3. Schema and database access.
            db_name = url.rsplit("/", 1)[-1]
            await conn.execute(f"GRANT CONNECT ON DATABASE {db_name} TO cortexa_app")
            await conn.execute("GRANT USAGE ON SCHEMA public TO cortexa_app")

            # 4. Table privileges.
            await conn.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cortexa_app")
            await conn.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cortexa_app")
            await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cortexa_app")
            await conn.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cortexa_app")

            # 5. resolve_widget_key() SECURITY DEFINER function.
            #    Required so get_bot_context() works under cortexa_app (bots has
            #    FORCE RLS; without the function, platform_session widget lookups
            #    return zero rows).
            await conn.execute("""
                CREATE OR REPLACE FUNCTION public.resolve_widget_key(p_hash text)
                RETURNS TABLE (bot_id uuid, tenant_id uuid, status text)
                LANGUAGE sql
                SECURITY DEFINER
                SET search_path = ''
                AS $$
                    SELECT b.id, b.tenant_id, b.status
                    FROM public.bots b
                    WHERE b.widget_key_hash = p_hash
                    LIMIT 1;
                $$
            """)
            await conn.execute(
                "REVOKE EXECUTE ON FUNCTION public.resolve_widget_key(text) FROM PUBLIC"
            )
            await conn.execute(
                "GRANT EXECUTE ON FUNCTION public.resolve_widget_key(text) TO cortexa_app"
            )
        finally:
            await conn.close()

    asyncio.run(_setup())
    yield



@pytest_asyncio.fixture(autouse=True)
async def _reset_engine_per_test():
    """
    Dispose the SQLAlchemy engine's connection pool BEFORE each test.

    Why: engine is a module-level singleton created at import time.  With
    asyncio_default_fixture_loop_scope = function each test runs on a fresh
    event loop.  Any pooled connections from a previous test are bound to
    that test's (now-dead) loop.  engine.dispose() closes those stale
    connections; the next checkout opens a fresh connection on THIS test's
    loop, eliminating "Future attached to a different loop" errors.
    """
    await engine.dispose()
    yield


@pytest_asyncio.fixture(autouse=True)
async def _reset_redis_per_test():
    """
    Reset the Redis client singleton BEFORE each test.

    Why: get_redis() caches its aioredis.Redis client in a module-level
    _pool variable.  That client's internal connection state is tied to
    the event loop on which it was first used.  Resetting _pool to None
    before each test causes get_redis() to create a fresh client on the
    current test's loop, preventing loop-mismatch errors on Redis ops.
    """
    _queue_module._pool = None
    yield


@pytest_asyncio.fixture
async def two_tenants():
    """Create Tenant A and Tenant B, each with one admin user, for isolation tests."""
    async with platform_session() as session:
        tenant_a = Tenant(
            id=uuid.uuid4(), name="Tenant A", slug=f"tenant-a-{uuid.uuid4().hex[:8]}",
            api_key_hash=hash_password("unused"),
        )
        tenant_b = Tenant(
            id=uuid.uuid4(), name="Tenant B", slug=f"tenant-b-{uuid.uuid4().hex[:8]}",
            api_key_hash=hash_password("unused"),
        )
        session.add_all([tenant_a, tenant_b])
        await session.flush()
        tenant_a_id, tenant_b_id = tenant_a.id, tenant_b.id

    async with tenant_session(tenant_a_id) as session:
        user_a = User(
            id=uuid.uuid4(), tenant_id=tenant_a_id, email=f"admin-{uuid.uuid4().hex[:6]}@a.test",
            password_hash=hash_password("pw"), role="tenant_admin",
        )
        session.add(user_a)
        await session.flush()
        user_a_id = user_a.id

    async with tenant_session(tenant_b_id) as session:
        user_b = User(
            id=uuid.uuid4(), tenant_id=tenant_b_id, email=f"admin-{uuid.uuid4().hex[:6]}@b.test",
            password_hash=hash_password("pw"), role="tenant_admin",
        )
        session.add(user_b)
        await session.flush()
        user_b_id = user_b.id

    yield tenant_a_id, tenant_b_id, user_a_id, user_b_id

    # Cleanup — tenants cascade-delete their users/documents/etc.
    async with platform_session() as session:
        await session.execute(delete(Tenant).where(Tenant.id.in_([tenant_a_id, tenant_b_id])))
