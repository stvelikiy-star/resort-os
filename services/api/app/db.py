import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI


DEV_DATABASE_URL = "postgresql://resort:resort@localhost:5432/resort_os"


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    if not value:
        if app_env in {"production", "prod"}:
            raise RuntimeError("DATABASE_URL is required in production; refusing development fallback")
        value = DEV_DATABASE_URL
    # Prisma commonly appends ?schema=public; asyncpg does not need it.
    return value.replace("?schema=public", "")


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
