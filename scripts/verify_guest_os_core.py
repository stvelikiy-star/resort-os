#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "guest-os-ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Guest-OS-CI-Owner-Password-2026")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]


def choose_option(client: httpx.Client, start: date, end: date):
    response = client.get(
        "/api/v1/booking/check-availability",
        params={"check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2, "children": 0},
    )
    response.raise_for_status()
    return next(item for item in response.json()["results"] if item["available_count"] > 0 and item["pricing"]["sellable"])


def create_reservation(client: httpx.Client, start: date, end: date):
    option = choose_option(client, start, end)
    suffix = uuid.uuid4().hex[:10]
    request = client.post(
        "/api/v1/booking/requests",
        json={
            "guest_name": "Guest OS CI",
            "phone": "+99655566" + suffix[:4],
            "email": f"guest-os-{suffix}@example.com",
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "adults": 2,
            "children": 0,
            "room_type_code": option["room_type_code"],
            "source": "CI_GUEST_OS",
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
            "external_ref": f"guest-os-ci-{suffix}",
            "idempotency_key": f"guest-os-ci-payment-{suffix}",
        },
    )
    confirm.raise_for_status()
    return confirm.json()["reservation_id"]


async def prepare_rooms(reservation_id: str, start: date, end: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        reservation_uuid = uuid.UUID(reservation_id)
        current = await conn.fetchrow(
            '''
            SELECT ib."roomId",room."roomTypeId",room.code
            FROM inventory_blocks ib
            JOIN rooms room ON room.id=ib."roomId"
            WHERE ib."reservationId"=$1 AND ib.active=true AND ib."blockType"='RESERVATION'
            ORDER BY ib."startDate" LIMIT 1
            ''',
            reservation_uuid,
        )
        assert current
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', current["roomId"])
        target = await conn.fetchrow(
            '''
            SELECT room.id,room.code
            FROM rooms room
            WHERE room."roomTypeId"=$1 AND room.id<>$2
              AND NOT EXISTS (
                SELECT 1 FROM inventory_blocks ib
                WHERE ib."roomId"=room.id AND ib.active=true
                  AND daterange(ib."startDate",ib."endDate",'[)') && daterange($3::date,$4::date,'[)')
              )
              AND NOT EXISTS (
                SELECT 1 FROM room_assignments ra
                WHERE ra."roomId"=room.id AND ra."endedAt" IS NULL
              )
            ORDER BY room.code
            LIMIT 1
            ''',
            current["roomTypeId"],
            current["roomId"],
            start - timedelta(days=1),
            end,
        )
        assert target, "No free same-type target room for Guest OS relocation test"
        await conn.execute('UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1', target["id"])
        return current["roomId"], target["id"]
    finally:
        await conn.close()


async def prove_check_in(reservation_id: str, visible_pin: str, stay_id: str, current_room_id: uuid.UUID):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stay = await conn.fetchrow(
            '''
            SELECT id,"guestId",status::text AS status,"guestAccessPinHash","actualCheckInAt"
            FROM stays WHERE id=$1
            ''',
            uuid.UUID(stay_id),
        )
        assert stay and stay["status"] == "ACTIVE" and stay["actualCheckInAt"] is not None
        assert visible_pin.isdigit() and len(visible_pin) == 6
        assert stay["guestAccessPinHash"] != visible_pin
        assert stay["guestAccessPinHash"].startswith("pbkdf2_sha256$")
        assignment = await conn.fetchrow(
            'SELECT id,"roomId","endedAt" FROM room_assignments WHERE "stayId"=$1 AND "endedAt" IS NULL',
            stay["id"],
        )
        assert assignment and assignment["roomId"] == current_room_id
        history_count = await conn.fetchval(
            "SELECT count(*) FROM guest_history_events WHERE \"stayId\"=$1 AND \"eventType\"='CHECK_IN'",
            stay["id"],
        )
        assert history_count == 1
        return stay["guestId"], assignment["id"]
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


async def prove_relocation(stay_id: str, old_assignment_id: uuid.UUID, from_room_id: uuid.UUID, to_room_id: uuid.UUID):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        old_assignment = await conn.fetchrow('SELECT "endedAt" FROM room_assignments WHERE id=$1', old_assignment_id)
        assert old_assignment and old_assignment["endedAt"] is not None
        current = await conn.fetchrow(
            'SELECT id,"roomId",source FROM room_assignments WHERE "stayId"=$1 AND "endedAt" IS NULL',
            uuid.UUID(stay_id),
        )
        assert current and current["roomId"] == to_room_id and current["source"] == "PMS_RELOCATION"
        event = await conn.fetchrow(
            '''SELECT "payloadJson" FROM guest_history_events
               WHERE "stayId"=$1 AND "eventType"='ROOM_RELOCATION'
               ORDER BY "occurredAt" DESC LIMIT 1''',
            uuid.UUID(stay_id),
        )
        assert event
        payload = event["payloadJson"]
        assert payload["from_room_id"] == str(from_room_id)
        assert payload["to_room_id"] == str(to_room_id)
        return current["id"]
    finally:
        await conn.close()


async def prepare_checkout(stay_id: str, reservation_id: str, guest_id: uuid.UUID, room_id: uuid.UUID, today: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yesterday = today - timedelta(days=1)
        reservation_uuid = uuid.UUID(reservation_id)
        await conn.execute('UPDATE reservations SET "checkIn"=$1,"updatedAt"=now() WHERE id=$2', yesterday, reservation_uuid)
        await conn.execute(
            '''UPDATE inventory_blocks SET "startDate"=$1,"updatedAt"=now()
               WHERE "reservationId"=$2 AND active=true AND "blockType"='RESERVATION' AND "roomId"=$3''',
            yesterday,
            reservation_uuid,
            room_id,
        )
        qr = await conn.fetchrow(
            '''SELECT id,"tokenHash" FROM room_qrs WHERE "roomId"=$1 AND status='ACTIVE' LIMIT 1''',
            room_id,
        )
        if not qr:
            qr_id = uuid.uuid4()
            qr_hash = "sha256:" + uuid.uuid4().hex + uuid.uuid4().hex
            await conn.execute(
                '''INSERT INTO room_qrs (id,"propertyId","roomId","tokenHash",status,label,"issuedAt","createdAt","updatedAt")
                   SELECT $1,"propertyId",id,$2,'ACTIVE','CI permanent room QR',now(),now(),now() FROM rooms WHERE id=$3''',
                qr_id,
                qr_hash,
                room_id,
            )
        else:
            qr_id = qr["id"]
            qr_hash = qr["tokenHash"]
        session_id = uuid.uuid4()
        session_hash = "sha256:" + uuid.uuid4().hex + uuid.uuid4().hex
        await conn.execute(
            '''INSERT INTO guest_sessions (
                 id,"propertyId","stayId","guestId","roomQrId","tokenHash",status,
                 "verificationMethod","verifiedAt","expiresAt","lastSeenAt","createdAt","updatedAt"
               )
               SELECT $1,s."propertyId",s.id,$2,$3,$4,'ACTIVE','PIN',now(),now()+interval '1 day',now(),now(),now()
               FROM stays s WHERE s.id=$5''',
            session_id,
            guest_id,
            qr_id,
            session_hash,
            uuid.UUID(stay_id),
        )
        return session_id, qr_id, qr_hash
    finally:
        await conn.close()


async def prove_checkout(stay_id: str, session_id: uuid.UUID, qr_id: uuid.UUID, qr_hash: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stay = await conn.fetchrow(
            'SELECT status::text AS status,"actualCheckOutAt","guestAccessPinHash" FROM stays WHERE id=$1',
            uuid.UUID(stay_id),
        )
        assert stay and stay["status"] == "CHECKED_OUT" and stay["actualCheckOutAt"] is not None
        assert stay["guestAccessPinHash"] is None
        open_assignments = await conn.fetchval(
            'SELECT count(*) FROM room_assignments WHERE "stayId"=$1 AND "endedAt" IS NULL',
            uuid.UUID(stay_id),
        )
        assert open_assignments == 0
        session = await conn.fetchrow(
            'SELECT status::text AS status,"revokedAt" FROM guest_sessions WHERE id=$1',
            session_id,
        )
        assert session and session["status"] == "REVOKED" and session["revokedAt"] is not None
        qr = await conn.fetchrow('SELECT status::text AS status,"tokenHash" FROM room_qrs WHERE id=$1', qr_id)
        assert qr and qr["status"] == "ACTIVE" and qr["tokenHash"] == qr_hash
        checkout_events = await conn.fetchval(
            "SELECT count(*) FROM guest_history_events WHERE \"stayId\"=$1 AND \"eventType\"='CHECK_OUT'",
            uuid.UUID(stay_id),
        )
        assert checkout_events == 1
    finally:
        await conn.close()


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    login = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    async def local_today():
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            return await conn.fetchval(
                "SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'"
            )
        finally:
            await conn.close()

    today = asyncio.run(local_today())
    end = today + timedelta(days=2)
    reservation_id = create_reservation(client, today, end)
    current_room_id, target_room_id = asyncio.run(prepare_rooms(reservation_id, today, end))

    check_in = client.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-in")
    check_in.raise_for_status()
    check_in_body = check_in.json()
    stay_id = check_in_body["stay_id"]
    visible_pin = check_in_body["guest_access_pin"]
    guest_id, old_assignment_id = asyncio.run(
        prove_check_in(reservation_id, visible_pin, stay_id, current_room_id)
    )

    version = asyncio.run(reservation_version(reservation_id))
    segments = [{"room_id": str(target_room_id), "start": today.isoformat(), "end": end.isoformat()}]
    preview = client.post(
        f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/preview",
        json={"segments": segments},
    )
    preview.raise_for_status()
    assert preview.json()["immediate_relocation"] is not None
    commit = client.post(
        f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/commit",
        json={"segments": segments, "expected_version": version},
    )
    commit.raise_for_status()
    commit_body = commit.json()
    assert commit_body["relocation_room_assignment_id"]
    asyncio.run(prove_relocation(stay_id, old_assignment_id, current_room_id, target_room_id))

    session_id, qr_id, qr_hash = asyncio.run(
        prepare_checkout(stay_id, reservation_id, guest_id, target_room_id, today)
    )
    checkout = client.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-out")
    checkout.raise_for_status()
    checkout_body = checkout.json()
    assert checkout_body["status"] == "CHECKED_OUT"
    assert checkout_body["guest_sessions_revoked"] >= 1
    asyncio.run(prove_checkout(stay_id, session_id, qr_id, qr_hash))

    client.close()
    print("GUEST_OS_CORE_E2E_OK")


if __name__ == "__main__":
    main()
