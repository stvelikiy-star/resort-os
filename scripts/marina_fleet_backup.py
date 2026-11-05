#!/usr/bin/env python3
"""Offline-capable, local-only per-hotel PostgreSQL backup; never restores or deletes data."""
import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLEET = ROOT / ".marina-fleet"
BACKUPS = ROOT / ".marina-backups"

def run(slug: str):
    from marina_fleet import env_path, parse_env, COMPOSE
    path = env_path(slug)
    if not path.is_file():
        raise SystemExit("Hotel not registered")
    env = parse_env(path)
    db_name = "marina_" + slug
    if env["MARINA_FLEET_DB"] != db_name:
        raise SystemExit("Unexpected database target")
    directory = BACKUPS / slug
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = directory / f"{db_name}_{timestamp}.dump"
    tmp = directory / (dest.name + ".partial")
    cmd = [
        "docker", "compose", "--env-file", str(path), "-f", str(COMPOSE),
        "exec", "-T", "postgres", "sh", "-c",
        'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc',
    ]
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            subprocess.run(cmd, cwd=ROOT, check=True, stdout=f)
        if tmp.stat().st_size < 1000:
            raise RuntimeError("Suspiciously small backup")
        with tmp.open("rb") as f:
            if f.read(5) != b"PGDMP":
                raise RuntimeError("Invalid PostgreSQL custom dump signature")
        tmp.replace(dest)
        print(f"BACKUP_CREATED {dest} ({dest.stat().st_size} bytes)")
        print("Copy backups to encrypted offsite storage and perform an isolated restore test before production.")
    finally:
        if tmp.exists():
            tmp.unlink()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    args = parser.parse_args()
    run(args.slug)
