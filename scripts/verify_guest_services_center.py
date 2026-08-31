#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx
from argon2 import PasswordHasher

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "guest-services-center-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Guest-Services-Center-Owner-2026")
STAFF_PASSWORD = "Guest-Services-Center-Staff-2026"
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


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


async def snapshot_finance_and_room(reservation_id: str, room_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT r."totalKgs",rm."operationalState"::text AS room_state,
                      (SELECT count(*)::int FROM payments p WHERE p."reservationId"=r.id) AS payment_count
               FROM reservations r JOIN rooms rm ON rm.id=$2
               WHERE r.id=$1''',
            uuid.UUID(reservation_id),
            uuid.UUID(room_id),
        )
        assert row
        return int(row["totalKgs"]), row["room_state"], int(row["payment_count"])
    finally:
        await conn.close()


async def ensure_staff(username: str, role: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        staff_id = await conn.fetchval(
            'SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2',
            pid,
            username,
        )
        password_hash = password_hasher.hash(STAFF_PASSWORD)
        if staff_id:
            await conn.execute(
                '''UPDATE staff_users SET "displayName"=$1,"passwordHash"=$2,role=$3::"StaffRole","isActive"=true,"updatedAt"=now()
                   WHERE id=$4''',
                f"CI {role}",
                password_hash,
                role,
                staff_id,
            )
        else:
            staff_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO staff_users (id,"propertyId",username,"displayName","passwordHash",role,"isActive","createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6::"StaffRole",true,now(),now())''',
                staff_id,
                pid,
                username,
                f"CI {role}",
                password_hash,
                role,
            )
        await conn.execute('UPDATE auth_sessions SET "revokedAt"=now() WHERE "userId"=$1 AND "revokedAt" IS NULL', staff_id)
        return str(staff_id)
    finally:
        await conn.close()


async def create_checked_in_reservation_without_stay(today: date) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        assert pid
        guest_id = uuid.uuid4()
        reservation_id = uuid.uuid4()
        suffix = uuid.uuid4().hex[:8]
        await conn.execute(
            '''INSERT INTO guests (id,"propertyId","firstName",phone,"createdAt","updatedAt")
               VALUES ($1,$2,$3,$4,now(),now())''',
            guest_id,
            pid,
            "Orphan Stay CI",
            "+996711" + suffix[:6],
        )
        await conn.execute(
            '''INSERT INTO reservations (
                 id,"propertyId","bookingNumber","primaryGuestId",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt"
               ) VALUES ($1,$2,$3,$4,'CHECKED_IN',$5,$6,1,0,1,now(),now())''',
            reservation_id,
            pid,
            f"ORPHAN-{suffix}",
            guest_id,
            today,
            today + timedelta(days=1),
        )
        return str(reservation_id)
    finally:
        await conn.close()


async def task_count_for_reservation(reservation_id: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            '''SELECT count(*)::int FROM operational_tasks
               WHERE "reservationId"=$1 AND type='GUEST_REQUEST' ''',
            uuid.UUID(reservation_id),
        )
    finally:
        await conn.close()


async def task_row(task_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchrow(
            '''SELECT id,type::text AS type,status::text AS status,priority::text AS priority,
                      "serviceCode",source,"reservationId","stayId","roomId","assignedToId","createdByType"
               FROM operational_tasks WHERE id=$1''',
            uuid.UUID(task_id),
        )
    finally:
        await conn.close()


async def assert_history(stay_id: str, task_ids: list[str], completed: list[str], cancelled: list[str]):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for task_id in task_ids:
            created = await conn.fetchval(
                '''SELECT count(*)::int FROM guest_history_events
                   WHERE "stayId"=$1 AND "eventType"='GUEST_REQUEST_CREATED'
                     AND "payloadJson"->>'task_id'=$2''',
                uuid.UUID(stay_id),
                task_id,
            )
            assert created >= 1, ("missing created history", task_id)
        for task_id in completed:
            done = await conn.fetchval(
                '''SELECT count(*)::int FROM guest_history_events
                   WHERE "stayId"=$1 AND "eventType"='GUEST_REQUEST_COMPLETED'
                     AND "payloadJson"->>'task_id'=$2''',
                uuid.UUID(stay_id),
                task_id,
            )
            assert done == 1, ("missing/duplicate completed history", task_id, done)
        for task_id in cancelled:
            value = await conn.fetchval(
                '''SELECT count(*)::int FROM guest_history_events
                   WHERE "stayId"=$1 AND "eventType"='GUEST_REQUEST_CANCELLED'
                     AND "payloadJson"->>'task_id'=$2''',
                uuid.UUID(stay_id),
                task_id,
            )
            assert value == 1, ("missing/duplicate cancelled history", task_id, value)
    finally:
        await conn.close()


async def audit_count(action: str, task_id: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchval(
            'SELECT count(*)::int FROM audit_logs WHERE action=$1 AND resource=\'OperationalTask\' AND "resourceId"=$2 AND result=\'SUCCESS\'',
            action,
            task_id,
        )
    finally:
        await conn.close()


def login(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-services-center-ci"})
    response = client.post('/api/v1/auth/login', json={"username": username, "password": password})
    response.raise_for_status()
    return client


def create_service(
    client: httpx.Client,
    reservation_id: str,
    code: str,
    *,
    service_date: date,
    description: str,
    service_time: str | None = None,
):
    payload = {
        "reservation_id": reservation_id,
        "service_code": code,
        "service_date": service_date.isoformat(),
        "priority": "HIGH" if code in {"MAINTENANCE", "TRANSFER"} else "NORMAL",
        "description": description,
    }
    if service_time:
        payload["service_time"] = service_time
    response = client.post('/api/v1/admin/guest-services', json=payload)
    response.raise_for_status()
    body = response.json()
    assert body["service_code"] == code and body["status"] == "OPEN", body
    return body


def routed_codes(client: httpx.Client) -> set[str]:
    response = client.get('/api/v1/ops/guest-requests', params={"status": "ACTIVE", "limit": 300})
    response.raise_for_status()
    return {item["request_code"] for item in response.json()["items"]}


def claim_complete(client: httpx.Client, task_id: str):
    claim = client.post(f'/api/v1/ops/guest-requests/{task_id}/claim')
    claim.raise_for_status()
    assert claim.json()["status"] == "IN_PROGRESS"
    done = client.post(f'/api/v1/ops/guest-requests/{task_id}/complete')
    done.raise_for_status()
    assert done.json()["status"] == "DONE"


def main():
    today = asyncio.run(local_today())
    end = today + timedelta(days=3)
    owner = login(OWNER_USERNAME, OWNER_PASSWORD)

    # Build one real current Stay through the manager-owned PMS flow.
    grid = owner.get('/api/v1/pms/grid', params={"start": today.isoformat(), "end": end.isoformat()})
    grid.raise_for_status()
    chosen = None
    preview_body = None
    for room in grid.json()["rooms"]:
        preview = owner.post('/api/v1/admin/pms/reservations/new/preview', json={
            "room_id": room["id"],
            "check_in": today.isoformat(),
            "check_out": end.isoformat(),
            "adults": 1,
            "children": 0,
        })
        if preview.status_code == 200 and preview.json().get("can_commit"):
            chosen = room
            preview_body = preview.json()
            break
    assert chosen and preview_body, "No sellable room for Guest Services Center E2E"
    asyncio.run(set_room_clean(chosen["id"]))

    suffix = uuid.uuid4().hex[:8]
    commit = owner.post('/api/v1/admin/pms/reservations/new/commit', json={
        "room_id": chosen["id"],
        "check_in": today.isoformat(),
        "check_out": end.isoformat(),
        "adults": 1,
        "children": 0,
        "guest_name": "Guest Services Center CI",
        "phone": "+996700" + suffix[:6],
        "email": f"guest-services-center-{suffix}@example.com",
        "expected_total_kgs": preview_body["pricing"]["total_kgs"],
        "expected_pricing_source": preview_body["pricing"]["source"],
        "notes": "Unified Guest Services Center E2E",
    })
    commit.raise_for_status()
    reservation_id = commit.json()["reservation_id"]
    assert commit.json()["payment_created"] is False

    check_in = owner.post(f'/api/v1/admin/stays/reservations/{reservation_id}/check-in')
    check_in.raise_for_status()
    stay_id = check_in.json()["stay_id"]
    pin = check_in.json()["guest_access_pin"]
    assert check_in.json()["room_code"] == chosen["code"]

    finance_before = asyncio.run(snapshot_finance_and_room(reservation_id, chosen["id"]))
    assert finance_before[1] == "CLEAN"

    # Current RBAC roles must be reproducible by tooling/database and usable in Core.
    reception_username = f"gsc-reception-{suffix}"
    maid_username = f"gsc-maid-{suffix}"
    tech_username = f"gsc-tech-{suffix}"
    dining_username = f"gsc-dining-{suffix}"
    reception_id = asyncio.run(ensure_staff(reception_username, "RECEPTION"))
    asyncio.run(ensure_staff(maid_username, "MAID"))
    asyncio.run(ensure_staff(tech_username, "TECHNICIAN"))
    asyncio.run(ensure_staff(dining_username, "DINING_STAFF"))

    reception = login(reception_username, STAFF_PASSWORD)
    maid = login(maid_username, STAFF_PASSWORD)
    tech = login(tech_username, STAFF_PASSWORD)
    dining = login(dining_username, STAFF_PASSWORD)

    # Reception can see the unified center.
    center = reception.get('/api/v1/admin/guest-services', params={"status": "ACTIVE"})
    center.raise_for_status()
    assert "Unified Guest Services Center" in center.json()["truth"]

    # Fail closed: a CHECKED_IN reservation without a factual active Stay is inconsistent
    # and must never generate an orphan operational request.
    orphan_reservation_id = asyncio.run(create_checked_in_reservation_without_stay(today))
    orphan = reception.post('/api/v1/admin/guest-services', json={
        "reservation_id": orphan_reservation_id,
        "service_code": "ADMIN",
        "service_date": today.isoformat(),
        "description": "Must fail closed",
    })
    assert orphan.status_code == 409, orphan.text
    assert orphan.json()["detail"]["code"] == "GUEST_SERVICE_ACTIVE_STAY_REQUIRED", orphan.text
    assert asyncio.run(task_count_for_reservation(orphan_reservation_id)) == 0

    # Service date is bounded by the reservation/stay period.
    outside = reception.post('/api/v1/admin/guest-services', json={
        "reservation_id": reservation_id,
        "service_code": "ADMIN",
        "service_date": (end + timedelta(days=1)).isoformat(),
        "description": "Outside stay",
    })
    assert outside.status_code == 422, outside.text
    assert outside.json()["detail"]["code"] == "GUEST_SERVICE_DATE_OUTSIDE_RESERVATION", outside.text

    towels = create_service(reception, reservation_id, "TOWELS", service_date=today, description="2 полотенца")
    maintenance = create_service(reception, reservation_id, "MAINTENANCE", service_date=today, description="Не работает лампа")
    meals = create_service(reception, reservation_id, "MEALS", service_date=today, description="Дополнительный завтрак")
    transfer = create_service(
        reception,
        reservation_id,
        "TRANSFER",
        service_date=today + timedelta(days=1),
        service_time="12:30",
        description="Трансфер до аэропорта",
    )
    parking = create_service(reception, reservation_id, "PARKING", service_date=today, description="Место для автомобиля")

    pms_task_ids = [towels["id"], maintenance["id"], meals["id"], transfer["id"], parking["id"]]
    for body in [towels, maintenance, meals, transfer, parking]:
        assert body["stay_id"] == stay_id, body
        assert body["room_id"] == chosen["id"], body
        assert body["room_code"] == chosen["code"], body
        assert body["source"] == "PMS_GUEST_SERVICE", body
        row = asyncio.run(task_row(body["id"]))
        assert row and row["type"] == "GUEST_REQUEST" and str(row["stayId"]) == stay_id
        assert str(row["roomId"]) == chosen["id"]
        assert row["createdByType"] == "STAFF"
        assert asyncio.run(audit_count("CREATE_GUEST_SERVICE", body["id"])) == 1

    # Establish a real Guest OS session on the same Stay.
    issue = owner.post(f'/api/v1/admin/guest-os/room-qrs/{chosen["id"]}/issue')
    issue.raise_for_status()
    qr_token = issue.json()["token"]
    guest = httpx.Client(base_url=BASE_URL, timeout=30.0, headers={"user-agent": "guest-services-center-guest"})
    verified = guest.post(f'/api/v1/guest-os/rooms/{qr_token}/verify', json={"pin": pin})
    verified.raise_for_status()

    # Cross-channel duplicate protection: Reception/PMS already created TRANSFER,
    # so Guest OS cannot create a second active task for the same factual service.
    guest_duplicate = guest.post(f'/api/v1/guest-os/rooms/{qr_token}/requests', json={
        "request_code": "TRANSFER",
        "description": "Duplicate must be rejected",
        "service_date": (today + timedelta(days=1)).isoformat(),
        "service_time": "12:30",
    })
    assert guest_duplicate.status_code == 409, guest_duplicate.text
    duplicate_detail = guest_duplicate.json()["detail"]
    assert duplicate_detail["code"] == "GUEST_REQUEST_DUPLICATE_ACTIVE", duplicate_detail
    assert duplicate_detail["task_id"] == transfer["id"], duplicate_detail
    assert duplicate_detail["existing_source"] == "PMS_GUEST_SERVICE", duplicate_detail

    # Guest-created request appears in the exact same admin Center, not a parallel queue.
    guest_admin = guest.post(f'/api/v1/guest-os/rooms/{qr_token}/requests', json={
        "request_code": "ADMIN",
        "description": "Позвоните в номер",
    })
    guest_admin.raise_for_status()
    guest_admin_id = guest_admin.json()["id"]

    unified = reception.get('/api/v1/admin/guest-services', params={"status": "ACTIVE", "guest": "Guest Services Center CI"})
    unified.raise_for_status()
    by_id = {item["id"]: item for item in unified.json()["items"]}
    assert guest_admin_id in by_id and by_id[guest_admin_id]["source"] == "GUEST_OS_ADMIN"

    # Same table, same queue, channel-independent routing.
    maid_codes = routed_codes(maid)
    tech_codes = routed_codes(tech)
    dining_codes = routed_codes(dining)
    reception_codes = routed_codes(reception)
    assert "TOWELS" in maid_codes and "MAINTENANCE" not in maid_codes and "MEALS" not in maid_codes
    assert "MAINTENANCE" in tech_codes and "TOWELS" not in tech_codes
    assert "MEALS" in dining_codes and "TRANSFER" not in dining_codes
    assert {"TRANSFER", "PARKING", "ADMIN"}.issubset(reception_codes)
    assert "TOWELS" not in reception_codes and "MEALS" not in reception_codes and "MAINTENANCE" not in reception_codes

    # Wrong department cannot take another department's request.
    wrong = reception.post(f'/api/v1/ops/guest-requests/{towels["id"]}/claim')
    assert wrong.status_code == 403, wrong.text
    wrong = maid.post(f'/api/v1/ops/guest-requests/{maintenance["id"]}/claim')
    assert wrong.status_code == 403, wrong.text

    # Correct roles execute PMS-created requests and the Guest OS request.
    claim_complete(maid, towels["id"])
    claim_complete(tech, maintenance["id"])
    claim_complete(dining, meals["id"])
    claim_complete(reception, transfer["id"])
    claim_complete(reception, guest_admin_id)

    # Reception can cancel its own unassigned routed request.
    cancelled = reception.post(f'/api/v1/ops/guest-requests/{parking["id"]}/cancel')
    cancelled.raise_for_status()
    assert cancelled.json()["status"] == "CANCELLED"

    # Financial and room-state invariants: requests are operational facts only.
    finance_after = asyncio.run(snapshot_finance_and_room(reservation_id, chosen["id"]))
    assert finance_after == finance_before, (finance_before, finance_after)

    completed_ids = [towels["id"], maintenance["id"], meals["id"], transfer["id"], guest_admin_id]
    asyncio.run(assert_history(stay_id, pms_task_ids + [guest_admin_id], completed_ids, [parking["id"]]))
    for task_id in completed_ids:
        assert asyncio.run(audit_count("COMPLETE_GUEST_REQUEST", task_id)) == 1
    assert asyncio.run(audit_count("CANCEL_GUEST_REQUEST", parking["id"])) == 1

    # Center filter facts remain coherent after execution.
    done = owner.get('/api/v1/admin/guest-services', params={"status": "DONE", "stay_id": stay_id})
    done.raise_for_status()
    done_ids = {item["id"] for item in done.json()["items"]}
    assert set(completed_ids).issubset(done_ids)
    cancelled_list = owner.get('/api/v1/admin/guest-services', params={"status": "CANCELLED", "stay_id": stay_id})
    cancelled_list.raise_for_status()
    assert parking["id"] in {item["id"] for item in cancelled_list.json()["items"]}

    # Assignment is factual and reception completion used the current authenticated user.
    transfer_row = asyncio.run(task_row(transfer["id"]))
    assert str(transfer_row["assignedToId"]) == reception_id

    guest.close()
    dining.close()
    tech.close()
    maid.close()
    reception.close()
    owner.close()
    print("GUEST_SERVICES_CENTER_E2E_OK")


if __name__ == "__main__":
    main()
