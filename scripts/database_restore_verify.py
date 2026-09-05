#!/usr/bin/env python3
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS, clean_postgres_url, migration_names_match_exactly

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
SUPPORTED_FORMATS = {
    "three-crowns-postgres-backup-v1",
    "three-crowns-postgres-backup-v2",
    "three-crowns-postgres-backup-v3",
}


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
            raise RuntimeError(f"Property {PROPERTY_CODE} is not loaded in restored database")
        pid = prop["id"]
        rows = await conn.fetch("SELECT conname FROM pg_constraint WHERE conname = ANY($1::text[]) ORDER BY conname", list(CRITICAL_CONSTRAINTS))
        constraints = [row["conname"] for row in rows]
        migration_table = await conn.fetchval("SELECT to_regclass('public._prisma_migrations') IS NOT NULL")
        migrations = []
        if migration_table:
            migration_rows = await conn.fetch(
                '''
                SELECT migration_name,checksum
                FROM _prisma_migrations
                WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL
                ORDER BY started_at,migration_name
                '''
            )
            migrations = [
                {"migration_name": row["migration_name"], "checksum": row["checksum"]}
                for row in migration_rows
            ]
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
                "payments": payment_count,
                "conversations": await conn.fetchval('SELECT COUNT(*) FROM conversations WHERE "propertyId"=$1', pid),
                "staff_users": await conn.fetchval('SELECT COUNT(*) FROM staff_users WHERE "propertyId"=$1', pid),
                "operational_tasks": await conn.fetchval('SELECT COUNT(*) FROM operational_tasks WHERE "propertyId"=$1', pid),
                "owner_analytics_snapshots": await conn.fetchval('SELECT COUNT(*) FROM owner_analytics_snapshots WHERE "propertyId"=$1', pid),
                "guest_engagements": await conn.fetchval('SELECT COUNT(*) FROM guest_engagements WHERE "propertyId"=$1', pid),
                "audit_logs": await conn.fetchval('SELECT COUNT(*) FROM audit_logs WHERE "propertyId"=$1', pid),
            },
            "database": {
                "critical_constraints": constraints,
                "missing_critical_constraints": sorted(CRITICAL_CONSTRAINTS - set(constraints)),
                "migration_history_present": bool(migration_table),
                "applied_migrations": migrations,
            },
        }
    finally:
        await conn.close()


async def main() -> int:
    backup_path = os.environ.get("BACKUP_FILE", "").strip()
    restore_url = os.environ.get("RESTORE_DATABASE_URL", "").strip()
    if not backup_path:
        print("BACKUP_FILE is required", file=sys.stderr)
        return 2
    if not restore_url:
        print("RESTORE_DATABASE_URL is required", file=sys.stderr)
        return 2

    backup_file = Path(backup_path).resolve()
    if not backup_file.is_file():
        print(f"Backup file not found: {backup_file}", file=sys.stderr)
        return 2

    manifest_path = Path(os.environ.get("BACKUP_MANIFEST", backup_file.with_suffix(".manifest.json"))).resolve()
    if not manifest_path.is_file():
        print(f"Backup manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_format = manifest.get("format")
    if manifest_format not in SUPPORTED_FORMATS:
        print("Unsupported backup manifest format", file=sys.stderr)
        return 2

    actual_sha = sha256_file(backup_file)
    if actual_sha != manifest.get("sha256"):
        print("Backup SHA256 mismatch", file=sys.stderr)
        return 1
    if backup_file.stat().st_size != manifest.get("size_bytes"):
        print("Backup size mismatch", file=sys.stderr)
        return 1

    restore_dsn = clean_postgres_url(restore_url)
    command = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-acl",
        "--dbname",
        restore_dsn,
        str(backup_file),
    ]
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        print("pg_restore failed", file=sys.stderr)
        if completed.stderr:
            print(completed.stderr.strip(), file=sys.stderr)
        return completed.returncode or 1

    restored = await collect_facts(restore_dsn)
    expected = manifest.get("facts") or {}
    errors: list[str] = []

    expected_property = expected.get("property") or {}
    for key in ("code", "name", "timezone", "currency"):
        if restored["property"].get(key) != expected_property.get(key):
            errors.append(f"Property fact mismatch for {key}")

    expected_counts = expected.get("counts") or {}
    for key, expected_value in expected_counts.items():
        actual_value = restored["counts"].get(key)
        if actual_value != expected_value:
            errors.append(f"Count mismatch for {key}: expected {expected_value}, found {actual_value}")

    if restored["database"]["missing_critical_constraints"]:
        errors.append("Missing critical constraints after restore: " + ", ".join(restored["database"]["missing_critical_constraints"]))

    restored_migration_names = [row["migration_name"] for row in restored["database"]["applied_migrations"]]
    if not migration_names_match_exactly(restored_migration_names):
        errors.append(
            "Restored migration ledger mismatch: expected "
            + ",".join(EXPECTED_MIGRATIONS)
            + "; found "
            + ",".join(restored_migration_names)
        )

    expected_database = expected.get("database") or {}
    if manifest_format in {"three-crowns-postgres-backup-v2", "three-crowns-postgres-backup-v3"}:
        if not restored["database"]["migration_history_present"]:
            errors.append("_prisma_migrations is missing after restore")
        expected_constraints = sorted(expected_database.get("critical_constraints") or [])
        # V3 fingerprints the current complete critical-constraint contract. V2 is
        # accepted only as a historical manifest format; current-release restore
        # still must pass CRITICAL_CONSTRAINTS above.
        if expected_constraints and expected_constraints != sorted(restored["database"]["critical_constraints"]):
            errors.append("Critical constraint fingerprint differs from backup manifest")
        expected_migrations = expected_database.get("applied_migrations") or []
        if expected_migrations and expected_migrations != restored["database"]["applied_migrations"]:
            errors.append("Applied Prisma migration ledger differs from backup manifest")
        if expected_database.get("migration_history_present") is not True:
            errors.append("Backup manifest did not prove migration history at backup time")

    if manifest_format == "three-crowns-postgres-backup-v3":
        manifest_expected = expected_database.get("expected_migration_names") or []
        if tuple(manifest_expected) != EXPECTED_MIGRATIONS:
            errors.append("V3 backup manifest does not identify the exact current release migration chain")

    print(f"BACKUP_SHA256={actual_sha}")
    print(f"RESTORED_PROPERTY={restored['property']['code']}")
    for key, value in restored["counts"].items():
        print(f"RESTORED_{key.upper()}={value}")
    print(f"RESTORED_CRITICAL_CONSTRAINTS={len(restored['database']['critical_constraints'])}")
    print(f"RESTORED_MIGRATION_HISTORY_PRESENT={restored['database']['migration_history_present']}")
    print(f"RESTORED_APPLIED_MIGRATIONS={len(restored['database']['applied_migrations'])}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print("RESTORE_VERIFICATION=FAILED", file=sys.stderr)
        return 1

    print(f"LAST_VERIFIED_BACKUP_AT={manifest['created_at']}")
    print("RESTORE_VERIFICATION=SUCCESS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
