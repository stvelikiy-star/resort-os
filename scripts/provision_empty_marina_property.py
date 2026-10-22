"""Create the initial, empty MARINA SMART hotel rows in a dedicated database.

This is deliberately a one-shot bootstrap, not a tenant administration API.
It refuses databases that contain application data and never seeds demo data,
staff accounts, rooms, prices, or integrations.
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import asyncpg
from argon2 import PasswordHasher

CONFIRMATION = "CREATE_ONE_EMPTY_MARINA_PROPERTY"
LOCK_KEY = "marina-smart-empty-property-provision-v1"
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{2,39}$")
OWNER_PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def validate_environment() -> dict[str, str]:
    """Validate deliberate operator intent and reject known shared DB targets."""
    app_env = _required("APP_ENV").lower()
    if app_env not in {"staging", "production"}:
        raise RuntimeError("APP_ENV must be exactly staging or production")
    if _required("MARINA_PROVISION_CONFIRM") != CONFIRMATION:
        raise RuntimeError(f"Set MARINA_PROVISION_CONFIRM={CONFIRMATION} to proceed")

    database_url = _required("DATABASE_URL")
    parsed = urlsplit(database_url)
    database_name = unquote(parsed.path.lstrip("/"))
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not database_name:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL with an explicit database name")
    if not database_name.lower().startswith("marina_"):
        raise RuntimeError("Refusing database name without the dedicated marina_ prefix")
    if database_name.lower() in {"marina", "marina_prod_shared", "marina_shared"}:
        raise RuntimeError("Refusing a shared or ambiguous database name")
    if database_name.lower() in {"resort_os", "three_crowns", "three-crowns"}:
        raise RuntimeError("Refusing a Three Crowns database")

    property_code = _required("PROPERTY_CODE").upper()
    if not CODE_RE.fullmatch(property_code):
        raise RuntimeError("PROPERTY_CODE must be 3-40 uppercase letters, digits, _ or -")
    property_name = _required("MARINA_PROPERTY_NAME")
    if len(property_name) > 160:
        raise RuntimeError("MARINA_PROPERTY_NAME must be at most 160 characters")
    tenant_code = os.environ.get("MARINA_TENANT_CODE", f"tenant_{property_code.lower()}").strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", tenant_code):
        raise RuntimeError("MARINA_TENANT_CODE must be 3-64 lowercase letters, digits, _ or -")
    timezone = os.environ.get("MARINA_TIMEZONE", "Asia/Bishkek").strip()
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError("MARINA_TIMEZONE must be a valid IANA timezone") from exc
    currency = os.environ.get("MARINA_CURRENCY", "KGS").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise RuntimeError("MARINA_CURRENCY must be a three-letter code")
    rate_plan_code = os.environ.get("RATE_PLAN_CODE", "DIRECT").strip().upper()
    if not CODE_RE.fullmatch(rate_plan_code):
        raise RuntimeError("RATE_PLAN_CODE must be 3-40 uppercase letters, digits, _ or -")
    owner_username = _required("MARINA_OWNER_USERNAME").lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", owner_username):
        raise RuntimeError("MARINA_OWNER_USERNAME must be 3-80 lowercase letters, digits, ., _ or -")
    owner_password = _required("MARINA_OWNER_PASSWORD")
    if len(owner_password) < 16 or len(owner_password) > 256:
        raise RuntimeError("MARINA_OWNER_PASSWORD must be 16-256 characters")
    owner_display_name = os.environ.get("MARINA_OWNER_DISPLAY_NAME", "Owner").strip()
    if not 2 <= len(owner_display_name) <= 160:
        raise RuntimeError("MARINA_OWNER_DISPLAY_NAME must be 2-160 characters")

    return {
        "database_url": database_url.replace("?schema=public", ""),
        "database_name": database_name,
        "property_code": property_code,
        "property_name": property_name,
        "tenant_code": tenant_code,
        "timezone": timezone,
        "currency": currency,
        "rate_plan_code": rate_plan_code,
        "owner_username": owner_username,
        "owner_password": owner_password,
        "owner_display_name": owner_display_name,
    }


async def assert_database_empty(conn: asyncpg.Connection) -> None:
    """Require every public application table to be empty, not just core rows."""
    tables = await conn.fetch(
        """SELECT table_name FROM information_schema.tables
           WHERE table_schema='public' AND table_type='BASE TABLE'
             AND table_name <> '_prisma_migrations'
           ORDER BY table_name"""
    )
    if not tables:
        raise RuntimeError("No public application tables found; apply migrations first")

    populated: list[str] = []
    for row in tables:
        # Identifier comes from information_schema and is quoted by PostgreSQL.
        table = row["table_name"].replace('"', '""')
        has_rows = await conn.fetchval(f'SELECT EXISTS (SELECT 1 FROM public."{table}" LIMIT 1)')
        if has_rows:
            populated.append(row["table_name"])
    if populated:
        raise RuntimeError(
            "Refusing non-empty database; public application tables contain rows: "
            + ", ".join(populated)
        )


async def provision(config: dict[str, str]) -> dict[str, str]:
    owner_password_hash = OWNER_PASSWORD_HASHER.hash(config["owner_password"])
    conn = await asyncpg.connect(config["database_url"])
    try:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", LOCK_KEY)
            await assert_database_empty(conn)

            tenant_id = uuid.uuid4()
            property_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO tenants (id,code,name,status,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,'ACTIVE',now(),now())''',
                tenant_id, config["tenant_code"], config["property_name"],
            )
            await conn.execute(
                '''INSERT INTO properties
                     (id,"tenantId",code,name,timezone,currency,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6,now(),now())''',
                property_id, tenant_id, config["property_code"], config["property_name"],
                config["timezone"], config["currency"],
            )
            await conn.execute(
                '''INSERT INTO rate_plans
                     (id,"propertyId",code,name,currency,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,now(),now())''',
                uuid.uuid4(), property_id, config["rate_plan_code"], "Direct bookings",
                config["currency"],
            )
            await conn.execute(
                '''INSERT INTO property_product_settings
                     (id,"propertyId","checkInTime","checkOutTime","enabledModules","createdAt","updatedAt")
                   VALUES ($1,$2,TIME '14:00',TIME '12:00','[]'::jsonb,now(),now())''',
                uuid.uuid4(), property_id,
            )
            await conn.execute(
                '''INSERT INTO staff_users
                     (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,'OWNER',true,now(),now())''',
                uuid.uuid4(), property_id, config["owner_username"],
                config["owner_display_name"], owner_password_hash,
            )

            # Verify the bootstrap created exactly the intended minimum state.
            result = await conn.fetchrow(
                '''SELECT
                     (SELECT count(*) FROM tenants) AS tenants,
                     (SELECT count(*) FROM properties) AS properties,
                     (SELECT count(*) FROM rate_plans) AS rate_plans,
                     (SELECT count(*) FROM property_product_settings) AS product_settings,
                     (SELECT count(*) FROM rooms) AS rooms,
                     (SELECT count(*) FROM room_types) AS room_types,
                     (SELECT count(*) FROM staff_users) AS staff_users,
                     (SELECT count(*) FROM staff_users WHERE "propertyId"=$1 AND username=$2 AND role='OWNER' AND "isActive") AS owner_users''',
                property_id, config["owner_username"],
            )
            actual = dict(result)
            expected = {
                "tenants": 1, "properties": 1, "rate_plans": 1,
                "product_settings": 1, "rooms": 0, "room_types": 0,
                "staff_users": 1, "owner_users": 1,
            }
            if actual != expected:
                raise RuntimeError(f"Unexpected post-provision state: {actual}")
            saved_password_hash = await conn.fetchval(
                'SELECT "passwordHash" FROM staff_users WHERE "propertyId"=$1 AND username=$2',
                property_id, config["owner_username"],
            )
            if not OWNER_PASSWORD_HASHER.verify(saved_password_hash, config["owner_password"]):
                raise RuntimeError("Owner password hash verification failed")
        return {"property_code": config["property_code"], "tenant_code": config["tenant_code"]}
    finally:
        await conn.close()


async def main() -> None:
    config = validate_environment()
    result = await provision(config)
    print(
        "MARINA empty-property provisioning OK: "
        f"database={config['database_name']} tenant={result['tenant_code']} "
        f"property={result['property_code']} rooms=0 room_types=0 owner_users=1"
    )


if __name__ == "__main__":
    asyncio.run(main())
