#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid

import asyncpg
import httpx

BASE = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
TECH_USERNAME = os.environ["SERVICE_POINT_TECH_USERNAME"]
TECH_PASSWORD = os.environ["SERVICE_POINT_TECH_PASSWORD"]


def login(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30.0)
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return client


def code(response: httpx.Response) -> str | None:
    try:
        detail = response.json().get("detail")
    except Exception:
        return None
    return detail.get("code") if isinstance(detail, dict) else None


def json_object(value):
    if isinstance(value, str):
        value = json.loads(value)
    assert isinstance(value, dict), type(value)
    return value


async def database_truth(task_id: str, point_id: str, raw_tokens: list[str]) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        task = await conn.fetchrow(
            '''SELECT "servicePointId","roomId","reservationId","stayId",type::text AS type,status::text AS status,
                      "createdByType",source,"serviceCode" FROM operational_tasks WHERE id=$1::uuid''',
            task_id,
        )
        assert task is not None
        assert str(task["servicePointId"]) == point_id
        assert task["roomId"] is None
        assert task["reservationId"] is None
        assert task["stayId"] is None
        assert task["type"] == "MAINTENANCE"
        assert task["status"] == "DONE"
        assert task["createdByType"] == "ANONYMOUS"
        assert task["source"] == "SERVICE_POINT_QR"
        # serviceCode belongs to the older structured Guest Services contract.
        # Location QR routing is represented by servicePointId + event/audit request_code.
        assert task["serviceCode"] is None

        point_task_count = await conn.fetchval(
            '''SELECT count(*)::int FROM operational_tasks
               WHERE "servicePointId"=$1::uuid AND source='SERVICE_POINT_QR' ''',
            point_id,
        )
        assert point_task_count == 1

        qrs = await conn.fetch(
            '''SELECT "tokenHash",status::text AS status FROM service_point_qrs
               WHERE "servicePointId"=$1::uuid ORDER BY "issuedAt"''',
            point_id,
        )
        assert len(qrs) == 2
        stored = {row["tokenHash"] for row in qrs}
        for raw in raw_tokens:
            assert raw not in stored
            assert "sha256:" + hashlib.sha256(raw.encode()).hexdigest() in stored
        assert all(row["status"] == "REVOKED" for row in qrs)

        event = await conn.fetchrow(
            '''SELECT "payloadJson","resultResource","resultResourceId" FROM automation_inbound_events
               WHERE "propertyId"=(SELECT "propertyId" FROM service_points WHERE id=$1::uuid)
                 AND "eventType"='SERVICE_POINT_REQUEST'
                 AND "resultResourceId"=$2''',
            point_id,
            task_id,
        )
        assert event is not None
        payload = json_object(event["payloadJson"])
        assert payload["service_point_id"] == point_id
        assert payload["request_code"] == "TECHNICAL"
        assert event["resultResource"] == "OperationalTask"

        audit = await conn.fetchrow(
            '''SELECT "afterJson" FROM audit_logs
               WHERE resource='OperationalTask' AND "resourceId"=$1
                 AND action='CREATE_SERVICE_POINT_REQUEST' ''',
            task_id,
        )
        assert audit is not None
        audit_payload = json_object(audit["afterJson"])
        assert audit_payload["request_code"] == "TECHNICAL"
        assert audit_payload["financial_effect"] == "NONE_AUTOMATIC"
        assert audit_payload["room_state_effect"] == "NONE_AUTOMATIC"

        payments = await conn.fetchval("SELECT count(*)::int FROM payments")
        guest_sessions = await conn.fetchval("SELECT count(*)::int FROM guest_sessions")
        assert payments == 0
        assert guest_sessions == 0
    finally:
        await conn.close()


def main() -> None:
    owner = login(OWNER_USERNAME, OWNER_PASSWORD)
    tech = login(TECH_USERNAME, TECH_PASSWORD)
    suffix = uuid.uuid4().hex[:8].upper()

    create = owner.post(
        "/api/v1/admin/service-points",
        json={
            "code": f"RESTROOM_{suffix}",
            "name": f"Санузел у бассейна {suffix}",
            "category": "RESTROOM",
            "zone_label": "У бассейна",
            "request_options": [
                {"code": "CLEANLINESS", "label": "Нужна уборка", "task_type": "HOUSEKEEPING", "priority": "NORMAL"},
                {"code": "TECHNICAL", "label": "Техническая проблема", "task_type": "MAINTENANCE", "priority": "NORMAL"},
            ],
        },
    )
    create.raise_for_status()
    point_id = create.json()["id"]

    listing = owner.get("/api/v1/admin/service-points")
    listing.raise_for_status()
    point = next(item for item in listing.json()["items"] if item["id"] == point_id)
    assert point["active_qr_id"] is None
    assert {x["code"] for x in point["request_options"]} == {"CLEANLINESS", "TECHNICAL"}

    issue = owner.post(f"/api/v1/admin/service-points/{point_id}/qr/issue")
    issue.raise_for_status()
    issued = issue.json()
    raw_one = issued["token"]
    assert issued["display_once"] is True
    assert raw_one not in issued["qr_svg"]
    assert issued["public_url"].endswith(f"/p/{raw_one}")

    public = httpx.get(f"{BASE}/api/v1/service-points/{raw_one}", timeout=30.0)
    public.raise_for_status()
    public_body = public.json()
    assert set(public_body) == {
        "qr_valid",
        "point",
        "request_options",
        "privacy",
        "financial_effect",
        "room_state_effect",
    }
    assert set(public_body["point"]) == {"code", "name", "category", "zone_label"}
    assert all(set(item) == {"code", "label"} for item in public_body["request_options"])
    assert public_body["privacy"] == "ANONYMOUS_LOCATION_QR_NO_GUEST_DATA"
    assert public_body["financial_effect"] == "NONE_AUTOMATIC"
    assert public_body["room_state_effect"] == "NONE_AUTOMATIC"
    assert public_body["point"]["category"] == "RESTROOM"
    assert {x["code"] for x in public_body["request_options"]} == {"CLEANLINESS", "TECHNICAL"}
    sensitive_keys = {
        "guest",
        "guest_id",
        "reservation",
        "reservation_id",
        "stay",
        "stay_id",
        "phone",
        "email",
        "payment",
        "payment_id",
        "task_type",
        "priority",
    }
    exposed_keys = set(public_body) | set(public_body["point"])
    for item in public_body["request_options"]:
        exposed_keys.update(item)
    assert exposed_keys.isdisjoint(sensitive_keys), exposed_keys & sensitive_keys

    client_request_id = f"service-point-ci-{suffix.lower()}"
    payload = {
        "client_request_id": client_request_id,
        "request_code": "TECHNICAL",
        "description": "Не работает смеситель",
    }
    submitted = httpx.post(
        f"{BASE}/api/v1/service-points/{raw_one}/requests",
        json=payload,
        timeout=30.0,
    )
    submitted.raise_for_status()
    task = submitted.json()
    task_id = task["task_id"]
    assert task["idempotent_replay"] is False
    assert task["type"] == "MAINTENANCE"
    assert task["priority"] == "NORMAL"
    assert task["financial_effect"] == "NONE_AUTOMATIC"
    assert task["room_state_effect"] == "NONE_AUTOMATIC"

    replay = httpx.post(
        f"{BASE}/api/v1/service-points/{raw_one}/requests",
        json=payload,
        timeout=30.0,
    )
    replay.raise_for_status()
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["task_id"] == task_id

    changed = dict(payload)
    changed["description"] = "Другое содержание с тем же ключом"
    mismatch = httpx.post(
        f"{BASE}/api/v1/service-points/{raw_one}/requests",
        json=changed,
        timeout=30.0,
    )
    assert mismatch.status_code == 409, mismatch.text
    assert code(mismatch) == "SERVICE_POINT_IDEMPOTENCY_PAYLOAD_MISMATCH"

    tech_tasks = tech.get("/api/v1/ops/tasks", params={"type": "MAINTENANCE"})
    tech_tasks.raise_for_status()
    visible = [item for item in tech_tasks.json()["items"] if item["id"] == task_id]
    assert len(visible) == 1
    assert "Санузел у бассейна" in visible[0]["title"]
    assert visible[0]["room_id"] is None

    claim = tech.post(f"/api/v1/ops/tasks/{task_id}/claim")
    claim.raise_for_status()
    assert claim.json()["status"] == "IN_PROGRESS"
    done = tech.patch(f"/api/v1/ops/tasks/{task_id}/status", json={"status": "DONE"})
    done.raise_for_status()
    assert done.json()["status"] == "DONE"
    assert "room_state" not in done.json()
    assert "housekeeping_task_id" not in done.json()

    rotate = owner.post(f"/api/v1/admin/service-points/{point_id}/qr/rotate")
    rotate.raise_for_status()
    rotated = rotate.json()
    raw_two = rotated["token"]
    assert raw_two != raw_one

    old = httpx.get(f"{BASE}/api/v1/service-points/{raw_one}", timeout=30.0)
    assert old.status_code == 404
    assert code(old) == "SERVICE_POINT_QR_NOT_FOUND"
    new = httpx.get(f"{BASE}/api/v1/service-points/{raw_two}", timeout=30.0)
    new.raise_for_status()

    revoke = owner.post(f"/api/v1/admin/service-points/{point_id}/qr/revoke")
    revoke.raise_for_status()
    assert revoke.json()["status"] == "REVOKED"
    revoked = httpx.get(f"{BASE}/api/v1/service-points/{raw_two}", timeout=30.0)
    assert revoked.status_code == 404

    nfc = httpx.post(f"{BASE}/api/v1/beach/charge", json={}, timeout=30.0)
    assert nfc.status_code == 404, nfc.text

    asyncio.run(database_truth(task_id, point_id, [raw_one, raw_two]))
    owner.close()
    tech.close()
    print("SERVICE_POINT_QR_E2E_OK")


if __name__ == "__main__":
    main()
