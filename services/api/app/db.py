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


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await asyncpg.create_pool(
        dsn=database_url(),
        min_size=1,
        max_size=10,
        command_timeout=15,
    )
    async def hold_expiration_worker():
        # Only a property-pinned runtime may run this background mutation.
        # Tenant-context can be enabled in separate property-pinned processes.
        # Only shared-auth preview lacks an authorized property-bound worker;
        # a dedicated shared multi-hotel scheduler is required later.
        from .auth import MARINA_SHARED_AUTH_PREVIEW_ENABLED, PROPERTY_CODE
        from .pms_holds import expire_holds
        while True:
            try:
                if not MARINA_SHARED_AUTH_PREVIEW_ENABLED:
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
