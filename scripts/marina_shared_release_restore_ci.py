#!/usr/bin/env python3
"""P0 full logical restore of the *shared* two-hotel PMS browser-CI database.

Uses existing snapshot() / pg_arguments() from the accepted property-pinned
restore gate, but proves a single shared-ASGI runtime with two hotel owners.
No DROP, TRUNCATE, production DSN, customer data, or external network allowed.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, parse_qsl, unquote

import asyncpg

from marina_two_property_restore_e2e import snapshot, pg_arguments
from marina_shared_live_browser_db import PASSWORD, RECEIPTS

ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "marina_shared_browser_ci"
TARGET_NAME = "marina_shared_browser_restore_ci"
SOURCE_ENV = "DATABASE_URL"
TARGET_ENV = "RESTORE_DATABASE_URL"
CONFIRM = "ISOLATED_SHARED_TWO_HOTEL_RESTORE_ONLY"


def validate_restore_urls(source: str, target: str) -> tuple[str, str]:
    if (os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM") !=
            "DISPOSABLE_TWO_HOTEL_BROWSER_CI" or
            os.environ.get("MARINA_SHARED_RESTORE_CI_CONFIRM") != CONFIRM):
        raise RuntimeError("Explicit synthetic shared restore confirmations are required")
    if (os.environ.get("APP_ENV") != "staging" or
            os.environ.get("MARINA_TENANT_CONTEXT_ENABLED") != "true" or
            os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") != "true" or
            os.environ.get("PROPERTY_CODE") != "MARINA_BROWSER_CI"):
        raise RuntimeError("Not the isolated shared-auth CI profile")
    parsed = []
    for value, expected in ((source, SOURCE_NAME), (target, TARGET_NAME)):
        u = urlsplit(value)
        if (u.scheme not in ("postgres", "postgresql") or
                u.hostname not in ("127.0.0.1", "localhost") or
                unquote(u.path) != "/" + expected or
                u.fragment or
                parse_qsl(u.query, keep_blank_values=True) not in ([], [("schema", "public")]) or
                not u.username or not u.password or
                u.port != 5432):
            raise RuntimeError("Refusing non-disposable local PostgreSQL restore URL")
        parsed.append(u)
    if parsed[0].hostname != parsed[1].hostname or parsed[0].username != parsed[1].username:
        raise RuntimeError("Restore must use same isolated host and role")
    if not PASSWORD.startswith("synthetic-ci-only-") or len(PASSWORD) < 16:
        raise RuntimeError("Synthetic-only role password missing")
    if not RECEIPTS.is_file():
        raise RuntimeError("Two-hotel browser receipts not found")
    # Strip only the Prisma schema marker after validating it is safe.
    return source.split("?", 1)[0], target.split("?", 1)[0]


def receipt_rows() -> dict:
    receipts = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    if set(receipts) != {"HOTEL_A", "HOTEL_B"}:
        raise AssertionError("Expected two separately authenticated hotel browser receipts")
    for hotel in receipts:
        item = receipts[hotel]
        for key in ("reservation_id", "room_id", "manual_payment_id",
                    "manual_amount_kgs", "maintenance_task_id"):
            if not item.get(key):
                raise AssertionError(f"{hotel} missing real browser receipt: {key}")
    return receipts


async def preflight_databases(source: str, target: str) -> dict:
    from prisma_migration_ledger import verify_committed_ledger
    source_conn = await asyncpg.connect(source)
    try:
        p = await source_conn.fetch('''
            SELECT t.code AS tenant_code,p.code AS hotel
            FROM properties p JOIN tenants t ON t.id=p."tenantId"
            ORDER BY p.code
        ''')
        if [(r["tenant_code"], r["hotel"]) for r in p] != [
                ("tenant_a", "HOTEL_A"), ("tenant_b", "HOTEL_B")]:
            raise RuntimeError("Source is not the exact disposable two-hotel shared fixture")
        ledger = await verify_committed_ledger(source_conn, ROOT)
        if await source_conn.fetchval("SELECT count(*) FROM reservations") < 2:
            raise RuntimeError("Source has no completed two-hotel PMS acceptance records")
        if await source_conn.fetchval("SELECT count(*) FROM payments") < 2:
            raise RuntimeError("Source has no real isolated manual payment records")
    finally:
        await source_conn.close()
    target_conn = await asyncpg.connect(target)
    try:
        cnt = await target_conn.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")
        if cnt:
            raise RuntimeError("Restore target is not empty; refusing to overwrite")
        if await target_conn.fetchval("SELECT count(*) FROM pg_indexes WHERE schemaname='public'"):
            raise RuntimeError("Restore target contains public indexes")
    finally:
        await target_conn.close()
    return ledger


async def public_schema_metadata(dsn: str) -> dict:
    """Compare indexes and columns in addition to accepted all-row/constraint snapshot."""
    conn = await asyncpg.connect(dsn)
    try:
        index_rows = await conn.fetch(
            "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname")
        col_rows = await conn.fetch('''
            SELECT table_name,column_name,udt_name,is_nullable,column_default
            FROM information_schema.columns WHERE table_schema='public'
            ORDER BY table_name,ordinal_position
        ''')
        return {
            "indexes": [dict(row) for row in index_rows],
            "columns": [dict(row) for row in col_rows],
        }
    finally:
        await conn.close()


def run_command(argv: list[str], env: dict | None = None) -> None:
    subprocess.run(argv, env=env, check=True, stdout=subprocess.DEVNULL)


def assert_equal(before: dict, restored: dict, name: str) -> None:
    if before != restored:
        # No raw customer-like rows or credential material in CI diagnostics.
        raise AssertionError(
            name + " differs after restore; comparison failed. "
            + f"source_items={len(before)}, restored_items={len(restored)}"
        )


def restore() -> None:
    src, dst = validate_restore_urls(
        os.environ.get(SOURCE_ENV, ""), os.environ.get(TARGET_ENV, ""))
    receipt_rows()
    ledger = asyncio.run(preflight_databases(src, dst))
    original = asyncio.run(snapshot(src))
    source_schema = asyncio.run(public_schema_metadata(src))

    with tempfile.TemporaryDirectory(prefix="marina-shared-restore-") as directory:
        backup = Path(directory) / "two-hotel-shared.dump"
        source_args, source_env = pg_arguments(src)
        run_command(["pg_dump", *source_args, "--format=custom", "--no-owner",
                     "--no-acl", "--file", str(backup)], env=source_env)
        if not backup.is_file() or backup.stat().st_size < 1024:
            raise AssertionError("No credible PostgreSQL backup file")
        run_command(["pg_restore", "--list", str(backup)])
        backup_digest = hashlib.sha256(backup.read_bytes()).hexdigest()
        target_args, target_env = pg_arguments(dst)
        # A fresh empty target database must already exist. Never use --clean or --create.
        asyncio.run(preflight_databases(src, dst))
        run_command(["pg_restore", *target_args, "--exit-on-error", "--no-owner",
                     "--no-acl", str(backup)], env=target_env)
        restored = asyncio.run(snapshot(dst))
        restored_schema = asyncio.run(public_schema_metadata(dst))
        assert_equal(original, restored, "Full public rows and constraints")
        assert_equal(source_schema, restored_schema, "Public indexes and columns")
        assert_equal(original, asyncio.run(snapshot(src)), "Original source preserved")
        from prisma_migration_ledger import verify_committed_ledger
        async def ledger_check():
            conn = await asyncpg.connect(dst)
            try:
                return await verify_committed_ledger(conn, ROOT)
            finally:
                await conn.close()
        assert_equal(ledger, asyncio.run(ledger_check()), "Migration ledger")
        print("MARINA_SHARED_TWO_HOTEL_RESTORE_DATA_PASS "
              + f"tables={len(original['tables'])} "
              + f"indexes={len(source_schema['indexes'])} "
              + f"migrations={len(ledger)} "
              + f"backup_sha256={backup_digest[:16]}... "
              + "source_unchanged=true", flush=True)

    # Only the separate empty target is modified by this process. Invoke a
    # separate read/write acceptance process with the restored DB as DATABASE_URL.
    child_env = dict(os.environ)
    child_env["MARINA_SHARED_ORIGINAL_DATABASE_URL"] = os.environ[SOURCE_ENV]
    child_env[SOURCE_ENV] = dst
    run_command([sys.executable, str(Path(__file__)), "api-check"], env=child_env)
    print("MARINA_SHARED_TWO_HOTEL_RESTORE_E2E_PASS: shared runtime, no external DB")


def restored_api_check() -> None:
    original_source = os.environ.get("MARINA_SHARED_ORIGINAL_DATABASE_URL", "")
    dst = os.environ.get(SOURCE_ENV, "")
    # Validate roles/profile again in this fresh process, without trusting callers
    # who might directly invoke the API checker against another database.
    validate_restore_urls(original_source, dst)
    receipts = receipt_rows()

    from fastapi.testclient import TestClient
    sys.path.insert(0, str(ROOT / "services" / "api"))
    from app.app_entry import app
    with TestClient(app, base_url="http://localhost:18000") as client:
        for hotel in ("HOTEL_A", "HOTEL_B"):
            foreign = "HOTEL_B" if hotel == "HOTEL_A" else "HOTEL_A"
            client.cookies.clear()
            login = client.post("/api/v1/auth/login", json={
                "tenant_code": "tenant_" + hotel[-1].lower(),
                "property_code": hotel,
                "username": "owner",
                "password": PASSWORD,
            })
            assert login.status_code == 200, f"{hotel} restore auth {login.status_code}"
            me = client.get("/api/v1/auth/me", headers={"X-Role": "OWNER",
                "X-Property-Id": receipts[foreign]["room_id"]})
            assert me.status_code == 200 and me.json()["property_code"] == hotel
            own = receipts[hotel]
            other = receipts[foreign]
            grid = client.get("/api/v1/pms/grid", params={
                "start": (date.today() - timedelta(days=2)).isoformat(),
                "end": (date.today() + timedelta(days=6)).isoformat(),
            })
            assert grid.status_code == 200
            assert grid.json()["property"] == hotel
            assert {x["code"] for x in grid.json()["rooms"]} == (
                {"A101"} if hotel == "HOTEL_A" else {"B202"})
            finance = client.get("/api/v1/admin/finance/summary", params={
                "from_date": (date.today() - timedelta(days=7)).isoformat(),
                "to_date": (date.today() + timedelta(days=7)).isoformat(),
            })
            assert finance.status_code == 200, finance.text[:160]
            f = finance.json()
            assert f["scope"]["internal_only"] is True
            assert f["period_payments"]["received_kgs"] == own["manual_amount_kgs"]
            assert any(row["reservation_id"] == own["reservation_id"] for row in f["reservation_ledger"])
            assert not any(row["reservation_id"] == other["reservation_id"] for row in f["reservation_ledger"])
            assert any(row["id"] == own["manual_payment_id"] for row in f["recent_payments"])
            assert not any(row["id"] == other["manual_payment_id"] for row in f["recent_payments"])
            own_history = client.get(
                "/api/v1/ops/tasks/" + own["maintenance_task_id"] + "/history")
            assert own_history.status_code == 200, own_history.text[:120]
            assert own_history.json()["task"]["id"] == own["maintenance_task_id"]
            foreign_history = client.get(
                "/api/v1/ops/tasks/" + other["maintenance_task_id"] + "/history")
            assert foreign_history.status_code == 404, "Restore must preserve 404 hotel boundary"
            logout = client.post("/api/v1/auth/logout")
            assert logout.status_code == 204
            assert client.get("/api/v1/auth/me").status_code == 401

    print("MARINA_SHARED_TWO_HOTEL_RESTORE_RUNTIME_PASS: "
          "two owners, grid, internal finance, task audit and foreign 404")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "api-check":
        restored_api_check()
    elif len(sys.argv) == 1:
        restore()
    else:
        raise SystemExit("Usage: marina_shared_release_restore_ci.py [api-check]")
