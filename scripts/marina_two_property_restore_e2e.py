"""Synthetic two-property API isolation before and after PostgreSQL restoration.

Only disposable local databases are accepted. Two property-pinned API processes
share a database. This proves that deployment mode, not single-runtime SaaS.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import unquote, urlsplit
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

from release_contract import clean_postgres_url, EXPECTED_MIGRATIONS

ROOT = Path(__file__).resolve().parents[1]
CODES = ("MARINA_ISOLATION_A", "MARINA_ISOLATION_B")
USERNAME = "isolation-owner"
PASSWORDS = ("Synthetic-Owner-A-2026!", "Synthetic-Owner-B-2026!")
PORTS = (18081, 18082)


def validate_ci_dsn(value: str) -> str:
    cleaned = clean_postgres_url(value)
    parsed = urlsplit(cleaned)
    if parsed.scheme not in {"postgres", "postgresql"} or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Only local disposable PostgreSQL is accepted")
    name = unquote(parsed.path.lstrip("/"))
    if parsed.query or parsed.fragment:
        raise RuntimeError("Disposable database URLs cannot override connection parameters")
    if not name.startswith("marina_isolation_") or not name.replace("_", "").isalnum():
        raise RuntimeError("Disposable database name must start with marina_isolation_")
    return cleaned


def runtime_env(dsn: str, index: int) -> dict[str, str]:
    return {
        **os.environ, "DATABASE_URL": dsn, "PROPERTY_CODE": CODES[index],
        "APP_ENV": "staging", "MARINA_TENANT_CONTEXT_ENABLED": "true",
        "MARINA_PROPERTY_NAME": f"Synthetic isolation hotel {index + 1}",
        "RATE_PLAN_CODE": "MARINA_DIRECT", "BOOTSTRAP_OWNER_USERNAME": USERNAME,
        "BOOTSTRAP_OWNER_PASSWORD": PASSWORDS[index], "COOKIE_SECURE": "false",
        "AUTH_TRUST_PROXY_HEADERS": "false", "ENABLE_PAYMENT_OPERATIONS": "false",
        "ENABLE_MKASSA": "false", "ENABLE_SERVICE_POINT_QR": "false",
        "OPENAI_API_KEY": "", "MARINA_AI_API_KEY": "",
    }


async def ensure_empty_source(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        if await conn.fetchval("SELECT count(*) FROM properties") or await conn.fetchval("SELECT count(*) FROM tenants"):
            raise RuntimeError("Source contains tenants or properties; refusing to add synthetic fixtures")
        migrations = await conn.fetch("SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL AND rolled_back_at IS NULL")
        if {row["migration_name"] for row in migrations} != set(EXPECTED_MIGRATIONS):
            raise RuntimeError("Source migration ledger does not match committed candidate")
    finally:
        await conn.close()


async def ensure_empty_target(dsn: str) -> None:
    conn = await asyncpg.connect(dsn)
    try:
        if await conn.fetchval("SELECT count(*) FROM pg_tables WHERE schemaname='public'"):
            raise RuntimeError("Restore target is not empty; refusing restoration")
    finally:
        await conn.close()


async def seed_records(dsn: str) -> list[dict]:
    conn = await asyncpg.connect(dsn)
    fixtures = []
    start, end = date.today(), date.today() + timedelta(days=1)
    try:
        async with conn.transaction():
            for code in CODES:
                pid = await conn.fetchval("SELECT id FROM properties WHERE code=$1", code)
                guest, reservation, request = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
                await conn.execute('INSERT INTO guests (id,"propertyId","firstName",phone,"createdAt","updatedAt") VALUES ($1,$2,$3,$4,now(),now())', guest, pid, code, "+996000000000")
                await conn.execute('INSERT INTO reservation_requests (id,"propertyId","guestName",phone,"checkIn","checkOut",adults,children,"createdAt","updatedAt") VALUES ($1,$2,$3,$4,$5,$6,1,0,now(),now())', request, pid, code, "+996000000000", start, end)
                await conn.execute('INSERT INTO reservations (id,"propertyId","bookingNumber","primaryGuestId","checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt") VALUES ($1,$2,$3,$4,$5,$6,1,0,3000,now(),now())', reservation, pid, code + "-SYNTHETIC", guest, start, end)
                fixtures.append({"reservation": str(reservation), "request": str(request)})
    finally:
        await conn.close()
    return fixtures


async def snapshot(dsn: str) -> dict:
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            data = {}
            for row in tables:
                name = row["tablename"]
                quoted = '"' + name.replace('"', '""') + '"'
                rows = await conn.fetch(f'SELECT to_jsonb(t)::text AS row FROM public.{quoted} t ORDER BY to_jsonb(t)::text')
                payload = json.dumps([item["row"] for item in rows], ensure_ascii=False).encode()
                data[name] = {"count": len(rows), "sha256": hashlib.sha256(payload).hexdigest()}
            constraints = await conn.fetch("SELECT c.conname,pg_get_constraintdef(c.oid) AS definition FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' ORDER BY c.conname,definition")
            return {"tables": data, "constraints": [dict(row) for row in constraints]}
    finally:
        await conn.close()


def pg_arguments(dsn: str) -> tuple[list[str], dict[str, str]]:
    parsed = urlsplit(dsn)
    args = ["--host", parsed.hostname, "--port", str(parsed.port or 5432), "--username", unquote(parsed.username or ""), "--dbname", unquote(parsed.path.lstrip("/"))]
    return args, {**os.environ, "PGPASSWORD": unquote(parsed.password or "")}


def run_api_gate(dsn: str, fixtures: list[dict], directory: Path) -> None:
    processes, logs = [], []
    try:
        for index, port in enumerate(PORTS):
            log = (directory / f"api-{index}.log").open("w")
            logs.append(log)
            processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "app.app_entry:app", "--app-dir", "services/api", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=runtime_env(dsn, index), stdout=log, stderr=log))
        deadline = time.monotonic() + 60
        for index, port in enumerate(PORTS):
            while True:
                if processes[index].poll() is not None:
                    raise RuntimeError(f"Synthetic API {index} exited during startup")
                try:
                    response = httpx.get(f"http://127.0.0.1:{port}/health/ready", timeout=1)
                    if response.status_code == 200 and response.json().get("property") == CODES[index]:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Synthetic APIs did not become ready")
                time.sleep(0.5)
        env = {
            **os.environ, "MARINA_STAGING_BASE_URL": f"http://127.0.0.1:{PORTS[0]}",
            "MARINA_STAGING_TENANT_B_BASE_URL": f"http://127.0.0.1:{PORTS[1]}",
            "MARINA_STAGING_ISOLATION_CONFIRM": "I_UNDERSTAND_STAGING_ONLY",
            "MARINA_STAGING_DATABASE_URL": dsn,
            "MARINA_STAGING_EXPECTED_PROPERTY_CODES": ",".join(CODES),
            "MARINA_STAGING_EXPECTED_TENANTS": "2", "MARINA_STAGING_EXPECTED_PROPERTIES": "2",
        }
        for index, letter in enumerate(("A", "B")):
            for suffix, value in {"USERNAME": USERNAME, "PASSWORD": PASSWORDS[index], "PROPERTY_CODE": CODES[index], "RESERVATION_ID": fixtures[index]["reservation"], "REQUEST_ID": fixtures[index]["request"]}.items():
                env[f"MARINA_STAGING_TENANT_{letter}_{suffix}"] = value
        subprocess.run([sys.executable, "scripts/verify_marina_multitenant_staging.py"], cwd=ROOT, env=env, check=True)
        subprocess.run([sys.executable, "scripts/verify_marina_multitenant_isolation.py"], cwd=ROOT, env=env, check=True)
        # Same username, different passwords: credentials and session cookies
        # must not transfer between the two property-pinned API processes.
        for index, port in enumerate(PORTS):
            foreign = 1 - index
            with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
                own = client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORDS[index]})
                assert own.status_code == 200, "Own account login failed"
                cookie = client.cookies.get("resort_session")
                assert cookie, "Own login did not create session"
                response = httpx.get(f"http://127.0.0.1:{PORTS[foreign]}/api/v1/auth/me", cookies={"resort_session": cookie})
                assert response.status_code == 401, "Foreign session crossed property boundary"
                wrong = httpx.post(f"http://127.0.0.1:{PORTS[foreign]}/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORDS[index]})
                assert wrong.status_code == 401, "Foreign password authenticated wrong property"
        print("MARINA_CROSS_PROPERTY_SESSION_PASSWORD_PASS")
    except Exception:
        for index, log in enumerate(logs):
            log.flush()
            print(f"Synthetic API {index} diagnostic log:")
            print((directory / f"api-{index}.log").read_text()[-8000:])
        raise
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()


def main() -> None:
    if os.environ.get("MARINA_CI_ISOLATION_CONFIRM") != "CREATE_SYNTHETIC_LOCAL_ONLY":
        raise RuntimeError("Synthetic local-only confirmation is required")
    source = validate_ci_dsn(os.environ["DATABASE_URL"])
    target = validate_ci_dsn(os.environ["RESTORE_DATABASE_URL"])
    if urlsplit(source).path == urlsplit(target).path:
        raise RuntimeError("Restore target must be a different disposable database")
    asyncio.run(ensure_empty_target(target))
    asyncio.run(ensure_empty_source(source))
    for index in range(2):
        for script in ("bootstrap_marina_test.py", "bootstrap_owner.py"):
            subprocess.run([sys.executable, "scripts/" + script], cwd=ROOT, env=runtime_env(source, index), check=True)
    fixtures = asyncio.run(seed_records(source))
    with tempfile.TemporaryDirectory(prefix="marina-isolation-") as temp:
        directory = Path(temp)
        run_api_gate(source, fixtures, directory)
        before = asyncio.run(snapshot(source))
        args, env = pg_arguments(source)
        dump = directory / "synthetic.dump"
        subprocess.run(["pg_dump", *args, "--format=custom", "--no-owner", "--no-acl", "--file", str(dump)], env=env, check=True)
        args, env = pg_arguments(target)
        # Target is provisioned empty by the workflow. No database or data is dropped.
        asyncio.run(ensure_empty_target(target))
        subprocess.run(["pg_restore", *args, "--exit-on-error", "--no-owner", "--no-acl", str(dump)], env=env, check=True)
        after = asyncio.run(snapshot(target))
        assert before == after, "Restored database rows or constraints differ from source"
        print(f"MARINA_TWO_PROPERTY_RESTORE_PASS tables={len(before['tables'])}; all public rows and constraints match")
        run_api_gate(target, fixtures, directory)
    print("MARINA_TWO_PROPERTY_RESTORE_E2E_PASS; property-pinned local runtimes only; external staging and production unverified")


if __name__ == "__main__":
    main()
