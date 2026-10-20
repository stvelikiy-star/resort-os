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
        if properties != 0 or tenants != 0:
            raise RuntimeError("Database is not empty; refusing bootstrap")
    finally:
        await conn.close()
    await bootstrap_marina_test.main()
    await bootstrap_owner.main()
    print("MARINA_DEMO_BOOTSTRAP_PASS: isolated synthetic hotel")


if __name__ == "__main__":
    asyncio.run(main())
