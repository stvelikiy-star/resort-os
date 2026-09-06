import os
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
    try:
        yield
    finally:
        await app.state.db.close()
