"""Only initialise a truly empty disposable MARINA demo PostgreSQL."""
import asyncio
import os

import asyncpg
import bootstrap_marina_test
import bootstrap_owner


async def main():
    if os.environ.get("MARINA_DEMO_CONFIRM") != "EMPTY_SYNTHETIC_DB_ONLY":
        raise RuntimeError("Synthetic-only explicit guard required")
    if os.environ.get("APP_ENV") != "staging" or os.environ.get("PROPERTY_CODE") != "MARINA_DEMO":
        raise RuntimeError("Refusing to seed outside MARINA_DEMO staging")
    dsn = os.environ["DATABASE_URL"].replace("?schema=public", "")
    if "@postgres:5432/marina_demo" not in dsn:
        raise RuntimeError("Refusing non-demo PostgreSQL connection")
    conn = await asyncpg.connect(dsn)
    try:
        properties = await conn.fetchval("SELECT count(*) FROM properties")
        tenants = await conn.fetchval("SELECT count(*) FROM tenants")
        if properties == 1 and tenants == 0:
            row = await conn.fetchrow(
                'SELECT p.code, (SELECT count(*) FROM rooms r WHERE r."propertyId"=p.id) AS rooms, '
                '(SELECT count(*) FROM room_types rt WHERE rt."propertyId"=p.id) AS categories FROM properties p'
            )
            owner_count = await conn.fetchval(
                'SELECT count(*) FROM staff_users su JOIN properties p ON p.id=su."propertyId" '
                'WHERE p.code=$1 AND su.username=$2 AND su.role=\'OWNER\' AND su."isActive"=true',
                "MARINA_DEMO", os.environ.get("BOOTSTRAP_OWNER_USERNAME", "demo-owner")
            )
            if row and row["code"] == "MARINA_DEMO" and row["rooms"] == 12 and row["categories"] == 3 and owner_count == 1:
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
