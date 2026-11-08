"""lock down Supabase Data API roles (anon, authenticated, service_role)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-19

WHY THIS MIGRATION EXISTS
--------------------------
Supabase provides an auto-generated PostgREST Data API backed by three pre-existing
roles:
  * anon:          unauthenticated HTTP requests presenting the public anon key
  * authenticated: HTTP requests presenting a Supabase Auth user JWT
  * service_role:  requests presenting the service_role secret key (bypasses RLS)

By default, Supabase grants these roles broad permissions in the public schema,
and configures ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public to
automatically grant ALL on newly created tables, sequences, and functions.

For Cortexa:
  1. The application NEVER uses the Supabase Data API / PostgREST. All requests
     flow through the FastAPI backend, which authenticates via its own JWTs or
     widget keys and switches to the non-superuser cortexa_app role.
  2. While tenant tables have Row-Level Security, unrestricted tables like
     `tenants` and `platform_admins` do NOT have RLS. If `anon` or `authenticated`
     have SELECT privileges, anyone holding the public anon key could read tenant
     metadata or platform admin records via PostgREST.
  3. The resolve_widget_key(text) function is defined with SECURITY DEFINER and
     is intended exclusively for cortexa_app. Supabase default privileges grant
     EXECUTE to anon, authenticated, and service_role, bypassing the REVOKE FROM PUBLIC.

This migration locks down the Data API roles:
  1. REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated
  2. REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated
  3. REVOKE EXECUTE ON FUNCTION public.resolve_widget_key(text) FROM anon,
     authenticated, service_role
  4. ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON
     TABLES, SEQUENCES, and FUNCTIONS FROM anon, authenticated

Idempotence & Portability
-------------------------
Every statement is wrapped in a DO block checking pg_roles because these roles
exist on Supabase but do not exist in local development/test environments.
This migration is safe to run against any Postgres database.
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Revoke all table privileges from anon and authenticated.
    # 2. Revoke all sequence privileges from anon and authenticated.
    # 3. Revoke execute on resolve_widget_key from anon, authenticated, service_role.
    # 4. Alter default privileges so future objects are not exposed.
    #
    # All statements use dynamic SQL guarded by pg_roles checks.
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        DECLARE
            r text;
        BEGIN
            -- 1 & 2: Revoke table and sequence access from anon and authenticated
            FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
                    EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', r);
                END IF;
            END LOOP;

            -- 3: Revoke execute on resolve_widget_key from Data API roles
            FOREACH r IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE EXECUTE ON FUNCTION public.resolve_widget_key(text) FROM %I', r);
                END IF;
            END LOOP;

            -- 4: Revoke default privileges for future tables, sequences, functions
            FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM %I', r);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', r);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM %I', r);
                END IF;
            END LOOP;
        END
        $$;
    """)


def downgrade() -> None:
    # Restore default privileges if the roles exist.
    op.execute("""
        DO $$
        DECLARE
            r text;
        BEGIN
            FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES TO %I', r);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO %I', r);
                    EXECUTE format('ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO %I', r);
                END IF;
            END LOOP;
        END
        $$;
    """)
