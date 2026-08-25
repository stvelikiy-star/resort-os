import asyncio
import os
import uuid

import asyncpg
from argon2 import PasswordHasher

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME")
PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD")
DISPLAY_NAME = os.environ.get("BOOTSTRAP_OWNER_DISPLAY_NAME", "Owner")

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("BOOTSTRAP_OWNER_USERNAME and BOOTSTRAP_OWNER_PASSWORD are required")
    if len(PASSWORD) < 12:
        raise RuntimeError("BOOTSTRAP_OWNER_PASSWORD must be at least 12 characters")

    conn = await asyncpg.connect(database_url())
    try:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code = $1", PROPERTY_CODE)
        if not property_id:
            raise RuntimeError(f"Property {PROPERTY_CODE} is not seeded")

        username = USERNAME.strip().lower()
        password_hash = password_hasher.hash(PASSWORD)
        user_id = await conn.fetchval(
            '''
            INSERT INTO staff_users (
                id, "propertyId", username, "displayName", "passwordHash", role, "isActive", "createdAt", "updatedAt"
            ) VALUES ($1, $2, $3, $4, $5, 'OWNER', true, now(), now())
            ON CONFLICT ("propertyId", username) DO UPDATE SET
                "displayName" = EXCLUDED."displayName",
                "passwordHash" = EXCLUDED."passwordHash",
                role = 'OWNER',
                "isActive" = true,
                "updatedAt" = now()
            RETURNING id
            ''',
            uuid.uuid4(),
            property_id,
            username,
            DISPLAY_NAME,
            password_hash,
        )

        await conn.execute(
            '''
            UPDATE auth_sessions
            SET "revokedAt" = now()
            WHERE "userId" = $1 AND "revokedAt" IS NULL
            ''',
            user_id,
        )
        print(f"Owner bootstrap OK: property={PROPERTY_CODE}, username={username}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
