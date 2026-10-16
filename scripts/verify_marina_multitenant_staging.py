#!/usr/bin/env python3
"""Read-only MARINA SMART staging gate for the first multi-tenant rollout.

The gate never inserts, updates or deletes data. It verifies that staging has the
tenant migration, that every property is assigned to exactly one tenant, and that
the API is reachable before the later login/isolation E2E is enabled.
"""

from __future__ import annotations

import asyncio
import os
import sys
from urllib.parse import urlsplit

import asyncpg
import httpx


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def validate_base_url(value: str) -> str:
    parsed = urlsplit(value)
    allowed_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not allowed_local:
        raise RuntimeError("MARINA_STAGING_BASE_URL must use HTTPS outside local CI")
    if not parsed.netloc:
        raise RuntimeError("MARINA_STAGING_BASE_URL must include a host")
    return value.rstrip("/")


def expected_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be positive")
    return value


async def main() -> int:
    base_url = validate_base_url(required("MARINA_STAGING_BASE_URL"))
    database_url = required("MARINA_STAGING_DATABASE_URL").replace("?schema=public", "")
    expected_tenants = expected_int("MARINA_STAGING_EXPECTED_TENANTS", 2)
    expected_properties = expected_int("MARINA_STAGING_EXPECTED_PROPERTIES", 2)

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0, follow_redirects=False) as client:
        health = await client.get("/health/ready")
        if health.status_code != 200:
            raise RuntimeError(f"staging readiness returned HTTP {health.status_code}")
        openapi = await client.get("/openapi.json")
        if openapi.status_code != 200:
            raise RuntimeError(f"staging OpenAPI returned HTTP {openapi.status_code}")

    conn = await asyncpg.connect(database_url, timeout=10)
    try:
        migration_count = await conn.fetchval(
            'SELECT count(*) FROM "_prisma_migrations" WHERE "finished_at" IS NOT NULL'
        )
        tenant_table = await conn.fetchval("SELECT to_regclass('public.tenants')::text")
        if tenant_table != "tenants":
            raise RuntimeError("staging tenants table is missing")
        tenant_count = await conn.fetchval("SELECT count(*) FROM tenants WHERE status='ACTIVE'")
        property_count = await conn.fetchval('SELECT count(*) FROM properties')
        unassigned_properties = await conn.fetchval(
            'SELECT count(*) FROM properties WHERE "tenantId" IS NULL'
        )
        duplicate_property_codes = await conn.fetchval(
            '''
            SELECT count(*)
            FROM (
                SELECT "tenantId", code
                FROM properties
                GROUP BY "tenantId", code
                HAVING count(*) > 1
            ) duplicates
            '''
        )
        if migration_count < 31:
            raise RuntimeError(f"staging migration ledger is incomplete: {migration_count}")
        if tenant_count != expected_tenants:
            raise RuntimeError(
                f"expected {expected_tenants} active tenants, found {tenant_count}"
            )
        if property_count != expected_properties:
            raise RuntimeError(
                f"expected {expected_properties} properties, found {property_count}"
            )
        if unassigned_properties:
            raise RuntimeError(f"properties without tenant: {unassigned_properties}")
        if duplicate_property_codes:
            raise RuntimeError(f"duplicate property codes inside tenants: {duplicate_property_codes}")

        expected_codes = [
            item.strip()
            for item in os.environ.get("MARINA_STAGING_EXPECTED_PROPERTY_CODES", "").split(",")
            if item.strip()
        ]
        if expected_codes:
            actual_codes = await conn.fetch(
                'SELECT code FROM properties ORDER BY code'
            )
            actual = [row["code"] for row in actual_codes]
            if actual != sorted(expected_codes):
                raise RuntimeError(f"property code set mismatch: expected {sorted(expected_codes)}, found {actual}")

        print(
            "MARINA_STAGING_FOUNDATION_PASS "
            f"migrations={migration_count} tenants={tenant_count} properties={property_count}"
        )
        print("BOUNDARY: read-only foundation gate passed; login/isolation E2E and production remain STOP")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except (OSError, RuntimeError, asyncpg.PostgresError, httpx.HTTPError) as exc:
        print(f"MARINA_STAGING_FOUNDATION_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
