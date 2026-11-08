#!/usr/bin/env python3
"""
verify_supabase_rls.py -- Supabase RLS Verification Script
===========================================================

Purpose
-------
Run this script DIRECTLY AGAINST YOUR SUPABASE PROJECT before pointing
the application at it.  It proves, at the database level, that:

  Check 1  -- postgres has rolsuper OR rolbypassrls (confirming the
              bypass-RLS risk is real and APP_DB_ROLE is not optional).
              Passes if either attribute is true; prints both values.

  Check 2a -- cortexa_app is NOT a superuser (rolsuper = false)
  Check 2b -- cortexa_app does NOT bypass RLS (rolbypassrls = false)
  Check 3  -- a cross-tenant read executed AS cortexa_app returns zero
              rows for another tenant's data (RLS enforced, not theoretical)
  Check 4  -- with app.tenant_id unset, cortexa_app returns zero rows
              (fails closed, not open)
  Check 5  -- all test rows seeded by Checks 3/4 are absent after
              rollback (no leftover verification artifacts)
  Check 6  -- Supabase Data API roles (anon, authenticated) have NO
              access to public.tenants or public.platform_admins, and
              cannot EXECUTE public.resolve_widget_key(text).
              Skipped with an INFO line when roles do not exist (local).

Checks 2a, 2b, 3, 4, 6 are the real pass/fail gates (when Data API roles exist).
Check 1 is informational -- it characterises postgres but does not block
the script.  It is expected to be true; if false it is merely surprising.
Check 5 is a post-rollback proof; if it fails something is very wrong
with the transaction handling of this script itself.

Connection note -- which URL to use
-------------------------------------
This script can accept ANY of the following URL formats:

  Direct connection (port 5432):
    postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres
    Works from machines with IPv6 connectivity to Supabase.

  Session pooler (port 5432 on the pooler host, IPv4-capable):
    postgresql://postgres.REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
    Use this from machines where the direct URL is not reachable (IPv6-only
    Supabase direct connections fail on IPv4-only networks).

  Transaction pooler (port 6543):
    postgresql://postgres.REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
    This is what the APPLICATION uses at runtime (configured in DATABASE_URL).
    SET LOCAL ROLE DOES work through the transaction pooler when issued inside
    a transaction -- it is a Postgres wire-protocol command, not a pooler-level
    command.  The pooler forwards it to the backend.  What the transaction
    pooler does NOT support is session-level SET ROLE (outside a transaction)
    and PREPARE TRANSACTION.  database.py only ever issues SET LOCAL inside
    BEGIN...COMMIT, so the app path is safe.
    WARNING for this script: because each psycopg2 statement is its own
    transaction (autocommit=False with explicit conn.rollback()), SET LOCAL
    ROLE issued outside a BEGIN block has no effect.  Use the direct or
    session pooler URL for this script.

How to run (Python)
--------------------
  pip install psycopg2-binary
  DATABASE_URL="postgresql://postgres:PASSWORD@db.REF.supabase.co:5432/postgres" \
      python verify_supabase_rls.py

How to run (pure SQL -- paste into Supabase SQL Editor)
--------------------------------------------------------
  Run this script with no DATABASE_URL set to print the raw SQL block.
  Paste that block into Supabase > SQL Editor > New query and run it.

What a passing run looks like
------------------------------
  [INFO] postgres: rolsuper=True, rolbypassrls=True -- bypass risk confirmed
  [PASS] Check 1: postgres has a bypass-RLS attribute (rolsuper or rolbypassrls)
  [PASS] Check 2a: cortexa_app is NOT a superuser
  [PASS] Check 2b: cortexa_app does NOT bypass RLS
  [PASS] Check 3: cross-tenant read blocked (0 rows)
  [PASS] Check 4: no tenant context returns 0 rows (fails closed)
  [PASS] Check 5: no leftover verification rows in tenants or documents
  [PASS] Check 6: Data API roles have NO access to sensitive tables or functions
                  (or [INFO] Check 6 skipped when roles do not exist locally)
  =================================================================
  ALL CHECKS PASSED -- RLS is correctly enforced for cortexa_app
  =================================================================
"""

import os
import sys
import uuid


# ---------------------------------------------------------------------------
# Constants -- keep in sync with migration 0005
# ---------------------------------------------------------------------------
APP_ROLE = "cortexa_app"


# ---------------------------------------------------------------------------
# Pure SQL version (paste into Supabase SQL Editor when no Python available)
# ---------------------------------------------------------------------------
PURE_SQL = r"""
-- ===========================================================================
-- Cortexa RLS Verification -- paste into Supabase SQL Editor
-- Run as the postgres role (the default in the SQL Editor).
-- ===========================================================================
-- Expected NOTICE output:
--   PASS: Check 1 -- postgres has a bypass-RLS attribute
--   PASS: Check 2 -- cortexa_app: rolsuper=false, rolbypassrls=false
--   PASS: Check 3 -- cross-tenant read blocked (count=0)
--   PASS: Check 4 -- no tenant context returns zero rows (count=0)
--   PASS: Check 5 -- no leftover rows
--   ALL CHECKS PASSED
-- ===========================================================================

DO $$
DECLARE
    v_rolsuper      bool;
    v_rolbypassrls  bool;
    v_app_super     bool;
    v_app_bypass    bool;
    v_tenant_a      uuid := gen_random_uuid();
    v_tenant_b      uuid := gen_random_uuid();
    v_bot_id        uuid := gen_random_uuid();
    v_doc_id        uuid := gen_random_uuid();
    v_bot_hash      text := replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '');
    v_count         int;
    v_leftover      int;
BEGIN
    -- -----------------------------------------------------------------------
    -- Check 1: postgres bypass-RLS risk characterisation.
    -- Passes if rolsuper OR rolbypassrls is true.
    -- Prints both values regardless.
    -- -----------------------------------------------------------------------
    SELECT rolsuper, rolbypassrls
    INTO v_rolsuper, v_rolbypassrls
    FROM pg_roles
    WHERE rolname = 'postgres';

    RAISE NOTICE 'INFO: postgres rolsuper=%, rolbypassrls=%', v_rolsuper, v_rolbypassrls;

    IF v_rolsuper OR v_rolbypassrls THEN
        RAISE NOTICE 'PASS: Check 1 -- postgres has a bypass-RLS attribute (risk confirmed, APP_DB_ROLE is required)';
    ELSE
        RAISE WARNING 'WARN: Check 1 -- postgres has NEITHER rolsuper NOR rolbypassrls; unusual Supabase config';
    END IF;

    -- -----------------------------------------------------------------------
    -- Check 2: cortexa_app must have rolsuper=false AND rolbypassrls=false.
    -- -----------------------------------------------------------------------
    SELECT rolsuper, rolbypassrls
    INTO v_app_super, v_app_bypass
    FROM pg_roles
    WHERE rolname = 'cortexa_app';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'FAIL: cortexa_app role does not exist -- run: alembic upgrade 0005';
    END IF;

    RAISE NOTICE 'INFO: cortexa_app rolsuper=%, rolbypassrls=%', v_app_super, v_app_bypass;

    IF v_app_super THEN
        RAISE EXCEPTION 'FAIL: Check 2a -- cortexa_app IS a superuser; RLS bypassed';
    END IF;
    IF v_app_bypass THEN
        RAISE EXCEPTION 'FAIL: Check 2b -- cortexa_app has BYPASSRLS; RLS bypassed';
    END IF;
    RAISE NOTICE 'PASS: Check 2 -- cortexa_app: rolsuper=false, rolbypassrls=false';

    -- -----------------------------------------------------------------------
    -- Seed test data as postgres (bypasses RLS -- intentional for setup).
    -- ALL inserts are inside this transaction; they roll back at the end.
    -- Note: documents.bot_id is NOT NULL (migration 0003), so we seed a bot
    -- for Tenant A first.
    -- -----------------------------------------------------------------------
    INSERT INTO tenants (id, name, slug, api_key_hash, plan_tier) VALUES
        (v_tenant_a, 'Verify Tenant A', 'verify-a-'||left(v_tenant_a::text,8), 'noop', 'free'),
        (v_tenant_b, 'Verify Tenant B', 'verify-b-'||left(v_tenant_b::text,8), 'noop', 'free');

    INSERT INTO bots (id, tenant_id, name, slug, widget_key_hash, status)
    VALUES (
        v_bot_id,
        v_tenant_a,
        'Verify Bot A',
        'verify-bot-'||left(v_bot_id::text,8),
        v_bot_hash,
        'active'
    );

    INSERT INTO documents (id, tenant_id, bot_id, original_filename, status)
    VALUES (v_doc_id, v_tenant_a, v_bot_id, 'secret.pdf', 'ready');

    -- -----------------------------------------------------------------------
    -- Check 3: AS cortexa_app scoped to Tenant B, read Tenant A's document.
    -- Must return 0 rows.
    -- -----------------------------------------------------------------------
    SET LOCAL ROLE cortexa_app;
    PERFORM set_config('app.tenant_id', v_tenant_b::text, true);
    SELECT COUNT(*) INTO v_count FROM documents WHERE id = v_doc_id;
    RESET ROLE;

    IF v_count > 0 THEN
        RAISE EXCEPTION 'FAIL: Check 3 -- cortexa_app CAN read cross-tenant data (count=%)', v_count;
    END IF;
    RAISE NOTICE 'PASS: Check 3 -- cross-tenant read blocked (count=0)';

    -- -----------------------------------------------------------------------
    -- Check 4: AS cortexa_app with NO tenant_id set, read anything.
    -- Must return 0 rows (fail-closed behaviour).
    -- -----------------------------------------------------------------------
    SET LOCAL ROLE cortexa_app;
    PERFORM set_config('app.tenant_id', '', true);
    SELECT COUNT(*) INTO v_count FROM documents WHERE id = v_doc_id;
    RESET ROLE;

    IF v_count > 0 THEN
        RAISE EXCEPTION 'FAIL: Check 4 -- unset tenant_id leaks data (count=%)', v_count;
    END IF;
    RAISE NOTICE 'PASS: Check 4 -- no tenant context returns zero rows (count=0)';

    -- -----------------------------------------------------------------------
    -- Explicit cleanup BEFORE the implicit rollback proves the intent.
    -- The transaction rolls back anyway, but this DELETE + subsequent
    -- count proves cleanup is deliberate, not accidental.
    -- -----------------------------------------------------------------------
    DELETE FROM documents WHERE id = v_doc_id;
    DELETE FROM bots      WHERE id = v_bot_id;
    DELETE FROM tenants   WHERE id IN (v_tenant_a, v_tenant_b);

    -- -----------------------------------------------------------------------
    -- Check 5: verify no leftover rows survive.
    -- -----------------------------------------------------------------------
    SELECT COUNT(*) INTO v_leftover
    FROM (
        SELECT id FROM tenants WHERE id IN (v_tenant_a, v_tenant_b)
        UNION ALL
        SELECT id FROM bots WHERE id = v_bot_id
        UNION ALL
        SELECT id FROM documents WHERE id = v_doc_id
    ) t;

    IF v_leftover > 0 THEN
        RAISE EXCEPTION 'FAIL: Check 5 -- % row(s) still exist after delete', v_leftover;
    END IF;
    RAISE NOTICE 'PASS: Check 5 -- no leftover rows';

    -- -----------------------------------------------------------------------
    -- Check 6: Data API roles lockdown (anon, authenticated).
    -- When the roles exist (Supabase), assert has_table_privilege('public.tenants', 'SELECT')
    -- is false, has_table_privilege('public.platform_admins', 'SELECT') is false,
    -- and has_function_privilege('public.resolve_widget_key(text)', 'EXECUTE') is false.
    -- Skipped with an INFO notice when roles do not exist (e.g. local test DB).
    -- -----------------------------------------------------------------------
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN ('anon', 'authenticated')) THEN
        RAISE NOTICE 'INFO: Check 6 -- anon/authenticated roles do not exist (local DB) -- skipping Data API lockdown check';
    ELSE
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            IF has_table_privilege('anon', 'public.tenants', 'SELECT') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role anon has SELECT on public.tenants';
            END IF;
            IF has_table_privilege('anon', 'public.platform_admins', 'SELECT') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role anon has SELECT on public.platform_admins';
            END IF;
            IF has_function_privilege('anon', 'public.resolve_widget_key(text)', 'EXECUTE') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role anon has EXECUTE on public.resolve_widget_key';
            END IF;
        END IF;

        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            IF has_table_privilege('authenticated', 'public.tenants', 'SELECT') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role authenticated has SELECT on public.tenants';
            END IF;
            IF has_table_privilege('authenticated', 'public.platform_admins', 'SELECT') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role authenticated has SELECT on public.platform_admins';
            END IF;
            IF has_function_privilege('authenticated', 'public.resolve_widget_key(text)', 'EXECUTE') THEN
                RAISE EXCEPTION 'FAIL: Check 6 -- role authenticated has EXECUTE on public.resolve_widget_key';
            END IF;
        END IF;

        RAISE NOTICE 'PASS: Check 6 -- Data API roles (anon, authenticated) have NO access to sensitive tables or resolve_widget_key';
    END IF;

    RAISE NOTICE 'ALL CHECKS PASSED';

    -- Roll back the entire transaction -- nothing is committed.
    -- Uses custom SQLSTATE 'RB001' so real RAISE EXCEPTION failures (P0001) are not swallowed.
    RAISE EXCEPTION 'ROLLBACK_SENTINEL' USING ERRCODE = 'RB001';

EXCEPTION
    WHEN SQLSTATE 'RB001' THEN
        -- Expected rollback path -- all test data discarded.
        RAISE NOTICE 'Transaction rolled back -- no test data was committed.';
END
$$;
"""


def run_python_checks(database_url: str) -> None:
    """
    Run all 5 verification checks via a Python psycopg2 connection.

    Use the direct connection URL (port 5432) or the session pooler URL
    (also port 5432 on the pooler host).  Do NOT use the transaction
    pooler (port 6543) for this script -- SET LOCAL ROLE requires being
    inside a transaction block, and psycopg2's per-statement execution
    model does not wrap each statement in BEGIN...COMMIT automatically.
    The application (database.py) is fine with the transaction pooler
    because it always wraps queries in session.begin().
    """
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed.  Run:  pip install psycopg2-binary")
        print()
        print("Alternatively, paste the SQL block below into Supabase > SQL Editor:")
        print(PURE_SQL)
        sys.exit(1)

    # Accept postgresql+asyncpg:// (the app format) -- strip to plain postgresql://
    url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = psycopg2.connect(url)
    # autocommit=False -- psycopg2 default; all statements run inside one transaction.
    conn.autocommit = False
    cur = conn.cursor()
    passed = 0
    failed = 0

    def ok(label: str, msg: str) -> None:
        nonlocal passed
        passed += 1
        print(f"  [PASS] {label}: {msg}")

    def info(msg: str) -> None:
        print(f"  [INFO] {msg}")

    def warn(msg: str) -> None:
        print(f"  [WARN] {msg}")

    def fail(label: str, msg: str) -> None:
        nonlocal failed
        failed += 1
        print(f"  [FAIL] {label}: {msg}", file=sys.stderr)

    print("\n=== Cortexa Supabase RLS Verification ===\n")

    # ------------------------------------------------------------------
    # Check 1: postgres bypass-RLS risk characterisation (informational).
    # Passes if rolsuper OR rolbypassrls is true.
    # ------------------------------------------------------------------
    cur.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'postgres'"
    )
    row = cur.fetchone()
    if row is None:
        warn("'postgres' role not found -- unexpected Supabase configuration")
    else:
        pg_super, pg_bypass = row
        info(f"postgres: rolsuper={pg_super}, rolbypassrls={pg_bypass}")
        if pg_super or pg_bypass:
            ok("Check 1", "postgres has a bypass-RLS attribute -- risk is real, APP_DB_ROLE is required")
        else:
            warn("Check 1: postgres has NEITHER rolsuper NOR rolbypassrls -- unusual; verify config")

    # ------------------------------------------------------------------
    # Check 2a/2b: cortexa_app must have rolsuper=False, rolbypassrls=False.
    # ------------------------------------------------------------------
    cur.execute(
        "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s", (APP_ROLE,)
    )
    row = cur.fetchone()
    if row is None:
        fail("Check 2", f"'{APP_ROLE}' role does not exist -- run: alembic upgrade 0005")
        conn.rollback()
        cur.close()
        conn.close()
        _summary(passed, failed)
        return

    app_super, app_bypass = row
    info(f"cortexa_app: rolsuper={app_super}, rolbypassrls={app_bypass}")

    if not app_super:
        ok("Check 2a", f"'{APP_ROLE}' is NOT a superuser")
    else:
        fail("Check 2a", f"'{APP_ROLE}' IS a superuser -- ALTER ROLE {APP_ROLE} NOSUPERUSER")

    if not app_bypass:
        ok("Check 2b", f"'{APP_ROLE}' does NOT bypass RLS")
    else:
        fail("Check 2b", f"'{APP_ROLE}' has BYPASSRLS -- ALTER ROLE {APP_ROLE} NOBYPASSRLS")

    # ------------------------------------------------------------------
    # Checks 3, 4, 5: live isolation proof with guaranteed cleanup.
    # All operations are inside a single transaction that is ALWAYS rolled
    # back -- on success, on failure, and on exception.
    # ------------------------------------------------------------------
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    bot_id   = uuid.uuid4()
    doc_id   = uuid.uuid4()
    bot_hash = uuid.uuid4().hex + uuid.uuid4().hex

    try:
        # Seed test data as postgres (superuser / bypassrls for setup).
        cur.execute(
            "INSERT INTO tenants (id, name, slug, api_key_hash, plan_tier) VALUES "
            "(%s, 'Verify Tenant A', %s, 'noop', 'free'), "
            "(%s, 'Verify Tenant B', %s, 'noop', 'free')",
            (
                str(tenant_a), f"verify-a-{str(tenant_a)[:8]}",
                str(tenant_b), f"verify-b-{str(tenant_b)[:8]}",
            ),
        )
        cur.execute(
            "INSERT INTO bots (id, tenant_id, name, slug, widget_key_hash, status) "
            "VALUES (%s, %s, 'Verify Bot A', %s, %s, 'active')",
            (
                str(bot_id), str(tenant_a),
                f"verify-bot-{str(bot_id)[:8]}", bot_hash,
            ),
        )
        cur.execute(
            "INSERT INTO documents (id, tenant_id, bot_id, original_filename, status) "
            "VALUES (%s, %s, %s, 'secret.pdf', 'ready')",
            (str(doc_id), str(tenant_a), str(bot_id)),
        )

        # Check 3: AS cortexa_app, scoped to Tenant B, try to read Tenant A's doc.
        cur.execute("BEGIN")  # explicit savepoint so SET LOCAL applies
        cur.execute(f"SET LOCAL ROLE {APP_ROLE}")
        cur.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_b),))
        cur.execute("SELECT COUNT(*) FROM documents WHERE id = %s", (str(doc_id),))
        count = cur.fetchone()[0]
        cur.execute("RESET ROLE")

        if count == 0:
            ok("Check 3", f"'{APP_ROLE}' cannot read Tenant A's doc from Tenant B's session (count=0)")
        else:
            fail("Check 3", f"'{APP_ROLE}' CAN read cross-tenant data (count={count}) -- RLS BROKEN")

        # Check 4: AS cortexa_app with no tenant_id, must return zero rows.
        cur.execute(f"SET LOCAL ROLE {APP_ROLE}")
        cur.execute("SELECT set_config('app.tenant_id', '', true)")
        cur.execute("SELECT COUNT(*) FROM documents WHERE id = %s", (str(doc_id),))
        count = cur.fetchone()[0]
        cur.execute("RESET ROLE")

        if count == 0:
            ok("Check 4", "no tenant context returns 0 rows -- fails closed correctly")
        else:
            fail("Check 4", f"no tenant context leaks {count} row(s) -- RLS BROKEN")

        # Explicit DELETE before rollback (proves intent; rollback removes them anyway).
        cur.execute("DELETE FROM documents WHERE id = %s", (str(doc_id),))
        cur.execute("DELETE FROM bots WHERE id = %s", (str(bot_id),))
        cur.execute(
            "DELETE FROM tenants WHERE id = ANY(%s::uuid[])",
            ([str(tenant_a), str(tenant_b)],),
        )

    finally:
        # ALWAYS roll back -- no verification artifacts are ever committed.
        conn.rollback()

    # ------------------------------------------------------------------
    # Check 5: post-rollback confirmation -- no leftover rows in DB.
    # Open a fresh transaction to verify the state outside our rolled-back txn.
    # ------------------------------------------------------------------
    cur.execute(
        "SELECT COUNT(*) FROM tenants WHERE id = ANY(%s::uuid[])",
        ([str(tenant_a), str(tenant_b)],),
    )
    leftover_tenants = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM bots WHERE id = %s",
        (str(bot_id),),
    )
    leftover_bots = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM documents WHERE id = %s",
        (str(doc_id),),
    )
    leftover_docs = cur.fetchone()[0]
    conn.rollback()

    if leftover_tenants == 0 and leftover_bots == 0 and leftover_docs == 0:
        ok("Check 5", "no leftover verification rows in tenants, bots, or documents")
    else:
        fail(
            "Check 5",
            f"leftover rows: tenants={leftover_tenants}, bots={leftover_bots}, documents={leftover_docs} -- "
            "transaction rollback did not work; investigate this script",
        )

    # ------------------------------------------------------------------
    # Check 6: Supabase Data API roles lockdown (anon, authenticated).
    # Skipped with an INFO line when roles do not exist (e.g. local test DB).
    # ------------------------------------------------------------------
    cur.execute(
        "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
    )
    existing_data_roles = [r[0] for r in cur.fetchall()]

    if not existing_data_roles:
        info(
            "Check 6: 'anon' / 'authenticated' roles not present (local DB) -- skipping Data API lockdown check"
        )
    else:
        check6_failed = False
        for role in existing_data_roles:
            cur.execute(
                "SELECT has_table_privilege(%s, 'public.tenants', 'SELECT')",
                (role,),
            )
            can_sel_tenants = cur.fetchone()[0]

            cur.execute(
                "SELECT has_table_privilege(%s, 'public.platform_admins', 'SELECT')",
                (role,),
            )
            can_sel_admins = cur.fetchone()[0]

            cur.execute(
                "SELECT has_function_privilege(%s, 'public.resolve_widget_key(text)', 'EXECUTE')",
                (role,),
            )
            can_exec_fn = cur.fetchone()[0]

            if can_sel_tenants:
                fail(
                    "Check 6",
                    f"role '{role}' HAS SELECT on public.tenants -- run migration 0006",
                )
                check6_failed = True
            if can_sel_admins:
                fail(
                    "Check 6",
                    f"role '{role}' HAS SELECT on public.platform_admins -- run migration 0006",
                )
                check6_failed = True
            if can_exec_fn:
                fail(
                    "Check 6",
                    f"role '{role}' HAS EXECUTE on public.resolve_widget_key(text) -- run migration 0006",
                )
                check6_failed = True

        if not check6_failed:
            ok(
                "Check 6",
                f"Data API roles ({', '.join(existing_data_roles)}) have NO access to tenants, platform_admins, or resolve_widget_key",
            )

    cur.close()
    conn.close()
    _summary(passed, failed)


def _summary(passed: int, failed: int) -> None:
    print()
    print("=" * 65)
    # Check 1 is informational, not counted in pass/fail totals shown to user.
    # The real gates are Checks 2a, 2b, 3, 4, 5, and 6.
    if failed == 0:
        print(f"  ALL {passed} CHECKS PASSED -- RLS is correctly enforced")
        print(f"  Safe to connect the application to this Supabase project.")
    else:
        print(f"  {failed} CHECK(S) FAILED -- DO NOT connect the application.")
        print(f"  Passed: {passed}  |  Failed: {failed}")
        print()
        print("  Next steps:")
        print("  1. Confirm migration 0005 ran:  alembic current")
        print("  2. Check role: SELECT rolname, rolsuper, rolbypassrls")
        print("     FROM pg_roles WHERE rolname IN ('postgres','cortexa_app');")
        print("  3. Check .env: APP_DB_ROLE=cortexa_app  (must not be blank)")
        print("  4. Check membership: SELECT * FROM pg_auth_members m")
        print("     JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles u ON u.oid=m.member")
        print("     WHERE r.rolname='cortexa_app' AND u.rolname='postgres';")
    print("=" * 65)
    print()
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print(__doc__)
        print()
        print("--- PURE SQL VERSION (paste into Supabase SQL Editor) ---")
        print(PURE_SQL)
        sys.exit(0)
    run_python_checks(db_url)
