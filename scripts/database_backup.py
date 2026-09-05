#!/usr/bin/env python3
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS, clean_postgres_url, migration_names_match_exactly

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
BACKUP_FORMAT = "three-crowns-postgres-backup-v3"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def collect_facts(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn, timeout=15)
    try:
        prop = await conn.fetchrow("SELECT id,code,name,timezone,currency FROM properties WHERE code=$1", PROPERTY_CODE)
        if not prop:
            raise RuntimeError(f"Property {PROPERTY_CODE} is not loaded")
        pid = prop["id"]

        constraint_rows = await conn.fetch(
            "SELECT conname FROM pg_constraint WHERE conname = ANY($1::text[]) ORDER BY conname",
            list(CRITICAL_CONSTRAINTS),
        )
        constraints = [row["conname"] for row in constraint_rows]
        missing_constraints = sorted(CRITICAL_CONSTRAINTS - set(constraints))
        if missing_constraints:
            raise RuntimeError("Database is missing critical constraints: " + ", ".join(missing_constraints))

        migration_table = await conn.fetchval("SELECT to_regclass('public._prisma_migrations') IS NOT NULL")
        migrations = []
        if migration_table:
            rows = await conn.fetch(
                '''
                SELECT migration_name,checksum,finished_at,rolled_back_at
                FROM _prisma_migrations
                WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL
                ORDER BY started_at,migration_name
                '''
            )
            migrations = [
                {
                    "migration_name": row["migration_name"],
                    "checksum": row["checksum"],
                }
                for row in rows
            ]

        server_version = await conn.fetchval("SHOW server_version")
        payment_count = await conn.fetchval(
            '''
            SELECT COUNT(*)
            FROM payments p
            WHERE EXISTS (
                SELECT 1 FROM reservation_requests rr
                WHERE rr.id=p."requestId" AND rr."propertyId"=$1
            ) OR EXISTS (
                SELECT 1 FROM reservations r
                WHERE r.id=p."reservationId" AND r."propertyId"=$1
            )
            ''',
            pid,
        )
        return {
            "property": {
                "code": prop["code"],
                "name": prop["name"],
                "timezone": prop["timezone"],
                "currency": prop["currency"],
            },
            "counts": {
                "rooms": await conn.fetchval('SELECT COUNT(*) FROM rooms WHERE "propertyId"=$1', pid),
                "room_types": await conn.fetchval('SELECT COUNT(*) FROM room_types WHERE "propertyId"=$1', pid),
                "rate_periods": await conn.fetchval('''SELECT COUNT(*) FROM rate_periods rp JOIN rate_plans p ON p.id=rp."ratePlanId" WHERE p."propertyId"=$1''', pid),
                "guests": await conn.fetchval('SELECT COUNT(*) FROM guests WHERE "propertyId"=$1', pid),
                "reservation_requests": await conn.fetchval('SELECT COUNT(*) FROM reservation_requests WHERE "propertyId"=$1', pid),
                "reservations": await conn.fetchval('SELECT COUNT(*) FROM reservations WHERE "propertyId"=$1', pid),
                # Payment intentionally has no denormalized propertyId. Its property
                # authority is derived through ReservationRequest/Reservation.
                "payments": payment_count,
                "conversations": await conn.fetchval('SELECT COUNT(*) FROM conversations WHERE "propertyId"=$1', pid),
                "staff_users": await conn.fetchval('SELECT COUNT(*) FROM staff_users WHERE "propertyId"=$1', pid),
                "operational_tasks": await conn.fetchval('SELECT COUNT(*) FROM operational_tasks WHERE "propertyId"=$1', pid),
                "owner_analytics_snapshots": await conn.fetchval('SELECT COUNT(*) FROM owner_analytics_snapshots WHERE "propertyId"=$1', pid),
                "guest_engagements": await conn.fetchval('SELECT COUNT(*) FROM guest_engagements WHERE "propertyId"=$1', pid),
                "audit_logs": await conn.fetchval('SELECT COUNT(*) FROM audit_logs WHERE "propertyId"=$1', pid),
            },
            "database": {
                "postgres_version": server_version,
                "critical_constraints": constraints,
                "migration_history_present": bool(migration_table),
                "expected_migration_names": list(EXPECTED_MIGRATIONS),
                "applied_migrations": migrations,
            },
        }
    finally:
        await conn.close()


async def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2

    dsn = clean_postgres_url(database_url)
    backup_dir = Path(os.environ.get("BACKUP_DIR", "backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    stamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    backup_file = backup_dir / f"three-crowns-{stamp}.dump"
    manifest_file = backup_dir / f"three-crowns-{stamp}.manifest.json"

    facts = await collect_facts(dsn)
    require_migration_history = os.environ.get("REQUIRE_MIGRATION_HISTORY", "true").lower() not in {"0", "false", "no"}
    if require_migration_history and not facts["database"]["migration_history_present"]:
        print("Backup rejected: _prisma_migrations is missing", file=sys.stderr)
        return 1
    migration_names = [row["migration_name"] for row in facts["database"]["applied_migrations"]]
    if require_migration_history and not migration_names_match_exactly(migration_names):
        print(
            "Backup rejected: migration ledger mismatch; expected "
            + ",".join(EXPECTED_MIGRATIONS)
            + "; found "
            + ",".join(migration_names),
            file=sys.stderr,
        )
        return 1

    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        str(backup_file),
        dsn,
    ]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        print("pg_dump failed", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)
        return completed.returncode or 1

    size_bytes = backup_file.stat().st_size
    if size_bytes <= 0:
        print("Backup file is empty", file=sys.stderr)
        return 1

    checksum = sha256_file(backup_file)
    manifest = {
        "format": BACKUP_FORMAT,
        "created_at": created_at.isoformat(),
        "property_code": PROPERTY_CODE,
        "backup_file": backup_file.name,
        "size_bytes": size_bytes,
        "sha256": checksum,
        "facts": facts,
    }
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    print(f"BACKUP_FILE={backup_file}")
    print(f"BACKUP_MANIFEST={manifest_file}")
    print(f"BACKUP_SHA256={checksum}")
    print(f"BACKUP_SIZE_BYTES={size_bytes}")
    print(f"BACKUP_MIGRATIONS={len(facts['database']['applied_migrations'])}")
    print(f"BACKUP_CRITICAL_CONSTRAINTS={len(facts['database']['critical_constraints'])}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
