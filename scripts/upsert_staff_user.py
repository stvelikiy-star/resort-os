import asyncio
import os
import uuid

import asyncpg
from argon2 import PasswordHasher

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
USERNAME = os.environ.get("STAFF_USERNAME")
PASSWORD = os.environ.get("STAFF_PASSWORD")
DISPLAY_NAME = os.environ.get("STAFF_DISPLAY_NAME", "Staff")
ROLE = os.environ.get("STAFF_ROLE", "MAID").upper()
ALLOWED_ROLES = {"OWNER", "ADMIN", "MANAGER", "RECEPTION", "DINING", "MAID", "TECHNICIAN", "BEACH_PARTNER"}

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("STAFF_USERNAME and STAFF_PASSWORD are required")
    if len(PASSWORD) < 12:
        raise RuntimeError("STAFF_PASSWORD must be at least 12 characters")
    if ROLE not in ALLOWED_ROLES:
        raise RuntimeError(f"STAFF_ROLE must be one of {sorted(ALLOWED_ROLES)}")

    conn = await asyncpg.connect(database_url())
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code = $1", PROPERTY_CODE)
        if not property_id:
            raise RuntimeError(f"Property {PROPERTY_CODE} is not seeded")

        username = USERNAME.strip().lower()
        user_id = await conn.fetchval(
            '''
            INSERT INTO staff_users (
                id, "propertyId", username, "displayName", "passwordHash", role, "isActive", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, $6::"StaffRole", true, now(), now())
            ON CONFLICT ("propertyId", username) DO UPDATE SET
                "displayName" = EXCLUDED."displayName",
                "passwordHash" = EXCLUDED."passwordHash",
                role = EXCLUDED.role,
                "isActive" = true,
                "updatedAt" = now()
            RETURNING id
            ''',
            uuid.uuid4(), property_id, username, DISPLAY_NAME, password_hasher.hash(PASSWORD), ROLE,
        )
        await conn.execute(
            '''UPDATE auth_sessions SET "revokedAt"=now() WHERE "userId"=$1 AND "revokedAt" IS NULL''',
            user_id,
        )
        print(f"Staff upsert OK: property={PROPERTY_CODE}, username={username}, role={ROLE}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
