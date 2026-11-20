import os
import asyncio
import logging
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg
from fastapi import FastAPI


DEV_DATABASE_URL = "postgresql://resort:resort@localhost:5432/resort_os"


def clean_asyncpg_url(value: str) -> str:
    """Remove Prisma-only schema= while preserving managed PostgreSQL options.

    Prisma accepts `schema=public`; asyncpg does not need that parameter. Production
    DBaaS URLs can also contain transport options such as sslmode/connect_timeout, so
    string replacement is unsafe: it can drop or corrupt the query-string delimiter.
    """
    parts = urlsplit(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() != "schema"
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if not value:
        if app_env in {"production", "prod"}:
            raise RuntimeError("DATABASE_URL is required in production; refusing development fallback")
        value = DEV_DATABASE_URL
    return clean_asyncpg_url(value)


async def expire_shared_holds_once(pool) -> int:
    """Sweep expired holds of verified shared properties, without a global hotel selector.

    Each hotel uses an independent transaction, and expire_holds takes row locks
    with SKIP LOCKED. Concurrent API processes therefore cannot release the same
    active inventory block twice. This is an eventual expiry worker, not a TTL
    authorization bypass: conversion separately validates expiresAt.
    """
    from .pms_holds import expire_holds

    async with pool.acquire() as conn:
        properties = await conn.fetch(
            """SELECT p.id
               FROM properties p
               JOIN tenants t ON t.id=p."tenantId"
               ORDER BY p.id"""
        )
    expired = 0
    for row in properties:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    expired += await expire_holds(conn, row["id"])
        except Exception:
            logging.getLogger(__name__).exception(
                "Shared HOLD expiry failed for property_id=%s", row["id"]
            )
    return expired


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(
        dsn=database_url(),
        min_size=1,
        max_size=10,
        command_timeout=15,
    )
    async def hold_expiration_worker():
        # Legacy deployments remain pinned to one configured property. Shared
        # staging enumerates only DB-linked tenant properties; no client-supplied
        # hotel identifier can influence the expiry job.
        from .auth import MARINA_SHARED_AUTH_PREVIEW_ENABLED, PROPERTY_CODE
        from .pms_holds import expire_holds
        while True:
            try:
                if MARINA_SHARED_AUTH_PREVIEW_ENABLED:
                    await expire_shared_holds_once(app.state.db)
                else:
                    async with app.state.db.acquire() as conn:
                        async with conn.transaction():
                            property_id = await conn.fetchval(
                                'SELECT id FROM properties WHERE code=$1', PROPERTY_CODE
                            )
                            if property_id is not None:
                                await expire_holds(conn, property_id)
            except Exception:
                logging.getLogger(__name__).exception("HOLD expiration worker failed")
            await asyncio.sleep(30)

    worker = asyncio.create_task(hold_expiration_worker())
    try:
        yield
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        await app.state.db.close()
