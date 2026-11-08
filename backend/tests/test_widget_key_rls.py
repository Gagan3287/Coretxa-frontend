"""
test_widget_key_rls.py -- proves the resolve_widget_key() SECURITY DEFINER
function returns a bot row even when called AS cortexa_app with no tenant
context, while a direct SELECT on bots from the same session returns 0 rows.

This verifies the core property described in migration 0005 step 8:
  - bots has FORCE ROW LEVEL SECURITY
  - platform_session() does SET LOCAL ROLE cortexa_app before any query
  - With no app.tenant_id set, cortexa_app sees zero rows on bots directly
  - The SECURITY DEFINER function bypasses RLS (runs as postgres) and
    returns exactly the three safe columns regardless of the session role

If this test fails it means either:
  a) The function was not created (migration 0005 / conftest fixture didn't run)
  b) The function no longer has SECURITY DEFINER or its owner lost bypass access
  c) get_bot_context() would return 401 for every valid widget key in production
"""
import secrets
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.database import platform_session, tenant_session
from app.core.security import hash_password, hash_widget_key
from app.models import Bot, Tenant, User

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def bot_with_widget_key():
    """
    Create a tenant, one bot with a known widget key, yield
    (tenant_id, bot_id, raw_widget_key, key_hash), then clean up.
    """
    tenant_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    raw_key = f"wgt_{secrets.token_urlsafe(32)}"
    key_hash = hash_widget_key(raw_key)

    # Use platform_session() for tenant creation (no RLS on tenants).
    async with platform_session() as session:
        tenant = Tenant(
            id=tenant_id,
            name="Widget Test Tenant",
            slug=f"widget-test-{uuid.uuid4().hex[:8]}",
            api_key_hash=hash_password("unused"),
        )
        session.add(tenant)

    # Use tenant_session() for the bot -- bots has RLS, requires tenant context.
    async with tenant_session(tenant_id) as session:
        bot = Bot(
            id=bot_id,
            tenant_id=tenant_id,
            name="Widget Test Bot",
            slug=f"widget-bot-{uuid.uuid4().hex[:6]}",
            widget_key_hash=key_hash,
            status="active",
        )
        session.add(bot)

    yield tenant_id, bot_id, raw_key, key_hash

    # Cleanup: delete tenant (cascades to bot).
    async with platform_session() as session:
        from sqlalchemy import delete
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def test_direct_select_on_bots_returns_zero_rows_under_cortexa_app(
    bot_with_widget_key,
):
    """
    A direct SELECT on bots AS cortexa_app with no app.tenant_id returns
    zero rows.  This proves the RLS gap that resolve_widget_key() fixes:
    without the SECURITY DEFINER function, get_bot_context() would always
    return None and every widget request would 401.
    """
    tenant_id, bot_id, raw_key, key_hash = bot_with_widget_key

    async with platform_session() as session:
        # platform_session() issues SET LOCAL ROLE cortexa_app and does NOT
        # set app.tenant_id -- same as the real get_bot_context() code path.
        # Verify the role is active.
        role_result = await session.execute(text("SELECT current_role"))
        current_role = role_result.scalar_one()
        assert current_role == "cortexa_app", (
            f"Expected current_role=cortexa_app, got {current_role!r}; "
            "APP_DB_ROLE may not be set"
        )

        # Direct SELECT on bots must return 0 rows (RLS blocks it).
        result = await session.execute(
            select(Bot).where(Bot.widget_key_hash == key_hash)
        )
        direct_rows = result.scalars().all()

    assert direct_rows == [], (
        f"CRITICAL: Direct SELECT on bots returned {len(direct_rows)} row(s) "
        "under cortexa_app with no tenant context -- FORCE ROW LEVEL SECURITY "
        "is not working on the bots table"
    )


async def test_resolve_widget_key_returns_bot_under_cortexa_app(
    bot_with_widget_key,
):
    """
    resolve_widget_key() returns the correct bot_id and tenant_id even
    when called AS cortexa_app with no app.tenant_id.

    This is the core property of the SECURITY DEFINER function: it runs
    as postgres (bypassing RLS) and returns only the safe columns.
    """
    tenant_id, bot_id, raw_key, key_hash = bot_with_widget_key

    async with platform_session() as session:
        result = await session.execute(
            text(
                "SELECT bot_id, tenant_id, status "
                "FROM public.resolve_widget_key(:hash)"
            ),
            {"hash": key_hash},
        )
        row = result.one_or_none()

    assert row is not None, (
        "resolve_widget_key() returned None -- function may not exist. "
        "Run: alembic upgrade 0005  (or restart the test suite so conftest "
        "setup_app_role recreates it)"
    )

    fn_bot_id, fn_tenant_id, fn_status = row
    assert str(fn_bot_id) == str(bot_id), (
        f"resolve_widget_key returned bot_id={fn_bot_id}, expected {bot_id}"
    )
    assert str(fn_tenant_id) == str(tenant_id), (
        f"resolve_widget_key returned tenant_id={fn_tenant_id}, expected {tenant_id}"
    )
    assert fn_status == "active", (
        f"resolve_widget_key returned status={fn_status!r}, expected 'active'"
    )


async def test_resolve_widget_key_returns_nothing_for_unknown_hash(
    bot_with_widget_key,
):
    """
    resolve_widget_key() returns no row for a hash that doesn't exist.
    This proves the function doesn't leak data -- unknown hashes get None,
    not all bots.
    """
    async with platform_session() as session:
        result = await session.execute(
            text(
                "SELECT bot_id, tenant_id, status "
                "FROM public.resolve_widget_key(:hash)"
            ),
            {"hash": "deadbeef" * 8},  # 64-char garbage hash
        )
        row = result.one_or_none()

    assert row is None, (
        "resolve_widget_key() returned a row for a nonexistent hash -- "
        "the function has a data leak"
    )


async def test_both_in_same_session_proves_rls_vs_definer(bot_with_widget_key):
    """
    In a single platform_session() (one SET LOCAL ROLE cortexa_app):
      - Direct SELECT on bots: 0 rows
      - resolve_widget_key(): 1 row

    This is the definitive proof that the function bypasses RLS while the
    session role does not.  Both queries run in the same transaction with
    the same role active.
    """
    tenant_id, bot_id, raw_key, key_hash = bot_with_widget_key

    async with platform_session() as session:
        # 1. Direct SELECT -- must be empty.
        direct = await session.execute(
            select(Bot).where(Bot.widget_key_hash == key_hash)
        )
        direct_rows = direct.scalars().all()

        # 2. Function call -- must return the bot.
        fn_result = await session.execute(
            text(
                "SELECT bot_id, tenant_id, status "
                "FROM public.resolve_widget_key(:hash)"
            ),
            {"hash": key_hash},
        )
        fn_row = fn_result.one_or_none()

    assert direct_rows == [], (
        f"Direct SELECT leaked {len(direct_rows)} row(s) -- RLS broken on bots"
    )
    assert fn_row is not None, (
        "resolve_widget_key() returned None -- SECURITY DEFINER function broken"
    )
    assert str(fn_row[0]) == str(bot_id)
