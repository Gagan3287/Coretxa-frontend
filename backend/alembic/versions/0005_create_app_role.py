"""create cortexa_app role with NOSUPERUSER NOBYPASSRLS and grant minimum required privileges

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-19

WHY THIS MIGRATION EXISTS
--------------------------
Supabase (and any managed Postgres where you connect via DATABASE_URL as the
"postgres" role) has a critical, documented behaviour: the "postgres" role is a
SUPERUSER (or has BYPASSRLS on some Supabase plan tiers).  Either attribute
causes every query run as postgres to bypass Row-Level Security, even when a
table has FORCE ROW LEVEL SECURITY applied.

This migration creates a dedicated application role -- cortexa_app -- that:
  * is NOT a superuser        (NOSUPERUSER, the default, stated explicitly)
  * does NOT bypass RLS       (NOBYPASSRLS, the default, stated explicitly)
  * has exactly the DML privileges the application needs, and no more
  * has NOLOGIN (the app never connects AS this role; it SETs LOCAL ROLE to it)

How it works at runtime
-----------------------
DATABASE_URL still uses "postgres" so that Alembic itself can run DDL
(CREATE TABLE, ALTER TABLE, etc.).  But database.py wraps EVERY tenant query
in:

    SET LOCAL ROLE cortexa_app

This drops the connection from postgres to cortexa_app for the duration of
that transaction ONLY.  SET LOCAL automatically resets to the original role at
COMMIT or ROLLBACK -- it can never leak across requests on a pooled connection.

Because cortexa_app has neither SUPERUSER nor BYPASSRLS, Postgres ENFORCES
the FORCE ROW LEVEL SECURITY tables' RLS policies for every statement executed
while that role is active.

GRANT cortexa_app TO postgres — why this is required on Supabase
----------------------------------------------------------------
On Supabase, the "postgres" role is NOT a true Postgres superuser at the
system level; it has elevated privileges granted by Supabase but may lack the
ability to SET LOCAL ROLE to an arbitrary role unless it is a MEMBER of that
role.  Specifically:

  SET LOCAL ROLE <role>

is equivalent to SET ROLE, which in Postgres requires the current session user
to either be a superuser OR be a member of the target role.  On Supabase,
postgres may fail this check even though it owns all the tables.

The fix is explicit: GRANT cortexa_app TO postgres.  This is idempotent (the
DO block checks pg_auth_members before executing) and does NOT grant cortexa_app
any new privileges -- it only allows postgres to assume that role within a
transaction via SET ROLE / SET LOCAL ROLE.

On a real local Postgres where postgres IS a superuser, this GRANT is a no-op
(superusers can SET ROLE to anything regardless of membership), so the
migration is safe to run in both environments.

SECURITY DEFINER function: resolve_widget_key()
-----------------------------------------------
get_bot_context() in deps.py calls platform_session() to look up a bot by its
widget_key_hash.  After this migration, platform_session() does
  SET LOCAL ROLE cortexa_app
before any query.  But bots has FORCE ROW LEVEL SECURITY, and with no
app.tenant_id set in platform_session(), cortexa_app sees zero rows -- every
widget authentication request would 401.

The fix: a SQL function owned by postgres, defined with SECURITY DEFINER, that
runs the lookup as postgres (bypassing RLS) regardless of who calls it.  The
function is tightly scoped:
  * Takes only a hash string -- no tenant context, no raw key
  * Returns only bot_id, tenant_id, status -- not widget_key_hash, llm_overrides, etc.
  * REVOKE EXECUTE FROM PUBLIC prevents any role from calling it except those
    explicitly granted
  * GRANT EXECUTE TO cortexa_app is the only grant
  * SET search_path = '' + schema-qualified names prevent search-path injection

Sequence grants
---------------
Sequences in Postgres require USAGE (to call nextval()) and SELECT (to call
currval()/lastval()).  UUIDs in this project are generated application-side
(uuid.uuid4()), so sequence grants are belt-and-suspenders for any future
serial/bigserial columns and for Alembic's internal bookkeeping.

Downgrade
---------
The downgrade drops the function, revokes all grants, and drops the role.
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# The role name is defined once here so that the migration, the downgrade,
# and any future migration that references it can all be kept in sync by
# changing a single line.
APP_ROLE = "cortexa_app"

# All tenant-scoped tables whose RLS policies must be enforced.
# This list must stay in sync with the tables enumerated in 0001_initial_schema.py,
# 0002_add_bots.py, and any future migration that adds a new RLS-protected table.
RLS_TABLES = [
    "users",
    "documents",
    "document_versions",
    "chunks",
    "queries",
    "audit_log",
    "bots",
]

# Tables with no RLS that the app role still needs to read/write.
# - tenants: read for tenant lookup during auth; written only by platform_session
#   (which also does SET LOCAL ROLE so it benefits from the same grants).
# - platform_admins: read for platform-admin auth.
UNRESTRICTED_TABLES = [
    "tenants",
    "platform_admins",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create the role if it does not already exist.
    #
    # DO $$ ... $$ is idempotent -- safe to run on a database that was set
    # up outside Alembic (e.g. a restored snapshot) and already has the role.
    #
    # NOSUPERUSER and NOBYPASSRLS are both Postgres defaults for new roles,
    # but we state them EXPLICITLY so that:
    #   a) a future reader cannot wonder "did we forget these?", and
    #   b) the intent is self-documenting in the migration history.
    #
    # NOLOGIN: the app never authenticates directly as cortexa_app.
    #   DATABASE_URL = postgres (superuser) -> Alembic can run migrations.
    #   SET LOCAL ROLE cortexa_app -> RLS is enforced per-transaction.
    # ------------------------------------------------------------------
    op.execute(f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE}
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOINHERIT
                    NOLOGIN
                    NOBYPASSRLS;
            ELSE
                -- Role already exists: ensure BYPASSRLS and SUPERUSER are off.
                -- This defends against a manual ALTER that accidentally granted either.
                ALTER ROLE {APP_ROLE} NOBYPASSRLS NOSUPERUSER;
            END IF;
        END
        $$
    """)

    # ------------------------------------------------------------------
    # 1b. GRANT cortexa_app TO postgres (Supabase SET LOCAL ROLE fix).
    #
    # On Supabase, "postgres" is NOT a full Postgres superuser at the OS
    # level.  SET LOCAL ROLE to a role you are not a member of requires
    # either rolsuper=true OR membership in that role.  Without this GRANT,
    # every tenant_session() / platform_session() call would fail with:
    #   ERROR:  permission denied to set role "cortexa_app"
    #
    # Unconditional GRANT: On Postgres 16+, role creation automatically
    # creates a pg_auth_members row (with SET option false), which causes
    # IF NOT EXISTS guards on pg_auth_members to skip the explicit grant
    # that actually enables SET ROLE. Running the GRANT unconditionally
    # ensures postgres has proper membership and rights.
    # ------------------------------------------------------------------
    op.execute(f"GRANT {APP_ROLE} TO postgres")

    # ------------------------------------------------------------------
    # 2. Grant CONNECT on the database.
    #
    # Required so that SET LOCAL ROLE can activate this role within an
    # existing superuser connection.  current_database() is the Supabase
    # database name -- "postgres" by default on all Supabase projects.
    # ------------------------------------------------------------------
    op.execute(f"GRANT CONNECT ON DATABASE postgres TO {APP_ROLE}")

    # ------------------------------------------------------------------
    # 3. Grant USAGE on the public schema.
    #
    # Required to resolve any object name (table, sequence, function) in
    # the public schema.  Without this, every query fails with
    # "permission denied for schema public" even if table grants exist.
    # ------------------------------------------------------------------
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")

    # ------------------------------------------------------------------
    # 4. Grant DML on RLS-protected tables (SELECT/INSERT/UPDATE/DELETE).
    #
    # Deliberately NOT granting TRUNCATE or REFERENCES.
    # NOT granting ALTER, DROP, or any DDL -- those require ownership and
    # must remain with postgres so Alembic can run future migrations.
    # ------------------------------------------------------------------
    for table in RLS_TABLES:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO {APP_ROLE}"
        )

    # ------------------------------------------------------------------
    # 5. Grant DML on unrestricted (non-RLS) tables.
    #
    # These tables have no RLS policies -- they are intentionally outside
    # the tenant boundary.  The app role needs to read tenants for auth
    # lookups and platform_admins for admin login.
    # INSERT/UPDATE/DELETE are granted for platform_session use-cases
    # (tenant provisioning writes to tenants; admin creation writes to
    # platform_admins).
    # ------------------------------------------------------------------
    for table in UNRESTRICTED_TABLES:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE {table} TO {APP_ROLE}"
        )

    # ------------------------------------------------------------------
    # 6. Grant USAGE + SELECT on all sequences in public schema.
    #
    # USAGE  -> allows nextval() / setval() calls (needed for any serial PK)
    # SELECT -> allows currval() / lastval() (needed after an INSERT)
    # ------------------------------------------------------------------
    op.execute(
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}"
    )

    # ------------------------------------------------------------------
    # 7. Set DEFAULT PRIVILEGES so future tables/sequences created by
    #    Alembic (as the postgres superuser) automatically grant the app
    #    role the same permissions without requiring another migration.
    #
    #    Without this, every new migration that adds a table would need an
    #    explicit GRANT statement, and forgetting one would silently break
    #    app writes on that table in production.
    # ------------------------------------------------------------------
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
    )

    # ------------------------------------------------------------------
    # 8. Create resolve_widget_key() — SECURITY DEFINER bypass for widget auth.
    #
    # Problem: get_bot_context() calls platform_session(), which now does
    # SET LOCAL ROLE cortexa_app before any query.  The bots table has
    # FORCE ROW LEVEL SECURITY.  With no app.tenant_id set in a
    # platform_session, cortexa_app sees zero rows on bots — every widget
    # authentication request 401s.
    #
    # Solution: a SECURITY DEFINER function owned by postgres that performs
    # the widget_key_hash lookup running AS postgres (RLS bypass), returning
    # only the three columns the caller needs.
    #
    # Security properties:
    #   SET search_path = ''        — prevents search-path hijacking
    #   Schema-qualified names      — references are unambiguous even with
    #                                 a tampered search_path
    #   REVOKE EXECUTE FROM PUBLIC  — no role can call it by default
    #   GRANT EXECUTE TO cortexa_app — exactly one grantee
    #   Returns only bot_id, tenant_id, status — not the key hash itself,
    #     not llm_overrides, not any other sensitive column
    # ------------------------------------------------------------------
    op.execute(f"""
        CREATE OR REPLACE FUNCTION public.resolve_widget_key(p_hash text)
        RETURNS TABLE (bot_id uuid, tenant_id uuid, status text)
        LANGUAGE sql
        SECURITY DEFINER
        SET search_path = ''
        AS $$
            SELECT
                b.id        AS bot_id,
                b.tenant_id AS tenant_id,
                b.status    AS status
            FROM public.bots b
            WHERE b.widget_key_hash = p_hash
            LIMIT 1;
        $$;
    """)
    # Revoke from PUBLIC first (default grants EXECUTE to PUBLIC for SQL functions).
    op.execute(f"REVOKE EXECUTE ON FUNCTION public.resolve_widget_key(text) FROM PUBLIC")
    # Grant to the app role only.
    op.execute(f"GRANT EXECUTE ON FUNCTION public.resolve_widget_key(text) TO {APP_ROLE}")


def downgrade() -> None:
    # Revoke in reverse order of grant.
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {APP_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        f"REVOKE USAGE, SELECT ON SEQUENCES FROM {APP_ROLE}"
    )
    op.execute(
        f"REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE}"
    )
    for table in UNRESTRICTED_TABLES:
        op.execute(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE {table} FROM {APP_ROLE}"
        )
    for table in RLS_TABLES:
        op.execute(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLE {table} FROM {APP_ROLE}"
        )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    op.execute(f"REVOKE CONNECT ON DATABASE postgres FROM {APP_ROLE}")

    # Revoke role membership granted in step 1b.
    op.execute(f"REVOKE {APP_ROLE} FROM postgres")

    # Drop SECURITY DEFINER function.
    op.execute("DROP FUNCTION IF EXISTS public.resolve_widget_key(text)")

    # Clean up all privileges and dependent objects for the role in this database before dropping.
    op.execute(f"DROP OWNED BY {APP_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {APP_ROLE}")
