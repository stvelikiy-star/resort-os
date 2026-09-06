import asyncio
import os
import uuid

import asyncpg
from argon2 import PasswordHasher

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()


def first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


STAFF = [
    {
        "role": "RECEPTION",
        "username": first_env("RECEPTION_USERNAME", "STAGING_RECEPTION_USERNAME"),
        "password": first_env("RECEPTION_PASSWORD", "STAGING_RECEPTION_PASSWORD"),
        "display_name": first_env("RECEPTION_DISPLAY_NAME", "STAGING_RECEPTION_DISPLAY_NAME") or "Staging Reception",
    },
    {
        "role": "DINING_STAFF",
        "username": first_env("DINING_STAFF_USERNAME", "STAGING_DINING_USERNAME"),
        "password": first_env("DINING_STAFF_PASSWORD", "STAGING_DINING_PASSWORD"),
        "display_name": first_env("DINING_STAFF_DISPLAY_NAME", "STAGING_DINING_DISPLAY_NAME") or "Staging Dining",
    },
    {
        "role": "MAID",
        "username": first_env("MAID_USERNAME", "STAGING_MAID_USERNAME"),
        "password": first_env("MAID_PASSWORD", "STAGING_MAID_PASSWORD"),
        "display_name": first_env("MAID_DISPLAY_NAME", "STAGING_MAID_DISPLAY_NAME") or "Staging Maid",
    },
    {
        "role": "TECHNICIAN",
        "username": first_env("TECHNICIAN_USERNAME", "STAGING_TECHNICIAN_USERNAME"),
        "password": first_env("TECHNICIAN_PASSWORD", "STAGING_TECHNICIAN_PASSWORD"),
        "display_name": first_env("TECHNICIAN_DISPLAY_NAME", "STAGING_TECHNICIAN_DISPLAY_NAME") or "Staging Technician",
    },
]

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    if APP_ENV != "staging":
        raise RuntimeError("bootstrap_staging_staff.py only runs with APP_ENV=staging")

    configured = []
    for item in STAFF:
        username = item["username"]
        password = item["password"]
        if not username and not password:
            continue
        if not username or not password:
            raise RuntimeError(f"Incomplete staging credentials for {item['role']}")
        if len(password) < 12:
            raise RuntimeError(f"Staging password for {item['role']} must be at least 12 characters")
        configured.append(item)

    if not configured:
        raise RuntimeError("No staging staff credentials were configured")

    conn = await asyncpg.connect(database_url())
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
        if not property_id:
            raise RuntimeError(f"Property {PROPERTY_CODE} is not seeded")

        async with conn.transaction():
            for item in configured:
                username = item["username"].strip().lower()
                password_hash = password_hasher.hash(item["password"])
                user_id = await conn.fetchval(
                    '''
                    INSERT INTO staff_users (
                      id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())
                    ON CONFLICT ("propertyId",username) DO UPDATE SET
                      "displayName"=EXCLUDED."displayName",
                      "passwordHash"=EXCLUDED."passwordHash",
                      role=EXCLUDED.role,
                      "isActive"=true,
                      "updatedAt"=now()
                    RETURNING id
                    ''',
                    uuid.uuid4(),
                    property_id,
                    username,
                    item["display_name"],
                    password_hash,
                    item["role"],
                )
                await conn.execute(
                    '''UPDATE auth_sessions SET "revokedAt"=now() WHERE "userId"=$1 AND "revokedAt" IS NULL''',
                    user_id,
                )
                print(f"Staging staff bootstrap OK: role={item['role']} username={username}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
