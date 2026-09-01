import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path

import asyncpg
import httpx

from release_contract import EXPECTED_MIGRATIONS

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Owner-Strong-Password-2026")
SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY", "owner-control-v2-ci-service-key")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]


def choose_option(client: httpx.Client, start: date, end: date):
    response = client.get(
        "/api/v1/booking/check-availability",
        params={"check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2, "children": 0},
    )
    response.raise_for_status()
    return next(item for item in response.json()["results"] if item["available_count"] > 0 and item["pricing"]["sellable"])


def create_reservation(client: httpx.Client, start: date):
    end = start + timedelta(days=2)
    option = choose_option(client, start, end)
    request = client.post(
        "/api/v1/booking/requests",
        json={
            "guest_name": "Owner Pace CI",
            "phone": "+996555778899",
            "email": "owner.pace.ci@example.com",
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
    quote = client.post(
        f"/api/v1/admin/booking/requests/{request_id}/quote",
        json={"room_type_code": option["room_type_code"]},
    )
    quote.raise_for_status()
    confirm = client.post(
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        json={
            "amount_kgs": 1000,
            "method": "CI_MANAGER",
            "external_ref": "owner-control-v2-ci-001",
            "idempotency_key": "owner-control-v2-payment-001",
        },
    )
    confirm.raise_for_status()
    return confirm.json(), start, end


async def move_baseline_to_yesterday(today: date):
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


async def prove_database_state(today: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        room_count = await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', pid)
        assert room_count == 84
        migrations = await conn.fetch("SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL ORDER BY started_at")
        names = [row["migration_name"] for row in migrations]
        assert names == list(EXPECTED_MIGRATIONS)
        snapshots = await conn.fetch(
            'SELECT "snapshotDate","horizonDays",jsonb_typeof("payloadJson") AS payload_type FROM owner_analytics_snapshots WHERE "propertyId"=$1 ORDER BY "snapshotDate"',
            pid,
        )
        assert len(snapshots) == 2
        assert snapshots[0]["snapshotDate"] == today - timedelta(days=1)
        assert snapshots[1]["snapshotDate"] == today
        assert all(row["horizonDays"] == 180 and row["payload_type"] == "object" for row in snapshots)
        audits = await conn.fetchval(
            "SELECT count(*) FROM audit_logs WHERE \"propertyId\"=$1 AND action='CAPTURE_OWNER_ANALYTICS_SNAPSHOT'",
            pid,
        )
        assert audits >= 3
    finally:
        await conn.close()


def prove_n8n_contract():
    path = Path("automation/n8n/owner-analytics-daily-snapshot.json")
    workflow = json.loads(path.read_text())
    assert workflow["active"] is False
    assert workflow["settings"]["timezone"] == "Asia/Bishkek"
    nodes = workflow["nodes"]
    schedule = next(node for node in nodes if node["type"] == "n8n-nodes-base.scheduleTrigger")
    expression = schedule["parameters"]["rule"]["interval"][0]["expression"]
    assert expression == "10 3 * * *"
    http = next(node for node in nodes if node["type"] == "n8n-nodes-base.httpRequest")
    assert "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180" in http["parameters"]["url"]
    headers = http["parameters"]["headerParameters"]["parameters"]
    assert any(item["name"] == "X-Resort-Service-Key" and "AUTOMATION_SERVICE_KEY" in item["value"] for item in headers)
    assert not any("postgres" in node["type"].lower() for node in nodes)


def main():
    prove_n8n_contract()
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    unauth = client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30")
    assert unauth.status_code == 401

    login = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    initial_brief = client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30")
    initial_brief.raise_for_status()
    initial = initial_brief.json()
    today = date.fromisoformat(initial["property"]["local_date"])
    assert initial["pickup_readiness"]["status"] == "INSUFFICIENT_HISTORY"
    assert len(initial["forward"]["daily"]) == 30
    assert initial["forward"]["next_30_days"]["available_room_nights"] > 0

    pickup_before = client.get(
        "/api/v1/admin/intelligence/pickup",
        params={"from_date": today.isoformat(), "to_date": (today + timedelta(days=29)).isoformat()},
    )
    pickup_before.raise_for_status()
    assert pickup_before.json()["status"] == "INSUFFICIENT_HISTORY"

    first_capture = client.post("/api/v1/admin/intelligence/snapshots/capture?horizon_days=180")
    first_capture.raise_for_status()
    captured = first_capture.json()
    assert captured["snapshot_date"] == today.isoformat()
    assert captured["horizon_days"] == 180
    assert captured["payload"]["summary"]["room_count"] == 84
    assert len(captured["payload"]["days"]) == 180

    asyncio.run(move_baseline_to_yesterday(today))

    reservation, check_in, check_out = create_reservation(client, today + timedelta(days=1))
    assert reservation["reservation_status"] == "GUARANTEED"

    brief = client.get("/api/v1/admin/intelligence/owner-brief?horizon_days=30")
    brief.raise_for_status()
    body = brief.json()
    assert body["pickup_readiness"]["status"] == "READY"
    assert body["forward"]["next_30_days"]["booked_room_nights"] >= 2
    assert body["forward"]["next_30_days"]["arrivals"] >= 1
    assert body["forward"]["next_30_days"]["departures"] >= 1
    debt_ids = {item["reservation_id"] for item in body["details"]["debt_arrivals_72h"]}
    assert reservation["reservation_id"] in debt_ids
    debt_action = next(item for item in body["actions"] if item["code"] == "DEBT_72H")
    assert debt_action["count"] >= 1
    daily = {item["date"]: item for item in body["forward"]["daily"]}
    assert daily[check_in.isoformat()]["arrivals"] >= 1
    assert daily[check_out.isoformat()]["departures"] >= 1

    pickup = client.get(
        "/api/v1/admin/intelligence/pickup",
        params={"from_date": today.isoformat(), "to_date": (today + timedelta(days=29)).isoformat()},
    )
    pickup.raise_for_status()
    pace = pickup.json()
    assert pace["status"] == "READY"
    assert pace["baseline"]["snapshot_date"] == (today - timedelta(days=1)).isoformat()
    assert pace["summary"]["room_night_pickup"] >= 2
    assert pace["summary"]["booked_value_pickup_kgs"] > 0

    bad_range = client.get(
        "/api/v1/admin/intelligence/pickup",
        params={"from_date": (today - timedelta(days=1)).isoformat(), "to_date": today.isoformat()},
    )
    assert bad_range.status_code == 422

    no_service_key = client.post("/api/v1/automation/intelligence/snapshots/capture?horizon_days=180")
    assert no_service_key.status_code == 401
    wrong_service_key = client.post(
        "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180",
        headers={"X-Resort-Service-Key": "wrong-key"},
    )
    assert wrong_service_key.status_code == 401
    service_capture = client.post(
        "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180",
        headers={"X-Resort-Service-Key": SERVICE_KEY},
    )
    service_capture.raise_for_status()
    assert service_capture.json()["snapshot_date"] == today.isoformat()

    second_same_day = client.post(
        "/api/v1/automation/intelligence/snapshots/capture?horizon_days=180",
        headers={"X-Resort-Service-Key": SERVICE_KEY},
    )
    second_same_day.raise_for_status()

    snapshots = client.get("/api/v1/admin/intelligence/snapshots?limit=10")
    snapshots.raise_for_status()
    assert len(snapshots.json()["items"]) == 2

    asyncio.run(prove_database_state(today))
    client.close()
    print("OWNER_CONTROL_V2_E2E_OK")


if __name__ == "__main__":
    main()
