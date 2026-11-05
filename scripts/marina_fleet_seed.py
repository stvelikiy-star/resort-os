"""Fail-closed staging initializer for one isolated MARINA hotel database."""
import asyncio
import os
import re
import asyncpg
import bootstrap_marina_test
import bootstrap_owner

async def main():
    slug = os.environ.get("MARINA_INSTANCE_SLUG", "")
    property_code = os.environ.get("PROPERTY_CODE", "")
    expected = f"MARINA_{slug.upper()}"
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,28}", slug):
        raise RuntimeError("Invalid hotel slug")
    if os.environ.get("APP_ENV") != "staging" or property_code != expected:
        raise RuntimeError("Wrong stage/property boundary; refusing bootstrap")
    if os.environ.get("MARINA_FLEET_CONFIRM") != "SYNTHETIC_EMPTY_PROPERTY_ONLY":
        raise RuntimeError("Explicit synthetic-only confirmation required")
    database = "marina_" + slug
    dsn = os.environ["DATABASE_URL"].replace("?schema=public", "")
    if f"@postgres:5432/{database}" not in dsn:
        raise RuntimeError("Refusing unexpected database target")
    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch("SELECT code FROM properties ORDER BY code")
        tenants = await conn.fetch("SELECT code FROM tenants ORDER BY code")
        if len(rows) == 1 and rows[0]["code"] == property_code and len(tenants) == 1 and tenants[0]["code"] == f"tenant_{property_code.lower()}":
            count = await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=(SELECT id FROM properties WHERE code=$1)', property_code)
            owner = await conn.fetchval('SELECT count(*) FROM staff_users WHERE "propertyId"=(SELECT id FROM properties WHERE code=$1) AND username=$2 AND role=\'OWNER\' AND "isActive"=true', property_code, os.environ["BOOTSTRAP_OWNER_USERNAME"])
            if count == 12 and owner == 1:
                print("FLEET_EXISTING_STAGING_PRESERVED", slug)
                return
        if rows or tenants:
            raise RuntimeError("Database contains non-empty/unverified hotel data; refusing initialization")
    finally:
        await conn.close()
    await bootstrap_marina_test.main()
    await bootstrap_owner.main()
    print("FLEET_STAGING_SEEDED", slug)

if __name__ == "__main__":
    asyncio.run(main())
