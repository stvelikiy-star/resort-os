"""Only initialise a truly empty disposable MARINA demo PostgreSQL."""
import asyncio
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg
import bootstrap_marina_test
import bootstrap_owner


def demo_database_url(value):
    """Accept only the dedicated Compose database, never a name-prefix match."""
    parsed = urlsplit(value)
    if (parsed.scheme not in ("postgres", "postgresql")
            or parsed.hostname != "postgres" or parsed.port != 5432
            or parsed.username != "marina_demo" or parsed.path != "/marina_demo"
            or parsed.fragment):
        raise RuntimeError("Refusing non-demo PostgreSQL connection")
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if any(key == "schema" and val != "public" for key, val in query):
        raise RuntimeError("Refusing non-public demo schema")
    query = [(key, val) for key, val in query if key != "schema"]
    return urlunsplit(parsed._replace(query=urlencode(query)))


async def main():
    if os.environ.get("MARINA_DEMO_CONFIRM") != "EMPTY_SYNTHETIC_DB_ONLY":
        raise RuntimeError("Synthetic-only explicit guard required")
    if os.environ.get("APP_ENV") != "staging" or os.environ.get("PROPERTY_CODE") != "MARINA_DEMO":
        raise RuntimeError("Refusing to seed outside MARINA_DEMO staging")
    dsn = demo_database_url(os.environ["DATABASE_URL"])
    conn = await asyncpg.connect(dsn)
    try:
        properties = await conn.fetchval("SELECT count(*) FROM properties")
        tenants = await conn.fetchval("SELECT count(*) FROM tenants")
        if properties == 1 and tenants == 1:
            row = await conn.fetchrow(
                'SELECT p.code, t.code AS tenant_code FROM properties p '
                'JOIN tenants t ON t.id=p."tenantId"'
            )
            owner_count = await conn.fetchval(
                'SELECT count(*) FROM staff_users su JOIN properties p ON p.id=su."propertyId" '
                'WHERE p.code=$1 AND su.username=$2 AND su.role=\'OWNER\' AND su."isActive"=true',
                "MARINA_DEMO", os.environ.get("BOOTSTRAP_OWNER_USERNAME", "demo-owner").strip().lower()
            )
            # Room/category counts are editable through the real PMS.
            # Identity, rather than the initial fixture size, determines reuse.
            if row and row["tenant_code"] == "tenant_marina_demo" and row["code"] == "MARINA_DEMO" and owner_count == 1:
                print("MARINA_DEMO_ALREADY_READY: preserving demo data and reservations")
                return
        if properties != 0 or tenants != 0:
            raise RuntimeError("Database is not empty or a verified existing demo; refusing bootstrap")
    finally:
        await conn.close()
    await bootstrap_marina_test.main()
    await bootstrap_owner.main()
    print("MARINA_DEMO_BOOTSTRAP_PASS: isolated synthetic hotel")


if __name__ == "__main__":
    asyncio.run(main())
