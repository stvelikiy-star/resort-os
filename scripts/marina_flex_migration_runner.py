"""Incremental FLEX-only migration runner; default is read-only plan.

Requires an existing verified registry. Never bootstraps an unknown database,
adopts unregistered objects, or applies settlement migration 0009.
"""
import argparse
import asyncio
import hashlib
import os
from pathlib import Path
import re
import subprocess

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
FROZEN = "SKIPPED_PAYMENT_FREEZE"


def manifest():
    result = {}
    for path in sorted((ROOT / "docs/flex/sql").glob("[0-9][0-9][0-9][0-9]_*.sql")):
        raw = path.read_bytes()
        number = int(path.name[:4])
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if number in result:
            raise ValueError("Duplicate migration ID")
        result[number] = (path.name, digest, raw.decode("utf-8"))
    if sorted(result) != list(range(1, len(result) + 1)):
        raise ValueError("Migration IDs must be contiguous")
    return result


def plan(rows, files):
    seen = set()
    for row in rows:
        n = row["migration_id"]
        if n not in files or n in seen:
            raise ValueError("Unknown or duplicate registered migration")
        name, digest, _ = files[n]
        if row["filename"] != name or row["git_blob_sha"].strip() != digest:
            raise ValueError(f"Migration {n:04}: SHA or filename mismatch")
        expected = FROZEN if n == 9 else "APPLIED"
        if row["disposition"] != expected:
            raise ValueError(f"Migration {n:04}: invalid disposition")
        seen.add(n)
    if sorted(seen) != list(range(1, len(seen) + 1)):
        raise ValueError("Migration registry has a gap")
    if not set(range(1, 16)).issubset(seen):
        raise ValueError("Baseline 0001–0015 must be verified and registered before incremental apply")
    return [n for n in sorted(files) if n not in seen]


def body(sql):
    # Only strip the reviewed outer transaction; preserve PL/pgSQL blocks.
    m = re.fullmatch(r"(?:\s|--[^\n]*\n)*BEGIN;\s*(.*?)\s*COMMIT;\s*", sql, re.S | re.I)
    if not m:
        raise ValueError("Expected outer BEGIN/COMMIT")
    return m.group(1)


async def run(args):
    files = manifest()
    release = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--", "docs/flex/sql"], cwd=ROOT, text=True).strip():
        raise ValueError("Migration files must match a clean Git checkout")
    conn = await asyncpg.connect(os.environ["FLEX_MIGRATION_DATABASE_URL"])
    try:
        async with conn.transaction(readonly=not args.apply):
            db, role = await conn.fetchrow("SELECT current_database(), current_user")
            expected = ("flex_ci", "flex_ci", "public") if args.ci else ("flex_qa", "flex_qa_owner", "flex_private")
            if (db, role, args.schema) != expected:
                raise ValueError("Unexpected FLEX migration database, role or schema")
            if args.apply and not args.ci:
                if args.approve_qa != release:
                    raise ValueError("QA apply requires explicit approval of exact release SHA")
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname IN ('auth','storage','realtime','supabase_functions')) OR EXISTS(SELECT 1 FROM pg_tables WHERE tablename IN ('properties','reservations','guests','staff_users','folio'))"):
                raise ValueError("Non-FLEX database detected")
            if args.apply:
                await conn.execute("SELECT pg_advisory_xact_lock(hashtext('MARINA_FLEX_MIGRATION_RUNNER'))")
            await conn.execute("SET LOCAL search_path TO " + args.schema + ", pg_catalog")
            rows = await conn.fetch("SELECT migration_id,filename,git_blob_sha,disposition FROM flex_schema_migrations ORDER BY migration_id")
            pending = plan(rows, files)
            for n in pending:
                name, digest, sql = files[n]
                if n == 9:
                    raise ValueError("Payment freeze violation")
                print(f"{'APPLY' if args.apply else 'PENDING'} {name} {digest}")
                if args.apply:
                    await conn.execute(body(sql))
                    await conn.execute("INSERT INTO flex_schema_migrations(migration_id,filename,git_blob_sha,release_sha,disposition) VALUES($1,$2,$3,$4,'APPLIED')", n,name,digest,release)
            print(f"FLEX migrations: {len(pending)} pending; 0009 remains frozen")
    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--ci", action="store_true")
    parser.add_argument("--schema", choices=["public", "flex_private"], default="flex_private")
    parser.add_argument("--approve-qa")
    asyncio.run(run(parser.parse_args()))
