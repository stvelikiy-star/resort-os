"""Rename the existing synthetic demo owner, preserving identity and all data."""
import asyncio
import os
import re
from urllib.parse import urlsplit, urlunsplit

import asyncpg
from argon2 import PasswordHasher


def configuration():
    if (os.environ.get("APP_ENV") != "staging"
            or os.environ.get("PROPERTY_CODE") != "MARINA_DEMO"
            or os.environ.get("MARINA_TENANT_CONTEXT_ENABLED", "false").lower() in {"1", "true", "yes", "on"}):
        raise RuntimeError("Refusing credentials change outside the isolated synthetic demo")
    username = os.environ.get("MARINA_DEMO_NEW_USERNAME", "demo")
    password = os.environ.get("MARINA_DEMO_NEW_PASSWORD", "")
    if username != "demo" or not re.fullmatch(r"[A-Za-z0-9_-]{6,256}", password):
        raise RuntimeError("Expected demo username and a 6+ character URL-safe password")
    parsed = urlsplit(os.environ["DATABASE_URL"])
    if (parsed.scheme not in {"postgresql", "postgres"} or parsed.hostname != "postgres"
            or parsed.port != 5432 or parsed.username != "marina_demo"
            or parsed.path != "/marina_demo" or parsed.fragment
            or parsed.query not in {"", "schema=public"}):
        raise RuntimeError("Refusing a database other than the dedicated Compose demo")
    return urlunsplit(parsed._replace(query="")), username, password


async def main():
    dsn, username, password = configuration()
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            await conn.execute("LOCK TABLE staff_users IN SHARE ROW EXCLUSIVE MODE")
            if await conn.fetchval("SELECT count(*) FROM properties") != 1 or await conn.fetchval("SELECT count(*) FROM tenants") != 1:
                raise RuntimeError("Expected exactly one synthetic property and tenant")
            prop = await conn.fetchrow('''SELECT p.id, p.code, t.code AS tenant_code
                FROM properties p JOIN tenants t ON t.id=p."tenantId"''')
            if not prop or prop["code"] != "MARINA_DEMO" or prop["tenant_code"] != "tenant_marina_demo":
                raise RuntimeError("Synthetic property identity mismatch")
            owners = await conn.fetch('''SELECT id, username, "isActive"
                FROM staff_users WHERE "propertyId"=$1 AND role='OWNER'
                AND username IN ('demo-owner', 'demo') FOR UPDATE''', prop["id"])
            if len(owners) != 1 or not owners[0]["isActive"]:
                raise RuntimeError("Expected one active existing demo owner; no account created or merged")
            owner_id = owners[0]["id"]
            await conn.execute('''UPDATE staff_users SET username=$2, "passwordHash"=$3,
                "updatedAt"=now() WHERE id=$1''', owner_id, username,
                PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4).hash(password))
            await conn.execute('''UPDATE auth_sessions SET "revokedAt"=now()
                WHERE "userId"=$1 AND "revokedAt" IS NULL''', owner_id)
        print("MARINA_DEMO_ACCESS_UPDATED: username=demo; identity/data preserved; old sessions revoked")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
