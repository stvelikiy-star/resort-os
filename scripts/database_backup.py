#!/usr/bin/env python3
import asyncio
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")


def clean_postgres_url(value: str) -> str:
    parts = urlsplit(value)
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True) if key != "schema"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


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
                "reservation_requests": await conn.fetchval('SELECT COUNT(*) FROM reservation_requests WHERE "propertyId"=$1', pid),
                "reservations": await conn.fetchval('SELECT COUNT(*) FROM reservations WHERE "propertyId"=$1', pid),
                "staff_users": await conn.fetchval('SELECT COUNT(*) FROM staff_users WHERE "propertyId"=$1', pid),
                "operational_tasks": await conn.fetchval('SELECT COUNT(*) FROM operational_tasks WHERE "propertyId"=$1', pid),
                "audit_logs": await conn.fetchval('SELECT COUNT(*) FROM audit_logs WHERE "propertyId"=$1', pid),
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
        "format": "three-crowns-postgres-backup-v1",
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
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
