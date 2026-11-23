"""Isolated MARINA FLEX management API entrypoint. No PMS runtime import.

Reuses vetted FLEX-only routers from services/api/app; never imports the PMS
FastAPI application, payment simulator, bank, refund or payout code.
Writes are disabled unless separately enabled in protected QA with MFA and
explicit PostgreSQL NOINHERIT writer membership. No new external services.
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute

# Shared source is the already reviewed FLEX-only code; its own modules must
# stay outside operational PMS app and be bundled by Vercel monorepo support.
_SHARED = Path(__file__).resolve().parents[2] / "services" / "api"
if not (_SHARED / "app" / "flex_control_plane.py").is_file():
    raise RuntimeError("FLEX_SOURCE_NOT_INCLUDED_IN_VERCEL_BUILD")
sys.path.insert(0, str(_SHARED))
from app import flex_control_plane, flex_partner_portal, flex_onboarding, flex_catalog_admin


def _qa_flag(name: str) -> bool:
    return os.environ.get("FLEX_ENVIRONMENT") == "qa" and os.environ.get(name) == "true"


_ENABLE_ONBOARDING = _qa_flag("FLEX_ENABLE_QA_ONBOARDING")
_ENABLE_CATALOG = _qa_flag("FLEX_ENABLE_QA_CATALOG_DRAFTS")


@asynccontextmanager
async def _flex_lifespan(application: FastAPI):
    # A database connection is mandatory; never silently run a mocked API.
    qa_dsn()
    async with flex_control_plane.lifespan(application):
        async with application.state.flex_pool.acquire() as conn:
            for role in flex_partner_portal.READERS:
                member = await conn.fetchval(
                    "SELECT pg_has_role(current_user,$1,'MEMBER')", role
                )
                inherited = await conn.fetchval(
                    "SELECT pg_has_role(current_user,$1,'USAGE')", role
                )
                if not member or inherited:
                    raise RuntimeError("FLEX partner reader requires NOINHERIT membership")
        if _ENABLE_ONBOARDING:
            await flex_onboarding._onboarding_writer_ready(application.state.flex_pool)
        if _ENABLE_CATALOG:
            async with application.state.flex_pool.acquire() as conn:
                membership = await conn.fetchval(
                    "SELECT pg_has_role(current_user,'flex_catalog_draft_writer','MEMBER')"
                )
                inherited = await conn.fetchval(
                    "SELECT pg_has_role(current_user,'flex_catalog_draft_writer','USAGE')"
                )
                if not membership or inherited:
                    raise RuntimeError("FLEX catalog writer must be a NOINHERIT member")
        yield


app = FastAPI(
    title="MARINA FLEX Management QA",
    version="0.2.0",
    lifespan=_flex_lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Existing explicit FLEX routers, not a generic path proxy. Write endpoints
# remain unregistered while their respective QA flags are disabled.
_ROUTES = [
    flex_control_plane.app,
    flex_partner_portal.app,
]
if _ENABLE_ONBOARDING:
    _ROUTES.append(flex_onboarding.app)
if _ENABLE_CATALOG:
    _ROUTES.append(flex_catalog_admin.app)
_seen = {"/health"}
for source in _ROUTES:
    for route in source.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/v1/"):
            continue
        if route.path in _seen:
            raise RuntimeError("FLEX_ROUTE_COLLISION: " + route.path)
        if not (route.methods <= {"GET", "POST"}):
            raise RuntimeError("FLEX_UNEXPECTED_MUTATION_ROUTE")
        if "POST" in route.methods and source not in (flex_onboarding.app, flex_catalog_admin.app):
            raise RuntimeError("FLEX_UNAUTHORIZED_WRITE_ROUTE")
        _seen.add(route.path)
        app.router.routes.append(route)


_CHECK_SQL = """
SELECT current_user AS db_role,
       r.rolsuper, r.rolbypassrls, r.rolcreaterole,
       pg_has_role(current_user,'flex_identity_reader','MEMBER') AS identity_member,
       pg_has_role(current_user,'flex_hotel_reader','MEMBER') AS hotel_member,
       pg_has_role(current_user,'flex_hotel_reader','USAGE') AS inherited_hotel_access,
       has_table_privilege(current_user,'flex_private.flex_hotels','SELECT') AS direct_hotel_read,
       has_table_privilege(current_user,'flex_private.flex_confirmed_payments','SELECT') AS direct_payment_read,
       has_table_privilege(current_user,'flex_private.flex_confirmed_payments','INSERT') AS direct_payment_write,
       has_table_privilege(current_user,'flex_private.flex_subscription_configuration_drafts','INSERT') AS direct_draft_write,
       to_regclass('flex_private.flex_qa_settlement_evidence') IS NULL AS payment_simulator_absent
FROM pg_roles r WHERE r.rolname=current_user
"""


def qa_dsn() -> str:
    if os.environ.get("FLEX_ENVIRONMENT") != "qa":
        raise ValueError("Not an isolated FLEX QA environment")
    dsn = os.environ.get("FLEX_DATABASE_URL", "")
    if not dsn:
        raise ValueError("FLEX QA database is not configured")
    parts = urlsplit(dsn)
    if (
        parts.scheme not in {"postgres", "postgresql"}
        or parts.username != "flex_qa_read_runtime"
        or parts.path != "/flex_qa"
        or not (parts.hostname or "").endswith(".neon.tech")
        or parse_qs(parts.query).get("sslmode", [""])[0]
        not in {"require", "verify-ca", "verify-full"}
    ):
        raise ValueError("Refusing non-Neon or privileged database connection")
    return dsn


@app.get("/health")
async def health() -> dict:
    try:
        dsn = qa_dsn()
    except ValueError:
        raise HTTPException(status_code=503, detail="FLEX_QA_NOT_CONFIGURED") from None

    connection = None
    try:
        connection = await asyncpg.connect(dsn, timeout=8, command_timeout=8)
        async with connection.transaction(readonly=True):
            row = await connection.fetchrow(_CHECK_SQL)
        if row is None or any((
            row["db_role"] != "flex_qa_read_runtime",
            row["rolsuper"], row["rolbypassrls"], row["rolcreaterole"],
            not row["identity_member"], not row["hotel_member"],
            row["inherited_hotel_access"], row["direct_hotel_read"],
            row["direct_payment_read"], row["direct_payment_write"],
            row["direct_draft_write"], not row["payment_simulator_absent"],
        )):
            raise HTTPException(503, detail="FLEX_QA_PRIVILEGE_GUARD_FAILED")
        return {
            "status": "ok",
            "mode": "QA_MANAGEMENT_READ_ONLY" if not (_ENABLE_ONBOARDING or _ENABLE_CATALOG) else "QA_MANAGEMENT_DRAFTS",
            "database": "isolated_neon",
            "least_privilege": True,
            "payments_enabled": False,
            "payouts_enabled": False,
            "onboarding_enabled": _ENABLE_ONBOARDING,
            "catalog_drafts_enabled": _ENABLE_CATALOG,
            "real_user_auth_enabled": bool(os.environ.get("FLEX_AUTH_PUBLIC_KEYS_JSON")),
            "read_routes_registered": True,
        }
    except HTTPException:
        raise
    except (asyncpg.PostgresError, OSError, TimeoutError, ValueError):
        raise HTTPException(503, detail="FLEX_QA_DATABASE_UNAVAILABLE") from None
    finally:
        if connection is not None:
            await connection.close()
