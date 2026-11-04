#!/usr/bin/env python3
"""Safely add one hotel to a POPULATED shared MARINA database; CI acceptance only.

No new API or migration. The atomic insert contract is reusable, but this CLI
refuses production, non-local databases and unreviewed hotel credentials.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
import re
from urllib.parse import urlsplit, unquote, parse_qsl
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import asyncpg

from provision_empty_marina_property import CODE_RE, OWNER_PASSWORD_HASHER

CI_CONFIRMATION = "DISPOSABLE_THIRD_HOTEL_ADDITIVE_CI_ONLY"
EXISTING_CONFIRMATION = "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
EXACT_DATABASE = "marina_shared_browser_ci"
ONBOARD_LOCK = "marina-smart-shared-hotel-onboarding-v1"
# Never change or overwrite these existing hotel fixture records.
EXISTING_CODES = (("tenant_a", "HOTEL_A"), ("tenant_b", "HOTEL_B"))


@dataclass(frozen=True)
class NewHotel:
    tenant_code: str
    property_code: str
    name: str
    timezone: str
    currency: str
    rate_plan_code: str
    owner_username: str
    owner_display_name: str
    owner_password: str


def staged_configuration() -> tuple[str, NewHotel]:
    required = {
        "APP_ENV": "staging",
        "PROPERTY_CODE": "MARINA_BROWSER_CI",
        "MARINA_TENANT_CONTEXT_ENABLED": "true",
        "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "true",
        "COOKIE_SECURE": "true",
        "MARINA_SHARED_BROWSER_CI_CONFIRM": EXISTING_CONFIRMATION,
        "MARINA_SHARED_THIRD_HOTEL_CONFIRM": CI_CONFIRMATION,
    }
    for key, value in required.items():
        if os.environ.get(key) != value:
            raise RuntimeError("Refusing unsafe shared onboarding environment: " + key)
    url = os.environ.get("DATABASE_URL", "")
    parsed = urlsplit(url)
    if (parsed.scheme not in {"postgresql", "postgres"} or
            parsed.hostname not in {"127.0.0.1", "localhost"} or
            parsed.port != 5432 or
            unquote(parsed.path) != "/" + EXACT_DATABASE or
            parsed.username != "marina_ci" or
            parsed.password != "synthetic-ci-database-only" or
            parsed.fragment or
            parse_qsl(parsed.query, keep_blank_values=True) not in ([], [("schema", "public")])):
        raise RuntimeError("Refusing non-disposable shared PostgreSQL URL")
    password = os.environ.get("MARINA_SHARED_BROWSER_CI_PASSWORD", "")
    if not password.startswith("synthetic-ci-only-") or len(password) < 16:
        raise RuntimeError("Refusing non-synthetic owner password in CI")
    return url.split("?", 1)[0], NewHotel(
        tenant_code="tenant_c", property_code="HOTEL_C", name="Synthetic Third Hotel",
        timezone="Asia/Bishkek", currency="KGS", rate_plan_code="MARINA_BROWSER_CI",
        owner_username="owner", owner_display_name="Synthetic Owner C", owner_password=password,
    )


def validate_hotel(hotel: NewHotel) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", hotel.tenant_code):
        raise ValueError("Invalid organization code")
    if not CODE_RE.fullmatch(hotel.property_code) or not CODE_RE.fullmatch(hotel.rate_plan_code):
        raise ValueError("Invalid hotel or rate plan code")
    if not 2 <= len(hotel.name) <= 160 or not 2 <= len(hotel.owner_display_name) <= 160:
        raise ValueError("Invalid hotel or owner name")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", hotel.owner_username):
        raise ValueError("Invalid owner username")
    if not 16 <= len(hotel.owner_password) <= 256:
        raise ValueError("Invalid owner credential length")
    if not re.fullmatch(r"[A-Z]{3}", hotel.currency):
        raise ValueError("Invalid currency")
    try:
        ZoneInfo(hotel.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Invalid hotel timezone") from exc


async def existing_hotel_pairs(conn: asyncpg.Connection) -> list[tuple[str, str]]:
    rows = await conn.fetch('''
        SELECT t.code AS tenant,p.code AS hotel
        FROM properties p JOIN tenants t ON t.id=p."tenantId"
        ORDER BY t.code,p.code''')
    return [(r["tenant"], r["hotel"]) for r in rows]


async def provision_additive(conn: asyncpg.Connection, hotel: NewHotel,
                             *, fail_after_property: bool = False) -> dict[str, uuid.UUID]:
    """Transactionally INSERT exactly one unrelated tenant/property/owner.

    Must never update existing hotel rows, reuse tenant, or depend on an empty
    application database. Duplicate attempts and simulated failures roll back.
    """
    validate_hotel(hotel)
    # Expensive password hash generated before acquiring any database locks.
    hash_value = OWNER_PASSWORD_HASHER.hash(hotel.owner_password)
    async with conn.transaction(isolation="serializable"):
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", ONBOARD_LOCK)
        if await existing_hotel_pairs(conn) != list(EXISTING_CODES):
            raise RuntimeError("Refusing to onboard: existing hotel inventory not exactly two approved properties")
        if await conn.fetchval("SELECT count(*) FROM tenants") != 2:
            raise RuntimeError("Refusing unrelated tenant records")
        if await conn.fetchval("SELECT count(*) FROM properties") != 2:
            raise RuntimeError("Refusing unexpected property records")
        # Existing fixture is not empty: reservations, money and staff must
        # already be there before executing the additive transaction.
        if await conn.fetchval("SELECT count(*) FROM reservations") < 2:
            raise RuntimeError("Refusing missing preexisting bookings")
        if await conn.fetchval("SELECT count(*) FROM payments") < 2:
            raise RuntimeError("Refusing missing preexisting financial records")
        if await conn.fetchval("SELECT EXISTS (SELECT 1 FROM tenants WHERE code=$1)", hotel.tenant_code):
            raise RuntimeError("Organization code collision")
        if await conn.fetchval("SELECT EXISTS (SELECT 1 FROM properties WHERE code=$1)", hotel.property_code):
            raise RuntimeError("Hotel code collision")
        ids = {field: uuid.uuid4() for field in
               ("tenant", "property", "rate", "settings", "owner", "audit")}
        await conn.execute('''
            INSERT INTO tenants(id,code,name,status,"createdAt","updatedAt")
            VALUES($1,$2,$3,'ACTIVE',now(),now())
        ''', ids["tenant"], hotel.tenant_code, hotel.name)
        await conn.execute('''
            INSERT INTO properties(id,"tenantId",code,name,timezone,currency,"createdAt","updatedAt")
            VALUES($1,$2,$3,$4,$5,$6,now(),now())
        ''', ids["property"], ids["tenant"], hotel.property_code, hotel.name,
                           hotel.timezone, hotel.currency)
        if fail_after_property:
            # CI deliberately simulates an interruption before account setup.
            # PostgreSQL must roll back even the new tenant and property.
            raise RuntimeError("Injected pre-owner transactional rollback")
        await conn.execute('''
            INSERT INTO rate_plans(id,"propertyId",code,name,currency,"createdAt","updatedAt")
            VALUES($1,$2,$3,'Direct bookings',$4,now(),now())
        ''', ids["rate"], ids["property"], hotel.rate_plan_code, hotel.currency)
        await conn.execute('''
            INSERT INTO property_product_settings
              (id,"propertyId","checkInTime","checkOutTime","enabledModules","createdAt","updatedAt")
            VALUES($1,$2,TIME '14:00',TIME '12:00','[]'::jsonb,now(),now())
        ''', ids["settings"], ids["property"])
        await conn.execute('''
            INSERT INTO staff_users
              (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
            VALUES($1,$2,$3,$4,$5,'OWNER',true,now(),now())
        ''', ids["owner"], ids["property"], hotel.owner_username,
                           hotel.owner_display_name, hash_value)
        await conn.execute('''
            INSERT INTO audit_logs
              (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"createdAt")
            VALUES($1,$2,'SYSTEM',NULL,'SHARED_PROPERTY_ONBOARD','Property',$3,
                   'ONBOARD','SUCCESS',now())
        ''', ids["audit"], ids["property"], str(ids["property"]))
        actual = await conn.fetchrow('''
            SELECT
              (SELECT count(*) FROM staff_users WHERE "propertyId"=$1) AS staff,
              (SELECT count(*) FROM rooms WHERE "propertyId"=$1) AS rooms,
              (SELECT count(*) FROM reservations WHERE "propertyId"=$1) AS reservations,
              (SELECT count(*) FROM property_product_settings WHERE "propertyId"=$1) AS product,
              (SELECT count(*) FROM rate_plans WHERE "propertyId"=$1) AS rates,
              (SELECT count(*) FROM audit_logs WHERE "propertyId"=$1) AS audit
        ''', ids["property"])
        if dict(actual) != {"staff": 1, "rooms": 0, "reservations": 0, "product": 1, "rates": 1, "audit": 1}:
            raise RuntimeError("New hotel was not initialized minimally and privately")
    return ids


if __name__ == "__main__":
    raise SystemExit("Library-only: run the isolated 3-hotel acceptance script, never raw production CLI")
