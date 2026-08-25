import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
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
