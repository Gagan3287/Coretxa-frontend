"""
smoke_app_path.py -- Transaction pooler (port 6543) verification script.
Tests the runtime application path using tenant_session() and platform_session().

Verifies over port 6543:
  1. SELECT current_user inside a session returns cortexa_app
  2. Cross-tenant read by exact ID returns 0 rows (with complete cleanup and no leftover rows)
  3. resolve_widget_key() SECURITY DEFINER function resolves active bot keys under cortexa_app
  4. 20 concurrent sessions complete without prepared-statement or pooler errors
"""
import asyncio
import secrets
import sys
import uuid
from uuid import UUID

from sqlalchemy import delete, func, select, text

from app.core.config import settings
from app.core.database import engine, platform_session, tenant_session
from app.core.security import hash_widget_key
from app.models import Bot, Document, Tenant


async def check_1_current_user():
    print("--- Check 1: SELECT current_user under tenant_session & platform_session ---")
    dummy_tenant_id = uuid.uuid4()
    async with tenant_session(dummy_tenant_id) as session:
        result = await session.execute(text("SELECT current_user"))
        current_user = result.scalar_one()
        assert current_user == settings.APP_DB_ROLE, (
            f"Expected current_user={settings.APP_DB_ROLE}, got {current_user}"
        )
        print(f"  [PASS] tenant_session: current_user = '{current_user}'")

    async with platform_session() as session:
        result = await session.execute(text("SELECT current_user"))
        current_user = result.scalar_one()
        assert current_user == settings.APP_DB_ROLE, (
            f"Expected current_user={settings.APP_DB_ROLE}, got {current_user}"
        )
        print(f"  [PASS] platform_session: current_user = '{current_user}'")


async def check_2_cross_tenant_isolation():
    print("\n--- Check 2: Cross-tenant read by exact ID & cleanup confirmation ---")
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    bot_a_id = uuid.uuid4()
    doc_a_id = uuid.uuid4()

    slug_a = f"smoke-tenant-a-{tenant_a_id.hex[:8]}"
    slug_b = f"smoke-tenant-b-{tenant_b_id.hex[:8]}"
    bot_slug = f"smoke-bot-a-{bot_a_id.hex[:8]}"

    # 1. Seed tenants in platform_session (tenants has no RLS)
    async with platform_session() as session:
        tenant_a = Tenant(
            id=tenant_a_id,
            name="Smoke Tenant A",
            slug=slug_a,
            api_key_hash="hash_a",
            plan_tier="free",
        )
        tenant_b = Tenant(
            id=tenant_b_id,
            name="Smoke Tenant B",
            slug=slug_b,
            api_key_hash="hash_b",
            plan_tier="free",
        )
        session.add_all([tenant_a, tenant_b])

    print("  [INFO] Seeded Tenant A and Tenant B")

    # 2. Seed Bot and Document in Tenant A's session
    async with tenant_session(tenant_a_id) as session:
        bot_a = Bot(
            id=bot_a_id,
            tenant_id=tenant_a_id,
            name="Smoke Bot A",
            slug=bot_slug,
            widget_key_hash=hash_widget_key("wgt_" + secrets.token_urlsafe(32)),
            status="active",
        )
        session.add(bot_a)
        doc_a = Document(
            id=doc_a_id,
            tenant_id=tenant_a_id,
            bot_id=bot_a_id,
            original_filename="secret_doc_a.pdf",
            status="ready",
        )
        session.add(doc_a)

    print("  [INFO] Seeded Bot A and Document A under Tenant A session")

    # 3. From Tenant B's session, attempt exact-ID read of Tenant A's document and bot
    async with tenant_session(tenant_b_id) as session:
        res_doc = await session.execute(
            select(Document).where(Document.id == doc_a_id)
        )
        leak_doc = res_doc.scalar_one_or_none()
        assert leak_doc is None, f"Cross-tenant leak! Tenant B read Document A: {leak_doc}"

        res_bot = await session.execute(
            select(Bot).where(Bot.id == bot_a_id)
        )
        leak_bot = res_bot.scalar_one_or_none()
        assert leak_bot is None, f"Cross-tenant leak! Tenant B read Bot A: {leak_bot}"

    print("  [PASS] Cross-tenant read by exact ID returned 0 rows (Document A and Bot A invisible to Tenant B)")

    # 4. Cleanup test rows
    async with tenant_session(tenant_a_id) as session:
        await session.execute(delete(Document).where(Document.id == doc_a_id))
        await session.execute(delete(Bot).where(Bot.id == bot_a_id))

    async with platform_session() as session:
        await session.execute(
            delete(Tenant).where(Tenant.id.in_([tenant_a_id, tenant_b_id]))
        )

    # 5. Confirm no leftover rows
    async with platform_session() as session:
        res_t = await session.execute(
            select(func.count()).select_from(Tenant).where(Tenant.id.in_([tenant_a_id, tenant_b_id]))
        )
        leftover_t = res_t.scalar_one()

        res_b = await session.execute(
            select(func.count()).select_from(Bot).where(Bot.id == bot_a_id)
        )
        leftover_b = res_b.scalar_one()

        res_d = await session.execute(
            select(func.count()).select_from(Document).where(Document.id == doc_a_id)
        )
        leftover_d = res_d.scalar_one()

        assert leftover_t == 0 and leftover_b == 0 and leftover_d == 0, (
            f"Leftover rows detected! Tenants: {leftover_t}, Bots: {leftover_b}, Docs: {leftover_d}"
        )
        print(f"  [PASS] Cleanup confirmed: leftover tenants={leftover_t}, bots={leftover_b}, documents={leftover_d}")


async def check_3_resolve_widget_key():
    print("\n--- Check 3: resolve_widget_key() SECURITY DEFINER function ---")
    tenant_id = uuid.uuid4()
    bot_id = uuid.uuid4()
    raw_widget_key = "wgt_" + secrets.token_urlsafe(32)
    key_hash = hash_widget_key(raw_widget_key)
    slug = f"wgt-tenant-{tenant_id.hex[:8]}"
    bot_slug = f"wgt-bot-{bot_id.hex[:8]}"

    # Seed tenant and bot
    async with platform_session() as session:
        tenant = Tenant(
            id=tenant_id,
            name="Widget Key Test Tenant",
            slug=slug,
            api_key_hash="hash_widget_test",
            plan_tier="free",
        )
        session.add(tenant)

    async with tenant_session(tenant_id) as session:
        bot = Bot(
            id=bot_id,
            tenant_id=tenant_id,
            name="Widget Key Test Bot",
            slug=bot_slug,
            widget_key_hash=key_hash,
            status="active",
        )
        session.add(bot)

    try:
        # Call resolve_widget_key in platform_session (runs as cortexa_app with no app.tenant_id set)
        async with platform_session() as session:
            result = await session.execute(
                text("SELECT bot_id, tenant_id, status FROM public.resolve_widget_key(:hash)"),
                {"hash": key_hash},
            )
            row = result.one_or_none()
            assert row is not None, "resolve_widget_key returned no row for valid active bot key"
            res_bot_id, res_tenant_id, res_status = row
            assert UUID(str(res_bot_id)) == bot_id, f"bot_id mismatch: {res_bot_id} != {bot_id}"
            assert UUID(str(res_tenant_id)) == tenant_id, f"tenant_id mismatch: {res_tenant_id} != {tenant_id}"
            assert res_status == "active", f"status mismatch: {res_status}"
            print(f"  [PASS] Valid widget key resolved: bot_id={res_bot_id}, tenant_id={res_tenant_id}, status={res_status}")

            # Test unknown hash
            fake_hash = hash_widget_key("wgt_unknown_key_12345678901234567890")
            result_fake = await session.execute(
                text("SELECT bot_id, tenant_id, status FROM public.resolve_widget_key(:hash)"),
                {"hash": fake_hash},
            )
            row_fake = result_fake.one_or_none()
            assert row_fake is None, f"Expected None for unknown hash, got: {row_fake}"
            print("  [PASS] Unknown widget key safely returns 0 rows")

    finally:
        async with tenant_session(tenant_id) as session:
            await session.execute(delete(Bot).where(Bot.id == bot_id))
        async with platform_session() as session:
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))


async def check_4_concurrent_sessions():
    print("\n--- Check 4: 20 concurrent sessions over transaction pooler (port 6543) ---")

    async def single_worker(worker_id: int):
        dummy_tenant = uuid.uuid4()
        async with tenant_session(dummy_tenant) as session:
            # Execute multiple statements in the same session
            res_user = await session.execute(text("SELECT current_user"))
            user = res_user.scalar_one()
            assert user == settings.APP_DB_ROLE

            res_val = await session.execute(
                text("SELECT CAST(:worker_id AS integer) as wid, current_setting('app.tenant_id', true) as tid"),
                {"worker_id": worker_id},
            )
            wid, tid = res_val.one()
            assert wid == worker_id
            assert tid == str(dummy_tenant)

            res_cnt = await session.execute(
                select(func.count()).select_from(Tenant)
            )
            _ = res_cnt.scalar_one()

    tasks = [single_worker(i) for i in range(20)]
    await asyncio.gather(*tasks)
    print("  [PASS] 20 concurrent sessions completed successfully with zero prepared-statement errors")


async def main():
    print("=== Cortexa Transaction Pooler (Port 6543) Smoke Test ===\n")
    try:
        await check_1_current_user()
        await check_2_cross_tenant_isolation()
        await check_3_resolve_widget_key()
        await check_4_concurrent_sessions()
        print("\n=================================================================")
        print("  ALL TRANSACTION POOLER CHECKS PASSED (PORT 6543)")
        print("=================================================================\n")
    except Exception as e:
        print(f"\n[FAIL] Transaction pooler smoke test failed: {e}", file=sys.stderr)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
