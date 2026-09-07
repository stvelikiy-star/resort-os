#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

import asyncpg
import httpx

from release_contract import EXPECTED_MIGRATIONS

APP_ENV = os.environ.get("APP_ENV", "").strip().lower()
BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "").strip()
DATABASE_URL = os.environ.get("DATABASE_URL", "").split("?")[0].strip()
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "").strip()
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "")
SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY", "")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def require_local_test_boundary() -> None:
    if APP_ENV not in {"ci", "test"}:
        raise RuntimeError("Owner Control V2 E2E requires explicit APP_ENV=ci|test")
    if not all((BASE_URL, DATABASE_URL, OWNER_USERNAME, OWNER_PASSWORD, SERVICE_KEY)):
        raise RuntimeError("Owner Control V2 E2E requires explicit Core URL, DB URL, owner credentials and service key")
    core_host = (urllib.parse.urlparse(BASE_URL).hostname or "").lower()
    db_host = (urllib.parse.urlparse(DATABASE_URL).hostname or "").lower()
    if core_host not in LOCAL_HOSTS:
        raise RuntimeError(f"Owner Control V2 E2E refuses non-local Core host: {core_host or '<missing>'}")
    if db_host not in LOCAL_HOSTS:
        raise RuntimeError(f"Owner Control V2 E2E refuses non-local database host: {db_host or '<missing>'}")


def choose_option(client: httpx.Client, start: date, end: date) -> dict:
    response = client.get(
        "/api/v1/booking/check-availability",
        params={"check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2, "children": 0},
    )
    response.raise_for_status()
    return next(x for x in response.json()["results"] if x["available_count"] > 0 and x["pricing"]["sellable"])


def create_reservation(client: httpx.Client, start: date) -> tuple[dict, date, date]:
    end = start + timedelta(days=2)
    option = choose_option(client, start, end)
    request = client.post(
        "/api/v1/booking/requests",
        json={
            "guest_name": "Owner Pace CI",
            "phone": "+996555778899",
            "email": "owner.pace.ci@example.invalid",
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "adults": 2,
            "children": 0,
            "room_type_code": option["room_type_code"],
            "source": "CI_OWNER_PACE",
        },
    )
    request.raise_for_status()
    request_id = request.json()["id"]
    quote = client.post(f"/api/v1/admin/booking/requests/{request_id}/quote", json={"room_type_code": option["room_type_code"]})
    quote.raise_for_status()
    confirm = client.post(
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        json={
            "amount_kgs": 1000,
            "method": "CI_MANAGER",
            "external_ref": "owner-control-v2-ci",
            "idempotency_key": f"owner-control-v2-{request_id}",
        },
    )
    confirm.raise_for_status()
    return confirm.json(), start, end


async def move_baseline_to_yesterday(today: date) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        count = await conn.fetchval('SELECT count(*) FROM owner_analytics_snapshots WHERE "propertyId"=$1', pid)
        assert count == 1
        await conn.execute(
            'UPDATE owner_analytics_snapshots SET "snapshotDate"=$2 WHERE "propertyId"=$1',
            pid,
            today - timedelta(days=1),
        )
    finally:
        await conn.close()


async def prove_database_state(today: date) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', pid) == 84
        migrations = await conn.fetch("SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL ORDER BY started_at")
        assert [r["migration_name"] for r in migrations] == list(EXPECTED_MIGRATIONS)
        snapshots = await conn.fetch(
            'SELECT "snapshotDate","horizonDays",jsonb_typeof("payloadJson") AS payload_type FROM owner_analytics_snapshots WHERE "propertyId"=$1 ORDER BY "snapshotDate"',
            pid,
        )
        assert len(snapshots) == 2
        assert snapshots[0]["snapshotDate"] == today - timedelta(days=1)
        assert snapshots[1]["snapshotDate"] == today
        assert all(r["horizonDays"] == 180 and r["payload_type"] == "object" for r in snapshots)
    finally:
        await conn.close()


def prove_n8n_contract() -> None:
    workflow = json.loads(Path("automation/n8n/owner-analytics-daily-snapshot.json").read_text())
    assert workflow["active"] is False
    assert workflow["settings"]["timezone"] == "Asia/Bishkek"
    nodes = workflow["nodes"]
    schedule = next(n for n in nodes if n["type"] == "n8n-nodes-base.scheduleTrigger")
    assert schedule["parameters"]["rule"]["interval"][0]["expression"] == "10 3 * * *"
    http = next(n for n in nodes if n["type"] == "n8n-nodes-base.httpRequest")
    assert "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180" in http["parameters"]["url"]
    headers = http["parameters"]["headerParameters"]["parameters"]
    assert any(h["name"] == "X-Resort-Service-Key" and "AUTOMATION_SERVICE_KEY" in h["value"] for h in headers)
    assert not any("postgres" in n["type"].lower() for n in nodes)


def main() -> None:
    require_local_test_boundary()
    prove_n8n_contract()
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    assert client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30").status_code == 401
    login = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    initial = client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30")
    initial.raise_for_status()
    body = initial.json()
    today = date.fromisoformat(body["property"]["local_date"])
    assert body["pickup_readiness"]["status"] == "INSUFFICIENT_HISTORY"

    first = client.post("/api/v1/admin/intelligence/snapshots/capture?horizon_days=180")
    first.raise_for_status()
    assert first.json()["payload"]["summary"]["room_count"] == 84
    asyncio.run(move_baseline_to_yesterday(today))

    reservation, check_in, check_out = create_reservation(client, today + timedelta(days=1))
    assert reservation["reservation_status"] == "GUARANTEED"

    brief = client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30")
    brief.raise_for_status()
    updated = brief.json()
    assert updated["pickup_readiness"]["status"] == "READY"
    assert updated["forward"]["next_30_days"]["booked_room_nights"] >= 2
    daily = {x["date"]: x for x in updated["forward"]["daily"]}
    assert daily[check_in.isoformat()]["arrivals"] >= 1
    assert daily[check_out.isoformat()]["departures"] >= 1

    no_key = client.post("/api/v1/automation/intelligence/snapshots/capture?horizon_days=180")
    assert no_key.status_code == 401
    wrong_key = client.post(
        "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180",
        headers={"X-Resort-Service-Key": "invalid-test-key"},
    )
    assert wrong_key.status_code == 401
    service = client.post(
        "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180",
        headers={"X-Resort-Service-Key": SERVICE_KEY},
    )
    service.raise_for_status()
    assert service.json()["snapshot_date"] == today.isoformat()

    asyncio.run(prove_database_state(today))
    client.close()
    print("OWNER_CONTROL_V2_LOCAL_CI_E2E_OK")


if __name__ == "__main__":
    main()
