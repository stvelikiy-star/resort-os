"""Isolated MARINA FLEX QA connectivity probe for Vercel FastAPI.

Diagnostic only. No PMS imports, no credentials in responses, no writes,
no authentication fallback, and no commercial or payment endpoints.
Do NOT mistake this probe for the full FLEX control-plane API.
"""
from __future__ import annotations

import os
from urllib.parse import parse_qs, urlsplit

import asyncpg
from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="MARINA FLEX QA Database Readiness",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

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
            "mode": "QA_DIAGNOSTIC_ONLY",
            "database": "isolated_neon",
            "least_privilege": True,
            "payments_enabled": False,
            "payouts_enabled": False,
            "onboarding_enabled": False,
            "real_user_auth_enabled": False,
        }
    except HTTPException:
        raise
    except (asyncpg.PostgresError, OSError, TimeoutError, ValueError):
        raise HTTPException(503, detail="FLEX_QA_DATABASE_UNAVAILABLE") from None
    finally:
        if connection is not None:
            await connection.close()
