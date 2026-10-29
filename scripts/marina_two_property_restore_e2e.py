"""Synthetic two-property API isolation before and after PostgreSQL restoration.

Only disposable local databases are accepted. Two property-pinned API processes
share a database. This proves that deployment mode, not single-runtime SaaS.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
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
        committed = {
            path.parent.name
            for path in (ROOT / "packages/database/prisma/migrations").glob("*/migration.sql")
        }
        # Preserve the pinned historical release baseline, while accepting new
        # reviewable migrations included in this exact checkout.
        if not set(EXPECTED_MIGRATIONS).issubset(committed):
            raise RuntimeError("Pinned baseline migrations are missing from repository")
        if {row["migration_name"] for row in migrations} != committed:
            raise RuntimeError("Source migration ledger does not match committed checkout")
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


def _strip_outer_parentheses(expression: str) -> str:
    expression = expression.strip()
    while expression.startswith("(") and expression.endswith(")"):
        depth = 0
        quote = None
        closes_at_end = True
        index = 0
        while index < len(expression):
            char = expression[index]
            if quote:
                if char == quote:
                    if index + 1 < len(expression) and expression[index + 1] == quote:
                        index += 2
                        continue
                    quote = None
            elif char in {"'", '"'}:
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    closes_at_end = False
                    break
            index += 1
        if not closes_at_end or depth != 0:
            break
        expression = expression[1:-1].strip()
    return expression


def _split_top_level_boolean(expression: str, operator: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote = None
    start = 0
    index = 0
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                if index + 1 < len(expression) and expression[index + 1] == quote:
                    index += 2
                    continue
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and expression[index:index + len(operator)].upper() == operator:
            before = expression[index - 1] if index else " "
            after_index = index + len(operator)
            after = expression[after_index] if after_index < len(expression) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                parts.append(expression[start:index].strip())
                start = after_index
                index = after_index
                continue
        index += 1
    if parts:
        parts.append(expression[start:].strip())
    return parts


def _canonical_constraint_expression(definition: str) -> str:
    expression = definition.strip()
    if expression[:5].upper() == "CHECK":
        expression = expression[5:].strip()
    expression = _strip_outer_parentheses(expression)
    for operator in ("OR", "AND"):
        parts = _split_top_level_boolean(expression, operator)
        if len(parts) > 1:
            children = []
            for part in parts:
                child = json.loads(_canonical_constraint_expression(part))
                if isinstance(child, list) and child[0] == operator:
                    children.extend(child[1])
                else:
                    children.append(child)
            return json.dumps([operator, sorted(children, key=lambda item: json.dumps(item, ensure_ascii=False))],
                              ensure_ascii=False, separators=(",", ":"))
    return json.dumps(["ATOM", re.sub(r"\\s+", " ", expression).strip()],
                      ensure_ascii=False, separators=(",", ":"))


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
            normalized_constraints = [
                {"conname": row["conname"], "definition": _canonical_constraint_expression(row["definition"])}
                for row in constraints
            ]
            return {"tables": data, "constraints": normalized_constraints}
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
        # Real HTTP checks against property-pinned APIs and disposable PostgreSQL.
        # Two concurrent requests for one room must produce exactly one HOLD.
        from concurrent.futures import ThreadPoolExecutor
        async def hold_rooms():
            conn = await asyncpg.connect(dsn)
            try:
                return [
                    str(await conn.fetchval(
                        'SELECT r.id FROM rooms r JOIN properties p ON p.id=r."propertyId" '
                        'WHERE p.code=$1 AND r."operationalState" <> \'TECH_BLOCK\' '
                        'ORDER BY r.code LIMIT 1', code
                    )) for code in CODES
                ]
            finally:
                await conn.close()
        room_ids = asyncio.run(hold_rooms())
        assert all(room_id != "None" for room_id in room_ids), "Synthetic HOLD room missing"
        check_in = (date.today() + timedelta(days=120)).isoformat()
        check_out = (date.today() + timedelta(days=122)).isoformat()
        payload = {"room_id": room_ids[0], "check_in": check_in, "check_out": check_out,
                   "guest_name": "Synthetic Hold Guest", "guest_phone": "+996700111222"}
        with httpx.Client(base_url=f"http://127.0.0.1:{PORTS[0]}") as client:
            login = client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORDS[0]})
            assert login.status_code == 200, f"HOLD owner login failed: {login.status_code}"
            token = client.cookies.get("resort_session")
            assert token, "HOLD owner session cookie missing"
            with ThreadPoolExecutor(max_workers=2) as executor:
                calls = [executor.submit(httpx.post, f"http://127.0.0.1:{PORTS[0]}/api/v1/admin/pms/holds",
                        json=payload, cookies={"resort_session": token}, timeout=15) for _ in range(2)]
                responses = [future.result() for future in calls]
            codes = sorted(response.status_code for response in responses)
            assert codes == [201, 409], f"Concurrent HOLD requests failed safety gate: {codes} {[r.text[:500] for r in responses]}"
            held = next(response.json() for response in responses if response.status_code == 201)
            # Authenticate independently as the owner of the *other* hotel:
            # an invalid foreign cookie alone would not prove tenant isolation.
            with httpx.Client(base_url=f"http://127.0.0.1:{PORTS[1]}") as other_hotel:
                second_login = other_hotel.post("/api/v1/auth/login",
                    json={"username": USERNAME, "password": PASSWORDS[1]})
                assert second_login.status_code == 200, "Second hotel owner login failed"
                foreign = other_hotel.get(f"/api/v1/admin/pms/holds/{held['id']}")
                assert foreign.status_code == 404, (
                    f"Authenticated owner of hotel B could inspect hotel A HOLD: {foreign.status_code}"
                )
                forbidden_release = other_hotel.delete(f"/api/v1/admin/pms/holds/{held['id']}")
                assert forbidden_release.status_code == 404, (
                    f"Authenticated owner of hotel B could release hotel A HOLD: {forbidden_release.status_code}"
                )
            detail = client.get(f"/api/v1/admin/pms/holds/{held['id']}")
            assert detail.status_code == 200, f"HOLD owner cannot read active HOLD: {detail.status_code}"
            released = client.delete(f"/api/v1/admin/pms/holds/{held['id']}")
            assert released.status_code == 200, f"HOLD release failed: {released.status_code}"
            renewed = client.post("/api/v1/admin/pms/holds", json=payload)
            assert renewed.status_code == 201, f"Released HOLD still blocks inventory: {renewed.status_code}"
            renewed_id = renewed.json()["id"]
            # Convert a real HOLD to a confirmed reservation through the same
            # preview/commit API used by the owner chessboard.
            preview_request = {
                **payload, "hold_id": renewed_id, "manager_total_kgs": 9000,
                "guest_phone": payload["guest_phone"],
            }
            preview = client.post("/api/v1/admin/pms/reservations/new/preview", json=preview_request)
            assert preview.status_code == 200, f"HOLD booking preview failed: {preview.status_code} {preview.text[:500]}"
            priced = preview.json()
            assert priced["can_commit"], f"HOLD reservation preview unavailable: {priced}"
            commit_request = {
                **preview_request, "guest_name": payload["guest_name"],
                "phone": payload["guest_phone"],
                "expected_total_kgs": priced["pricing"]["total_kgs"],
                "expected_pricing_source": priced["pricing"]["source"],
            }
            committed = client.post("/api/v1/admin/pms/reservations/new/commit", json=commit_request)
            assert committed.status_code == 201, f"HOLD conversion failed: {committed.status_code} {committed.text[:500]}"
            repeated = client.post("/api/v1/admin/pms/reservations/new/commit", json=commit_request)
            assert repeated.status_code == 409, f"Confirmed HOLD converted twice: {repeated.status_code}"
            confirmed_release = client.delete(f"/api/v1/admin/pms/holds/{renewed_id}")
            assert confirmed_release.status_code == 409, "Confirmed HOLD was released"
        print("MARINA_HOLD_CONCURRENT_API_TENANT_RELEASE_CONVERSION_PASS")

        if os.environ.get("MARINA_CI_CHANNEL_IMPORT") == "true":
            subprocess.run([sys.executable, "scripts/verify_channel_reservations.py"], cwd=ROOT, env=env, check=True)
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
        if before != after:
            table_names = sorted(set(before["tables"]) | set(after["tables"]))
            table_diffs = {
                name: {"source": before["tables"].get(name), "restored": after["tables"].get(name)}
                for name in table_names
                if before["tables"].get(name) != after["tables"].get(name)
            }
            source_constraints = {(item["conname"], item["definition"]) for item in before["constraints"]}
            restored_constraints = {(item["conname"], item["definition"]) for item in after["constraints"]}
            constraint_diffs = {
                "missing_after_restore": sorted(source_constraints - restored_constraints),
                "unexpected_after_restore": sorted(restored_constraints - source_constraints),
            }
            print("MARINA_RESTORE_SNAPSHOT_DIFF=" + json.dumps(
                {"tables": table_diffs, "constraints": constraint_diffs},
                ensure_ascii=False, sort_keys=True,
            ))
            raise AssertionError(
                "Restored database snapshot differs: "
                f"{len(table_diffs)} table(s), "
                f"{len(constraint_diffs['missing_after_restore'])} missing and "
                f"{len(constraint_diffs['unexpected_after_restore'])} unexpected constraint(s)"
            )
        print(f"MARINA_TWO_PROPERTY_RESTORE_PASS tables={len(before['tables'])}; all public rows and constraints match")
        run_api_gate(target, fixtures, directory)
    print("MARINA_TWO_PROPERTY_RESTORE_E2E_PASS; property-pinned local runtimes only; external staging and production unverified")


if __name__ == "__main__":
    main()
