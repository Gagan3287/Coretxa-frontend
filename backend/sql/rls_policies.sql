-- ============================================================================
-- Row-Level Security policies for Cortexa.
--
-- Pattern: every tenant-scoped table gets ENABLE + FORCE row level security,
-- plus a single USING policy comparing tenant_id to the session-local
-- `app.tenant_id` setting.
--
-- The FORCE is the detail people miss: by default, the table OWNER bypasses
-- RLS. In most hosted setups (Supabase, Render+managed Postgres) your app
-- connects AS the table owner — so without FORCE, RLS silently does nothing
-- for your own application traffic. FORCE closes that gap.
--
-- `tenants` and `platform_admins` deliberately have NO policy here — see
-- app/models/tenant.py and app/models/platform_admin.py for why.
-- ============================================================================

-- USERS ----------------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- DOCUMENTS --------------------------------------------------------------
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_documents ON documents
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- DOCUMENT_VERSIONS -----------------------------------------------------
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_document_versions ON document_versions
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- CHUNKS ------------------------------------------------------------------
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_chunks ON chunks
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- QUERIES -------------------------------------------------------------------
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_queries ON queries
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- AUDIT_LOG -------------------------------------------------------------
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_audit_log ON audit_log
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Note: current_setting(..., true) with the second arg = true means "return
-- NULL instead of raising an error if unset" — so a request that forgets to
-- set app.tenant_id fails CLOSED (sees zero rows) rather than crashing or,
-- worse, silently seeing everything.
