import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://postgres:cortexa_test@localhost:5434/cortexa_test")

    rows = await conn.fetch(
        "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = ANY(ARRAY['postgres','cortexa_app'])"
    )
    print("=== pg_roles ===")
    for r in rows:
        print("  rolname=" + r["rolname"] + " rolsuper=" + str(r["rolsuper"]) + " rolbypassrls=" + str(r["rolbypassrls"]))

    mem = await conn.fetch(
        "SELECT u.rolname AS member, r.rolname AS role "
        "FROM pg_auth_members m "
        "JOIN pg_roles r ON r.oid = m.roleid "
        "JOIN pg_roles u ON u.oid = m.member "
        "WHERE r.rolname = 'cortexa_app'"
    )
    print("=== membership (who can SET ROLE cortexa_app) ===")
    for m in mem:
        print("  " + m["member"] + " is member of " + m["role"])

    fn = await conn.fetch(
        "SELECT proname, prosecdef, proowner::regrole::text AS owner "
        "FROM pg_proc WHERE proname = 'resolve_widget_key'"
    )
    print("=== resolve_widget_key function ===")
    if fn:
        for f in fn:
            print("  name=" + f["proname"] + " SECURITY_DEFINER=" + str(f["prosecdef"]) + " owner=" + f["owner"])
    else:
        print("  NOT FOUND")

    grant = await conn.fetch(
        "SELECT grantee, privilege_type "
        "FROM information_schema.routine_privileges "
        "WHERE routine_name = 'resolve_widget_key'"
    )
    print("=== EXECUTE grants on resolve_widget_key ===")
    for g in grant:
        print("  grantee=" + g["grantee"] + " privilege=" + g["privilege_type"])

    await conn.close()

asyncio.run(check())
