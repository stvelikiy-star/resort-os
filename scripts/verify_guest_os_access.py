#!/usr/bin/env python3
import asyncio
import hashlib
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "guest-access-ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Guest-Access-CI-Owner-Password-2026")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
COOKIE_NAME = "tc_guest_session"


def assert_no_pii(body: dict):
    raw = str(body).lower()
    assert "phone" not in raw, body
    assert "email" not in raw, body
    assert "passport" not in raw, body
    assert body.get("guest") is None, body
    assert body.get("stay") is None, body


async def local_today() -> date:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
    finally:
        await conn.close()


async def set_room_clean(room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', uuid.UUID(room_id))
    finally:
        await conn.close()


async def payment_count() -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval("SELECT count(*)::int FROM payments")
    finally:
        await conn.close()


async def prove_qr_hash(qr_id: str, raw_token: str, room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('SELECT "tokenHash",status::text AS status,"roomId",label FROM room_qrs WHERE id=$1', uuid.UUID(qr_id))
        assert row and row["status"] == "ACTIVE"
        assert str(row["roomId"]) == room_id
        expected = "sha256:" + hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert row["tokenHash"] == expected
        assert row["tokenHash"] != raw_token
        assert raw_token not in (row["label"] or "")
    finally:
        await conn.close()


async def target_room(room_id: str, room_type_code: str, start: date, end: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''
            SELECT room.id,room.code
            FROM rooms room
            JOIN room_types rt ON rt.id=room."roomTypeId"
            WHERE rt.code=$1 AND room.id<>$2 AND room."operationalState"<>'TECH_BLOCK'
              AND NOT EXISTS (
                SELECT 1 FROM inventory_blocks ib
                WHERE ib."roomId"=room.id AND ib.active=true
                  AND daterange(ib."startDate",ib."endDate",'[)') && daterange($3::date,$4::date,'[)')
              )
              AND NOT EXISTS (
                SELECT 1 FROM room_assignments ra WHERE ra."roomId"=room.id AND ra."endedAt" IS NULL
              )
            ORDER BY room.code LIMIT 1
            ''',
            room_type_code,
            uuid.UUID(room_id),
            start - timedelta(days=1),
            end,
        )
        assert row, "No relocation target available"
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', row["id"])
        return str(row["id"]), row["code"]
    finally:
        await conn.close()


async def reservation_version(reservation_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''SELECT to_char("updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') FROM reservations WHERE id=$1''',
            uuid.UUID(reservation_id),
        )
    finally:
        await conn.close()


async def prepare_early_checkout(reservation_id: str, room_id: str, today: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yesterday = today - timedelta(days=1)
        await conn.execute('UPDATE reservations SET "checkIn"=$1,"updatedAt"=now() WHERE id=$2', yesterday, uuid.UUID(reservation_id))
        await conn.execute(
            '''
            UPDATE inventory_blocks SET "startDate"=$1,"updatedAt"=now()
            WHERE "reservationId"=$2 AND "roomId"=$3 AND active=true AND "blockType"='RESERVATION'
            ''',
            yesterday,
            uuid.UUID(reservation_id),
            uuid.UUID(room_id),
        )
    finally:
        await conn.close()


async def prove_session(raw_session: str, stay_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        expected = "sha256:" + hashlib.sha256(raw_session.encode("utf-8")).hexdigest()
        row = await conn.fetchrow(
            'SELECT id,"tokenHash",status::text AS status,"stayId","guestId","expiresAt" FROM guest_sessions WHERE "tokenHash"=$1',
            expected,
        )
        assert row and row["status"] == "ACTIVE"
        assert str(row["stayId"]) == stay_id
        assert row["tokenHash"] != raw_session
        history = await conn.fetchval(
            "SELECT count(*)::int FROM guest_history_events WHERE \"stayId\"=$1 AND \"eventType\"='GUEST_OS_SESSION_VERIFIED'",
            uuid.UUID(stay_id),
        )
        assert history >= 1
        return str(row["id"])
    finally:
        await conn.close()


async def prove_attempt_audit(qr_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        failures = await conn.fetchval(
            '''SELECT count(*)::int FROM audit_logs WHERE resource='RoomQr' AND "resourceId"=$1 AND action='VERIFY_PIN' AND source='GUEST_OS' AND result='FAILURE' ''',
            qr_id,
        )
        success = await conn.fetchval(
            '''SELECT count(*)::int FROM audit_logs WHERE resource='RoomQr' AND "resourceId"=$1 AND action='VERIFY_PIN' AND source='GUEST_OS' AND result='SUCCESS' ''',
            qr_id,
        )
        assert failures >= 5, failures
        assert success >= 1, success
    finally:
        await conn.close()


async def prove_checkout(stay_id: str, session_id: str, qr_ids: list[str]):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stay = await conn.fetchrow('SELECT status::text AS status,"actualCheckOutAt" FROM stays WHERE id=$1', uuid.UUID(stay_id))
        assert stay and stay["status"] == "CHECKED_OUT" and stay["actualCheckOutAt"] is not None
        session = await conn.fetchrow('SELECT status::text AS status,"revokedAt" FROM guest_sessions WHERE id=$1', uuid.UUID(session_id))
        assert session and session["status"] == "REVOKED" and session["revokedAt"] is not None
        for qr_id in qr_ids:
            status_value = await conn.fetchval('SELECT status::text FROM room_qrs WHERE id=$1', uuid.UUID(qr_id))
            assert status_value == "ACTIVE"
        open_assignment = await conn.fetchval('SELECT count(*)::int FROM room_assignments WHERE "stayId"=$1 AND "endedAt" IS NULL', uuid.UUID(stay_id))
        assert open_assignment == 0
    finally:
        await conn.close()


def main():
    today = asyncio.run(local_today())
    end = today + timedelta(days=2)
    client = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-os-ci-main"})
    login = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    grid = client.get("/api/v1/pms/grid", params={"start": today.isoformat(), "end": end.isoformat()})
    grid.raise_for_status()
    chosen = None
    preview_body = None
    for room in grid.json()["rooms"]:
        preview = client.post(
            "/api/v1/admin/pms/reservations/new/preview",
            json={"room_id": room["id"], "check_in": today.isoformat(), "check_out": end.isoformat(), "adults": 1, "children": 0},
        )
        if preview.status_code == 200 and preview.json().get("can_commit"):
            chosen = room
            preview_body = preview.json()
            break
    assert chosen and preview_body, "No sellable room for Guest OS access test"
    asyncio.run(set_room_clean(chosen["id"]))

    # Permanent QR can exist before any guest is assigned. Plaintext token is returned once only.
    issue = client.post(f'/api/v1/admin/guest-os/room-qrs/{chosen["id"]}/issue')
    issue.raise_for_status()
    issued = issue.json()
    assert issued["token_display_once"] is True
    assert issued["reprint_requires_rotation"] is True
    assert "<svg" in issued["qr_svg"]
    token = issued["token"]
    qr_id = issued["qr_id"]
    asyncio.run(prove_qr_hash(qr_id, token, chosen["id"]))

    invalid = client.get("/api/v1/guest-os/rooms/not-a-real-room-qr-token-123456")
    assert invalid.status_code == 404
    before_stay = client.get(f"/api/v1/guest-os/rooms/{token}")
    before_stay.raise_for_status()
    before_body = before_stay.json()
    assert before_body["active_stay"] is False and before_body["authenticated"] is False
    assert_no_pii(before_body)

    payments_before = asyncio.run(payment_count())
    suffix = uuid.uuid4().hex[:8]
    commit = client.post(
        "/api/v1/admin/pms/reservations/new/commit",
        json={
            "room_id": chosen["id"],
            "check_in": today.isoformat(),
            "check_out": end.isoformat(),
            "adults": 1,
            "children": 0,
            "guest_name": "Guest Access CI",
            "phone": "+996555" + suffix[:6],
            "email": f"guest-access-{suffix}@example.com",
            "expected_total_kgs": preview_body["pricing"]["total_kgs"],
            "expected_pricing_source": preview_body["pricing"]["source"],
            "notes": "Guest OS access E2E",
        },
    )
    commit.raise_for_status()
    reservation_id = commit.json()["reservation_id"]
    assert commit.json()["payment_created"] is False
    assert asyncio.run(payment_count()) == payments_before

    check_in = client.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-in")
    check_in.raise_for_status()
    check_in_body = check_in.json()
    stay_id = check_in_body["stay_id"]
    pin = check_in_body["guest_access_pin"]
    assert pin.isdigit() and len(pin) == 6

    locked = client.get(f"/api/v1/guest-os/rooms/{token}")
    locked.raise_for_status()
    locked_body = locked.json()
    assert locked_body["active_stay"] is True and locked_body["verification_required"] is True
    assert_no_pii(locked_body)

    # A photographed room QR is insufficient; brute-force attempts are durably rate-limited.
    brute = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-os-ci-bruteforce"})
    wrong = "000000" if pin != "000000" else "111111"
    for attempt in range(5):
        response = brute.post(f"/api/v1/guest-os/rooms/{token}/verify", json={"pin": wrong})
        if attempt < 4:
            assert response.status_code == 401, (attempt, response.status_code, response.text)
        else:
            assert response.status_code == 429, response.text
    blocked = brute.post(f"/api/v1/guest-os/rooms/{token}/verify", json={"pin": wrong})
    assert blocked.status_code == 429
    brute.close()

    verified = client.post(f"/api/v1/guest-os/rooms/{token}/verify", json={"pin": pin})
    verified.raise_for_status()
    set_cookie = verified.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie
    raw_session = client.cookies.get(COOKIE_NAME)
    assert raw_session and len(raw_session) >= 40
    session_id = asyncio.run(prove_session(raw_session, stay_id))
    asyncio.run(prove_attempt_audit(qr_id))

    personalized = client.get(f"/api/v1/guest-os/rooms/{token}")
    personalized.raise_for_status()
    personal_body = personalized.json()
    assert personal_body["authenticated"] is True
    assert personal_body["guest"]["first_name"] == "Guest Access CI"
    assert personal_body["room"]["code"] == chosen["code"]
    personal_raw = str(personal_body).lower()
    assert "phone" not in personal_raw and "email" not in personal_raw and "passport" not in personal_raw

    target_id, target_code = asyncio.run(target_room(chosen["id"], chosen["room_type_code"], today, end))
    target_issue = client.post(f"/api/v1/admin/guest-os/room-qrs/{target_id}/issue")
    target_issue.raise_for_status()
    target_qr = target_issue.json()
    asyncio.run(prove_qr_hash(target_qr["qr_id"], target_qr["token"], target_id))
    target_before = client.get(f'/api/v1/guest-os/rooms/{target_qr["token"]}')
    target_before.raise_for_status()
    assert target_before.json()["active_stay"] is False

    version = asyncio.run(reservation_version(reservation_id))
    segments = [{"room_id": target_id, "start": today.isoformat(), "end": end.isoformat()}]
    schedule_preview = client.post(f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/preview", json={"segments": segments})
    schedule_preview.raise_for_status()
    schedule_commit = client.post(
        f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/commit",
        json={"segments": segments, "expected_version": version},
    )
    schedule_commit.raise_for_status()

    old_after_move = client.get(f"/api/v1/guest-os/rooms/{token}")
    old_after_move.raise_for_status()
    assert old_after_move.json()["active_stay"] is False
    assert_no_pii(old_after_move.json())
    new_after_move = client.get(f'/api/v1/guest-os/rooms/{target_qr["token"]}')
    new_after_move.raise_for_status()
    moved_body = new_after_move.json()
    assert moved_body["authenticated"] is True and moved_body["room"]["code"] == target_code
    assert moved_body["guest"]["first_name"] == "Guest Access CI"

    asyncio.run(prepare_early_checkout(reservation_id, target_id, today))
    checkout = client.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-out")
    checkout.raise_for_status()
    assert checkout.json()["revoked_guest_sessions"] >= 1
    asyncio.run(prove_checkout(stay_id, session_id, [qr_id, target_qr["qr_id"]]))

    after_checkout = client.get(f'/api/v1/guest-os/rooms/{target_qr["token"]}')
    after_checkout.raise_for_status()
    after_body = after_checkout.json()
    assert after_body["active_stay"] is False and after_body["authenticated"] is False
    assert_no_pii(after_body)

    qr_list = client.get("/api/v1/admin/guest-os/room-qrs")
    qr_list.raise_for_status()
    items = qr_list.json()["items"]
    assert len(items) == 84
    assert all(item["raw_token_recoverable"] is False for item in items)

    client.close()
    print("GUEST_OS_ACCESS_E2E_OK")
    print("PASS: permanent room QR, hash-only secrets, no-PII unauthenticated context, durable PIN rate limit, HttpOnly guest session, relocation-safe room context, checkout revoke, 84-room admin registry, no payment mutation")


if __name__ == "__main__":
    main()
