import asyncio
import os
import uuid

import asyncpg
from argon2 import PasswordHasher

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()

STAFF = [
    {
        "role": "MAID",
        "username": os.environ.get("STAGING_MAID_USERNAME"),
        "password": os.environ.get("STAGING_MAID_PASSWORD"),
        "display_name": os.environ.get("STAGING_MAID_DISPLAY_NAME", "Staging Maid"),
    },
    {
        "role": "TECHNICIAN",
        "username": os.environ.get("STAGING_TECHNICIAN_USERNAME"),
        "password": os.environ.get("STAGING_TECHNICIAN_PASSWORD"),
        "display_name": os.environ.get("STAGING_TECHNICIAN_DISPLAY_NAME", "Staging Technician"),
    },
]

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    if APP_ENV != "staging":
        raise RuntimeError("bootstrap_staging_staff.py only runs with APP_ENV=staging")

    for item in STAFF:
        if not item["username"] or not item["password"]:
            raise RuntimeError(f"Missing staging credentials for {item['role']}")
        if len(item["password"]) < 12:
            raise RuntimeError(f"Staging password for {item['role']} must be at least 12 characters")

    conn = await asyncpg.connect(database_url())
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
        if not property_id:
            raise RuntimeError(f"Property {PROPERTY_CODE} is not seeded")

        async with conn.transaction():
            for item in STAFF:
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
