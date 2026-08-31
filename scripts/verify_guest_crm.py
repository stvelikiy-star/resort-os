#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "guest-crm-ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Guest-CRM-CI-Owner-Password-2026")


async def local_today() -> date:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
    finally:
        await conn.close()


async def prepare_room(room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


async def reservation_version(reservation_id: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''SELECT to_char("updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') FROM reservations WHERE id=$1''',
            uuid.UUID(reservation_id),
        )
    finally:
        await conn.close()


async def reservation_guest(reservation_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('SELECT "primaryGuestId" FROM reservations WHERE id=$1', uuid.UUID(reservation_id))
        assert row and row["primaryGuestId"]
        return str(row["primaryGuestId"])
    finally:
        await conn.close()


async def guest_identity_count(phone: str, email: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''
            SELECT count(*)::int
            FROM guests g JOIN properties p ON p.id=g."propertyId"
            WHERE p.code='THREE_CROWNS'
              AND regexp_replace(COALESCE(g.phone,''),'\\D','','g')=regexp_replace($1,'\\D','','g')
              AND lower(trim(COALESCE(g.email,'')))=lower(trim($2))
            ''',
            phone,
            email,
        )
    finally:
        await conn.close()


async def choose_target(current_room_id: str, start: date, end: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        room_type_id = await conn.fetchval('SELECT "roomTypeId" FROM rooms WHERE id=$1', uuid.UUID(current_room_id))
        target = await conn.fetchrow(
            '''
            SELECT r.id,r.code
            FROM rooms r
            WHERE r."roomTypeId"=$1 AND r.id<>$2
              AND NOT EXISTS (
                SELECT 1 FROM inventory_blocks ib
                WHERE ib."roomId"=r.id AND ib.active=true
                  AND daterange(ib."startDate",ib."endDate",'[)') && daterange($3::date,$4::date,'[)')
              )
              AND NOT EXISTS (
                SELECT 1 FROM room_assignments ra WHERE ra."roomId"=r.id AND ra."endedAt" IS NULL
              )
            ORDER BY r.code LIMIT 1
            ''',
            room_type_id,
            uuid.UUID(current_room_id),
            start,
            end,
        )
        assert target, "No free same-type target room for Guest CRM relocation E2E"
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', target["id"])
        return str(target["id"]), target["code"]
    finally:
        await conn.close()


async def payment_count() -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval('SELECT count(*)::int FROM payments')
    finally:
        await conn.close()


async def audit_count(action: str, guest_id: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''SELECT count(*)::int FROM audit_logs WHERE action=$1 AND source='GUEST_CRM' AND result='SUCCESS'
               AND ("afterJson"->>'guest_id'=$2 OR "beforeJson"->>'guest_id'=$2)''',
            action,
            guest_id,
        )
    finally:
        await conn.close()


def choose_sellable_room(owner: httpx.Client, start: date, end: date, *, exclude: set[str] | None = None):
    excluded = exclude or set()
    grid = owner.get('/api/v1/pms/grid', params={"start": start.isoformat(), "end": end.isoformat()})
    grid.raise_for_status()
    for room in grid.json()["rooms"]:
        if room["id"] in excluded:
            continue
        preview = owner.post('/api/v1/admin/pms/reservations/new/preview', json={
            "room_id": room["id"], "check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 1, "children": 0,
        })
        if preview.status_code == 200 and preview.json().get("can_commit"):
            return room, preview.json()
    raise AssertionError("No sellable room for Guest CRM E2E")


def create_reservation(
    owner: httpx.Client,
    *,
    room: dict,
    preview: dict,
    check_in: date,
    check_out: date,
    guest_name: str,
    phone: str,
    email: str,
    notes: str,
):
    asyncio.run(prepare_room(room["id"]))
    response = owner.post('/api/v1/admin/pms/reservations/new/commit', json={
        "room_id": room["id"],
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "adults": 1,
        "children": 0,
        "guest_name": guest_name,
        "phone": phone,
        "email": email,
        "expected_total_kgs": preview["pricing"]["total_kgs"],
        "expected_pricing_source": preview["pricing"]["source"],
        "notes": notes,
    })
    response.raise_for_status()
    body = response.json()
    assert body["payment_created"] is False
    return body["reservation_id"]


def main():
    today = asyncio.run(local_today())
    first_start = today - timedelta(days=1)
    first_end = today + timedelta(days=2)
    second_start = today
    second_end = today + timedelta(days=2)

    owner = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-crm-ci"})
    login = owner.post('/api/v1/auth/login', json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    chosen, preview_body = choose_sellable_room(owner, first_start, first_end)
    suffix = uuid.uuid4().hex[:8]
    phone = "+996556" + suffix[:6]
    email = f"guest-crm-{suffix}@example.com"

    reservation_id = create_reservation(
        owner,
        room=chosen,
        preview=preview_body,
        check_in=first_start,
        check_out=first_end,
        guest_name="Guest CRM CI",
        phone=phone,
        email=email,
        notes="Guest CRM factual history E2E",
    )
    guest_id = asyncio.run(reservation_guest(reservation_id))
    assert asyncio.run(guest_identity_count(phone, email)) == 1

    qr = owner.post(f'/api/v1/admin/guest-os/room-qrs/{chosen["id"]}/issue')
    qr.raise_for_status()
    qr_token = qr.json()["token"]

    check_in = owner.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-in')
    check_in.raise_for_status()
    first_stay_id = check_in.json()["stay_id"]
    pin = check_in.json()["guest_access_pin"]
    verify = owner.post(f'/api/v1/guest-os/rooms/{qr_token}/verify', json={"pin": pin})
    verify.raise_for_status()

    payments_before = asyncio.run(payment_count())
    request = owner.post(f'/api/v1/guest-os/rooms/{qr_token}/requests', json={
        "request_code": "TOWELS", "description": "CRM history towels request",
    })
    request.raise_for_status()
    task_id = request.json()["id"]
    claim = owner.post(f'/api/v1/ops/guest-requests/{task_id}/claim')
    claim.raise_for_status()
    complete = owner.post(f'/api/v1/ops/guest-requests/{task_id}/complete')
    complete.raise_for_status()
    assert complete.json()["status"] == "DONE"

    target_room_id, target_room_code = asyncio.run(choose_target(chosen["id"], today, first_end))
    version = asyncio.run(reservation_version(reservation_id))
    segments = [
        {"room_id": chosen["id"], "start": first_start.isoformat(), "end": today.isoformat()},
        {"room_id": target_room_id, "start": today.isoformat(), "end": first_end.isoformat()},
    ]
    move_preview = owner.post(f'/api/v1/admin/pms/reservations/{reservation_id}/schedule/preview', json={"segments": segments})
    move_preview.raise_for_status()
    assert move_preview.json()["immediate_relocation"] is not None
    move_commit = owner.post(
        f'/api/v1/admin/pms/reservations/{reservation_id}/schedule/commit',
        json={"segments": segments, "expected_version": version},
    )
    move_commit.raise_for_status()
    assert move_commit.json()["relocation_room_assignment_id"]

    detail = owner.get(f'/api/v1/admin/guest-crm/{guest_id}')
    detail.raise_for_status()
    crm = detail.json()
    assert crm["guest"]["id"] == guest_id
    assert len(crm["stays"]) == 1
    stay = crm["stays"][0]
    assert stay["id"] == first_stay_id and stay["status"] == "ACTIVE"
    assert stay["actual_check_in_at"] is not None
    assert len(stay["assignments"]) == 2, stay["assignments"]
    assert stay["assignments"][0]["room_code"] == chosen["code"]
    assert stay["assignments"][0]["ended_at"] is not None
    assert stay["assignments"][1]["room_code"] == target_room_code
    assert stay["assignments"][1]["ended_at"] is None
    assert any(item["id"] == task_id and item["status"] == "DONE" and item["request_code"] == "TOWELS" for item in stay["requests"])
    event_types = {event["event_type"] for event in crm["events"]}
    assert {"CHECK_IN", "GUEST_REQUEST_CREATED", "GUEST_REQUEST_COMPLETED", "ROOM_RELOCATION"}.issubset(event_types), event_types
    relocation = next(event for event in crm["events"] if event["event_type"] == "ROOM_RELOCATION")
    assert relocation["payload"]["from_room_id"] == chosen["id"]
    assert relocation["payload"]["to_room_id"] == target_room_id
    raw = str(crm).lower()
    assert "guestaccesspinhash" not in raw and "tokenhash" not in raw and "guest_session" not in raw

    invalid = owner.put(f'/api/v1/admin/guest-crm/{guest_id}/preferences/PASSPORT_NOTE', json={"value": "never"})
    assert invalid.status_code == 422 and invalid.json()["detail"]["code"] == "PREFERENCE_KEY_NOT_ALLOWED"

    pref = owner.put(f'/api/v1/admin/guest-crm/{guest_id}/preferences/HOUSEKEEPING_TIME', json={"value": "После 15:00"})
    pref.raise_for_status()
    assert pref.json()["active"] is True
    update = owner.put(f'/api/v1/admin/guest-crm/{guest_id}/preferences/HOUSEKEEPING_TIME', json={"value": "После 16:00"})
    update.raise_for_status()
    assert update.json()["value"] == "После 16:00"

    checkout = owner.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-out')
    checkout.raise_for_status()
    assert checkout.json()["status"] == "CHECKED_OUT"
    assert checkout.json()["stay_id"] == first_stay_id

    second_room, second_preview = choose_sellable_room(
        owner,
        second_start,
        second_end,
        exclude={chosen["id"], target_room_id},
    )
    second_reservation_id = create_reservation(
        owner,
        room=second_room,
        preview=second_preview,
        check_in=second_start,
        check_out=second_end,
        guest_name="Guest CRM CI Return",
        phone=phone,
        email=email,
        notes="Repeat guest identity and history E2E",
    )
    second_guest_id = asyncio.run(reservation_guest(second_reservation_id))
    assert second_guest_id == guest_id
    assert asyncio.run(guest_identity_count(phone, email)) == 1

    second_check_in = owner.post(f'/api/v1/admin/stays/reservations/{second_reservation_id}/check-in')
    second_check_in.raise_for_status()
    second_stay_id = second_check_in.json()["stay_id"]
    assert second_stay_id != first_stay_id

    detail2 = owner.get(f'/api/v1/admin/guest-crm/{guest_id}')
    detail2.raise_for_status()
    crm2 = detail2.json()
    assert len(crm2["stays"]) == 2, crm2["stays"]
    stays_by_id = {item["id"]: item for item in crm2["stays"]}
    assert stays_by_id[first_stay_id]["status"] == "CHECKED_OUT"
    assert stays_by_id[first_stay_id]["actual_check_out_at"] is not None
    assert len(stays_by_id[first_stay_id]["assignments"]) == 2
    assert stays_by_id[second_stay_id]["status"] == "ACTIVE"
    assert len(stays_by_id[second_stay_id]["assignments"]) == 1
    assert stays_by_id[second_stay_id]["assignments"][0]["room_code"] == second_room["code"]
    preferences = {item["key"]: item for item in crm2["preferences"]}
    assert preferences["HOUSEKEEPING_TIME"]["active"] is True
    assert preferences["HOUSEKEEPING_TIME"]["value"] == "После 16:00"
    event_types2 = [event["event_type"] for event in crm2["events"]]
    assert event_types2.count("CHECK_IN") >= 2
    assert "CHECK_OUT" in event_types2 and "ROOM_RELOCATION" in event_types2

    intelligence = owner.get(f'/api/v1/admin/intelligence/guests/{guest_id}')
    intelligence.raise_for_status()
    intel = intelligence.json()
    assert intel["lifetime"]["reservation_count"] == 2
    assert intel["lifetime"]["completed_stays"] == 1
    assert len(intel["reservations"]) == 2

    deleted = owner.delete(f'/api/v1/admin/guest-crm/{guest_id}/preferences/HOUSEKEEPING_TIME')
    assert deleted.status_code == 204, deleted.text
    detail3 = owner.get(f'/api/v1/admin/guest-crm/{guest_id}')
    detail3.raise_for_status()
    preferences3 = {item["key"]: item for item in detail3.json()["preferences"]}
    assert preferences3["HOUSEKEEPING_TIME"]["active"] is False

    assert asyncio.run(audit_count("UPSERT_GUEST_PREFERENCE", guest_id)) == 2
    assert asyncio.run(audit_count("DEACTIVATE_GUEST_PREFERENCE", guest_id)) == 1
    assert asyncio.run(payment_count()) == payments_before

    owner.close()
    print("GUEST_CRM_REPEAT_GUEST_E2E_OK")


if __name__ == "__main__":
    main()
