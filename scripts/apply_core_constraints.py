import asyncio
import os
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "packages" / "database" / "sql"


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os")
    return value.replace("?schema=public", "")


async def main() -> None:
    sql_files = sorted(SQL_DIR.glob("*.sql"))
    if not sql_files:
        raise RuntimeError(f"No SQL modules found in {SQL_DIR}")

    conn = await asyncpg.connect(database_url())
    try:
        for sql_file in sql_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
            print(f"Applied {sql_file.name}")
        print(f"Core SQL applied: {len(sql_files)} module(s)")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
