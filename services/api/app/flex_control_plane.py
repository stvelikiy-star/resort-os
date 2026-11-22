"""Read-only, isolated MARINA FLEX commercial API (NOT included in PMS app).

Run only with a dedicated least-privilege FLEX_DATABASE_URL role that is a
member of three NOLOGIN reader roles, with EdDSA signing keys from a trusted
external identity issuer. Never deploy this with PMS DATABASE_URL or DB owner.

No mutations, provider webhooks, hotel blocking, deployment hooks, JWT issuance,
hotel-staff authentication or payment operations are implemented here.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import asyncpg
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from jwt.exceptions import PyJWTError

from .db import clean_asyncpg_url
from .flex_foundation import PlatformPrincipal, platform_action_allowed

MAX_TOKEN_BYTES = 8192
MAX_TOKEN_AGE_SECONDS = 900
SUBJECT_RE = re.compile(r"^[a-zA-Z0-9_:.@/\-]{2,180}$")
KID_RE = re.compile(r"^[a-zA-Z0-9_\-]{2,80}$")


def _same_db_target(a: str, b: str) -> bool:
    x, y = urlsplit(a), urlsplit(b)
    return (
        (x.hostname or "").lower(), x.port or 5432, x.path.rstrip("/")
    ) == (
        (y.hostname or "").lower(), y.port or 5432, y.path.rstrip("/")
    )


def _flex_dsn() -> str:
    raw = os.environ.get("FLEX_DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("FLEX_DATABASE_URL required: standalone FLEX DB only")
    legacy = os.environ.get("DATABASE_URL", "").strip()
    if legacy and _same_db_target(raw, legacy):
        raise RuntimeError("FLEX database must be separate from PMS database")
    return clean_asyncpg_url(raw)


def verify_platform_token(authorization: str | None) -> tuple[str, bool]:
    """Verify issuer-signed EdDSA token. Role and hotel scopes NEVER come from JWT."""
    if not authorization or len(authorization) > MAX_TOKEN_BYTES:
        raise HTTPException(401, detail="Valid bearer token required")
    kind, sep, raw_token = authorization.partition(" ")
    if kind.lower() != "bearer" or not sep or not raw_token or " " in raw_token:
        raise HTTPException(401, detail="Valid bearer token required")
    try:
        keys = json.loads(os.environ.get("FLEX_AUTH_PUBLIC_KEYS_JSON", ""))
        issuer = os.environ.get("FLEX_AUTH_ISSUER", "")
        audience = os.environ.get("FLEX_AUTH_AUDIENCE", "")
        if not isinstance(keys, dict) or not keys or not issuer or not audience:
            raise ValueError("Missing issuer configuration")
    except (ValueError, TypeError):
        raise HTTPException(503, detail="FLEX authentication not configured") from None

    try:
        header = jwt.get_unverified_header(raw_token)
        kid = header.get("kid")
        if header.get("alg") != "EdDSA" or not isinstance(kid, str) or not KID_RE.fullmatch(kid):
            raise ValueError("Invalid JWT header")
        pem = keys.get(kid)
        if not isinstance(pem, str):
            raise ValueError("Unknown signing key")
        key = load_pem_public_key(pem.encode("utf-8"))
        claims = jwt.decode(
            raw_token, key, algorithms=["EdDSA"], audience=audience,
            issuer=issuer, leeway=30,
            options={"require": ["sub", "iss", "aud", "exp", "iat", "nbf", "jti"]},
        )
        subject = claims.get("sub")
        issued = claims.get("iat")
        expires = claims.get("exp")
        if (
            not isinstance(subject, str) or not SUBJECT_RE.fullmatch(subject)
            or not isinstance(issued, int) or isinstance(issued, bool)
            or not isinstance(expires, int) or isinstance(expires, bool)
            or expires <= issued or expires - issued > MAX_TOKEN_AGE_SECONDS
            or issued > time.time() + 30
            or not isinstance(claims.get("jti"), str) or not claims["jti"]
        ):
            raise ValueError("Token lifetime or subject rejected")
        amr = claims.get("amr")
        mfa = isinstance(amr, list) and "mfa" in amr
        return subject, mfa
    except (PyJWTError, ValueError, TypeError, UnicodeError):
        raise HTTPException(401, detail="Invalid bearer token") from None


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(dsn=_flex_dsn(), min_size=1, max_size=5, command_timeout=10)
    try:
        # Running the app as DB owner/superuser defeats the intended RLS model.
        async with pool.acquire() as conn:
            elevated = await conn.fetchval(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
            if elevated:
                raise RuntimeError("FLEX runtime database account must not bypass RLS")
            for role in ("flex_identity_reader", "flex_hotel_reader", "flex_platform_admin_reader"):
                can_use = await conn.fetchval("SELECT pg_has_role(current_user,$1,'MEMBER')", role)
                if not can_use:
                    raise RuntimeError(f"FLEX runtime role missing membership: {role}")
                inherited = await conn.fetchval(
                    "SELECT pg_has_role(current_user,$1,'USAGE')", role
                )
                if inherited:
                    raise RuntimeError(f"FLEX runtime must not inherit reader privileges: {role}")
        app.state.flex_pool = pool
        yield
    finally:
        await pool.close()


app = FastAPI(
    title="MARINA FLEX Read-Only Control Plane",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None, redoc_url=None, openapi_url=None,
)


async def _switch_to_reader(conn: asyncpg.Connection, reader_role: str, scope: str, value: str):
    """Call only *inside* a transaction; reader role is a code literal."""
    if reader_role not in ("flex_identity_reader", "flex_hotel_reader", "flex_platform_admin_reader"):
        raise RuntimeError("Invalid database reader role")
    await conn.execute("SELECT set_config($1,$2,true)", scope, value)
    # Role string has already been allowlisted; no user input reaches SQL syntax.
    await conn.execute("SET LOCAL ROLE " + reader_role)


async def resolve_platform_principal(
    request: Request, authorization: str | None = Header(default=None),
) -> PlatformPrincipal:
    subject, mfa = verify_platform_token(authorization)
    pool = getattr(request.app.state, "flex_pool", None)
    if pool is None:
        raise HTTPException(503, detail="FLEX database not ready")
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch_to_reader(
                conn, "flex_identity_reader", "flex.authorized_subject_id", subject
            )
            row = await conn.fetchrow(
                "SELECT role FROM flex_platform_memberships WHERE subject_id=$1 AND active=true",
                subject,
            )
            if row is None:
                raise HTTPException(403, detail="No active FLEX membership")
            grants = await conn.fetch(
                "SELECT hotel_id FROM flex_platform_hotel_grants WHERE subject_id=$1",
                subject,
            )
            agent_id = await conn.fetchval(
                "SELECT id FROM flex_agents WHERE platform_subject_id=$1 AND status='ACTIVE'",
                subject,
            )
            investor_id = await conn.fetchval(
                "SELECT id FROM flex_investors WHERE platform_subject_id=$1 AND status='ACTIVE'",
                subject,
            )
            return PlatformPrincipal(
                subject_id=subject, role=row["role"], mfa_verified=mfa,
                hotel_ids=frozenset(str(v["hotel_id"]) for v in grants),
                agent_id=str(agent_id) if agent_id is not None else None,
                investor_id=str(investor_id) if investor_id is not None else None,
            )


def _require_hotel_read(principal: PlatformPrincipal, hotel_id: uuid.UUID):
    if not platform_action_allowed(
        principal, action="VIEW_HOTEL_BILLING", hotel_id=str(hotel_id)
    ):
        # 404 limits revelation of hotel existence to unauthorized callers.
        raise HTTPException(404, detail="Hotel not found")


def _reader_for(principal: PlatformPrincipal) -> str:
    if principal.role == "SUPER_ADMIN":
        if not principal.mfa_verified:
            raise HTTPException(403, detail="MFA required")
        return "flex_platform_admin_reader"
    return "flex_hotel_reader"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "marina-flex", "mutation_api": False}


@app.get("/v1/me")
async def me(principal: PlatformPrincipal = Depends(resolve_platform_principal)):
    return {
        "role": principal.role,
        "hotels": sorted(principal.hotel_ids),
        "agent_id": principal.agent_id,
        "investor_id": principal.investor_id,
    }


@app.get("/v1/hotels")
async def hotels(
    request: Request, principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    if principal.role != "SUPER_ADMIN" or not principal.mfa_verified:
        raise HTTPException(403, detail="Admin with MFA required")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch_to_reader(conn, "flex_platform_admin_reader", "flex.unused", "1")
            rows = await conn.fetch(
                "SELECT id,display_name,status,billing_currency FROM flex_hotels "
                "ORDER BY created_at DESC,id DESC LIMIT 100"
            )
            return [
                dict(id=str(r["id"]), name=r["display_name"], status=r["status"],
                     currency=r["billing_currency"])
                for r in rows
            ]


@app.get("/v1/hotels/{hotel_id}/subscription")
async def hotel_subscription(
    hotel_id: uuid.UUID, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    _require_hotel_read(principal, hotel_id)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch_to_reader(
                conn, _reader_for(principal), "flex.authorized_hotel_id", str(hotel_id)
            )
            row = await conn.fetchrow(
                "SELECT id,status,enforcement,period_start,period_end,grace_until "
                "FROM flex_subscriptions WHERE hotel_id=$1 "
                "AND status <> 'CANCELLED' ORDER BY created_at DESC LIMIT 1",
                hotel_id,
            )
            if row is None:
                raise HTTPException(404, detail="Subscription not found")
            return {
                "id": str(row["id"]), "status": row["status"],
                "enforcement": row["enforcement"],
                "period_start": row["period_start"].isoformat(),
                "period_end": row["period_end"].isoformat(),
                "grace_until": (
                    row["grace_until"].isoformat() if row["grace_until"] else None
                ),
            }


@app.get("/v1/hotels/{hotel_id}/invoices")
async def hotel_invoices(
    hotel_id: uuid.UUID, request: Request,
    principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    _require_hotel_read(principal, hotel_id)
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch_to_reader(
                conn, _reader_for(principal), "flex.authorized_hotel_id", str(hotel_id)
            )
            rows = await conn.fetch(
                "SELECT id,invoice_number,status,total,currency,due_at "
                "FROM flex_invoices WHERE hotel_id=$1 "
                "ORDER BY created_at DESC,id DESC LIMIT 100",
                hotel_id,
            )
            return [
                dict(
                    id=str(r["id"]), number=r["invoice_number"],
                    status=r["status"], total=str(r["total"]),
                    currency=r["currency"],
                    due_at=r["due_at"].isoformat() if r["due_at"] else None,
                )
                for r in rows
            ]


@app.get("/v1/catalog")
async def commercial_catalog(
    request: Request, principal: PlatformPrincipal = Depends(resolve_platform_principal),
):
    """Published LIST prices only; contract discounts and feature grants are private.

    This is informational and never enables a PMS feature or creates an invoice.
    """
    if principal.role not in {"HOTEL_OWNER", "SUPER_ADMIN"}:
        raise HTTPException(403, detail="Catalog not available to this role")
    if principal.role == "SUPER_ADMIN" and not principal.mfa_verified:
        raise HTTPException(403, detail="MFA required")
    if principal.role == "HOTEL_OWNER" and not principal.hotel_ids:
        raise HTTPException(403, detail="No assigned hotel")
    async with request.app.state.flex_pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await _switch_to_reader(
                conn, _reader_for(principal), "flex.authorized_hotel_id",
                sorted(principal.hotel_ids)[0] if principal.hotel_ids else "",
            )
            rows = await conn.fetch(
                "SELECT s.sku,s.title,s.capability_key,p.version,p.monthly_price,p.currency "
                "FROM flex_skus s "
                "JOIN LATERAL ( "
                "  SELECT version,monthly_price,currency FROM flex_price_versions "
                "  WHERE sku=s.sku AND valid_from<=now() "
                "    AND (valid_to IS NULL OR valid_to>now()) "
                "    AND currency='KGS' "
                "  ORDER BY valid_from DESC,version DESC LIMIT 1 "
                ") p ON true "
                "WHERE s.product_status='AVAILABLE' "
                "ORDER BY s.sku LIMIT 100"
            )
            return [
                {"sku": r["sku"], "name": r["title"],
                 "capability": r["capability_key"], "price_version": r["version"],
                 "monthly_list_price": str(r["monthly_price"]), "currency": r["currency"]}
                for r in rows
            ]
