"""Fail-closed Prisma migration ledger check reused by the shared restore gate."""
from __future__ import annotations

import hashlib
from pathlib import Path


async def verify_committed_ledger(conn, root: Path) -> dict[str, str]:
    path = root / "packages" / "database" / "prisma" / "migrations"
    files = {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in path.glob("*/migration.sql")}
    if not files:
        raise RuntimeError("No committed Prisma migrations")
    rows = await conn.fetch('''
        SELECT migration_name,checksum,finished_at,rolled_back_at
        FROM _prisma_migrations
    ''')
    if len(rows) != len(files):
        raise RuntimeError("Applied migration count mismatches source")
    applied = {}
    for row in rows:
        name = row["migration_name"]
        if name in applied or row["finished_at"] is None or row["rolled_back_at"] is not None:
            raise RuntimeError("Migration history contains incomplete/duplicate/rolled back row")
        applied[name] = row["checksum"]
    if applied != files:
        raise RuntimeError("Prisma migration checksums/source do not match")
    return applied
