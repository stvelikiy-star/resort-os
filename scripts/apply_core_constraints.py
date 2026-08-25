import asyncio
import os
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "packages" / "database" / "sql" / "001_core_constraints.sql"


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = await asyncpg.connect(database_url())
    try:
        await conn.execute(sql)
        print("Core constraints applied")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
