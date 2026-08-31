import asyncio
import os
import uuid
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import asyncpg
import httpx


BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Only-Strong-Password-2026")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os").split("?")[0]


def assert_ok(response: httpx.Response, label: str):
    if response.status_code >= 400:
        raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text}")
    return response.json()


def iso(value: date) -> str:
    return value.isoformat()


async def verify_db(created: list[dict], room3: str, original_state: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        room_count = await conn.fetchval('SELECT count(*) FROM rooms')
        assert room_count == 84, f"expected 84 seeded rooms, got {room_count}"

        expected_beds = {
            "112": "1сп+1сп",
            "114": "2сп+кр+кр",
            "311": "2сп+1сп; кухня",
            "421": "2сп+1сп+1сп+д+кр+кр+кр",
        }
        rows = await conn.fetch('SELECT code,"bedConfiguration" FROM rooms WHERE code=ANY($1::text[])', list(expected_beds))
        actual = {row["code"]: row["bedConfiguration"] for row in rows}
        assert actual == expected_beds, f"owner room shorthand mismatch: {actual}"

        for item in created:
            reservation_id = uuid.UUID(item["reservation_id"])
            row = await conn.fetchrow(
                '''
                SELECT r."bookingNumber",r.status::text AS status,r."totalKgs",rr.status::text AS request_status,
                       rr.source,rr."quotedTotalKgs",ib."startDate",ib."endDate",ib."roomId"
                FROM reservations r
                JOIN reservation_requests rr ON rr.id=r."requestId"
                JOIN inventory_blocks ib ON ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
                WHERE r.id=$1
                ''',
                reservation_id,
            )
            assert row, f"reservation missing: {reservation_id}"
            assert row["status"] == "GUARANTEED"
            assert row["request_status"] == "CONVERTED"
            assert row["source"] == "PMS"
            assert row["totalKgs"] == item["total_kgs"]
            assert row["quotedTotalKgs"] == item["total_kgs"]
            assert row["startDate"].isoformat() == item["check_in"]
            assert row["endDate"].isoformat() == item["check_out"]
            assert str(row["roomId"]) == item["room_id"]

            payment_count = await conn.fetchval('SELECT count(*) FROM payments WHERE "reservationId"=$1', reservation_id)
            assert payment_count == 0, "owner grid commit must not fabricate a payment"

            audit = await conn.fetchrow(
                '''
                SELECT source,"afterJson" FROM audit_logs
                WHERE resource='Reservation' AND "resourceId"=$1 AND action='MANAGER_CREATE_RESERVATION_FROM_GRID'
                ORDER BY "createdAt" DESC LIMIT 1
                ''',
                str(reservation_id),
            )
            assert audit, "owner grid audit evidence missing"
            assert audit["source"] == "PMS_OWNER_GRID"
            payload = audit["afterJson"]
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            assert payload["payment_created"] is False
            assert payload["pricing_source"] == item["pricing_source"]
            assert int(payload["nights"]) == item["nights"]
            assert int(payload["total_kgs"]) == item["total_kgs"]

        await conn.execute('UPDATE rooms SET "operationalState"=$1::"RoomOperationalState" WHERE id=$2', original_state, uuid.UUID(room3))
    finally:
        await conn.close()


def main():
    today = date.today()
    try:
        today = __import__("datetime").datetime.now(ZoneInfo("Asia/Bishkek")).date()
    except Exception:
        pass
    d1 = today + timedelta(days=1)
    d2 = d1 + timedelta(days=1)
    d4 = d1 + timedelta(days=3)

    created: list[dict] = []
    with httpx.Client(base_url=BASE, timeout=20.0, follow_redirects=True) as client:
        login = client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD})
        assert_ok(login, "login")

        availability = assert_ok(
            client.get(
                "/api/v1/booking/check-availability",
                params={"check_in": iso(d1), "check_out": iso(d4), "adults": 2, "children": 0},
            ),
            "availability",
        )
        candidates = [
            item for item in availability["results"]
            if item["pricing"]["sellable"] and len(item["available_rooms"]) >= 3
        ]
        assert candidates, "need a sellable room type with at least three free rooms"
        candidate = candidates[0]
        room1, room2, room3 = [item["id"] for item in candidate["available_rooms"][:3]]

        one = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/preview",
                json={"room_id": room1, "check_in": iso(d1), "check_out": iso(d2), "adults": 2, "children": 0},
            ),
            "one-night preview",
        )
        assert one["nights"] == 1, f"one selected square must equal one night: {one['nights']}"
        assert one["can_commit"] is True
        assert len(one["pricing"]["nights"]) == 1
        assert one["pricing"]["total_kgs"] == one["pricing"]["nights"][0]["price_kgs"]

        multi = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/preview",
                json={"room_id": room1, "check_in": iso(d1), "check_out": iso(d4), "adults": 2, "children": 0},
            ),
            "multi-night preview",
        )
        assert multi["nights"] == 3, f"three selected squares must equal three nights: {multi['nights']}"
        assert len(multi["pricing"]["nights"]) == 3
        nightly_sum = sum(int(item["price_kgs"]) for item in multi["pricing"]["nights"])
        assert nightly_sum == multi["pricing"]["total_kgs"], f"Core total {multi['pricing']['total_kgs']} != nightly sum {nightly_sum}"
        assert multi["pricing"]["source"] == "CORE_RATE"

        commit1 = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/commit",
                json={
                    "room_id": room1,
                    "check_in": iso(d1),
                    "check_out": iso(d4),
                    "adults": 2,
                    "children": 0,
                    "manager_total_kgs": None,
                    "guest_name": "Owner Grid Core Price",
                    "phone": "+996555010101",
                    "email": None,
                    "notes": "owner-grid-ci core pricing",
                    "expected_total_kgs": multi["pricing"]["total_kgs"],
                    "expected_pricing_source": "CORE_RATE",
                },
            ),
            "core-price commit",
        )
        assert commit1["nights"] == 3
        assert commit1["payment_created"] is False
        assert commit1["pricing_source"] == "CORE_RATE"
        created.append(commit1)

        conflict = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/preview",
                json={"room_id": room1, "check_in": iso(d1), "check_out": iso(d2), "adults": 2, "children": 0},
            ),
            "conflict preview",
        )
        assert conflict["can_commit"] is False
        assert conflict["conflicts"], "occupied selected square must report a conflict"

        conflict_commit = client.post(
            "/api/v1/admin/pms/reservations/new/commit",
            json={
                "room_id": room1,
                "check_in": iso(d1),
                "check_out": iso(d2),
                "adults": 2,
                "children": 0,
                "manager_total_kgs": None,
                "guest_name": "Conflict Guest",
                "phone": "+996555010199",
                "expected_total_kgs": one["pricing"]["total_kgs"],
                "expected_pricing_source": "CORE_RATE",
            },
        )
        assert conflict_commit.status_code == 409, conflict_commit.text
        assert conflict_commit.json()["detail"]["code"] == "ROOM_CONFLICT"

        override_value = int(multi["pricing"]["total_kgs"]) + 123
        override = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/preview",
                json={
                    "room_id": room2,
                    "check_in": iso(d1),
                    "check_out": iso(d4),
                    "adults": 2,
                    "children": 0,
                    "manager_total_kgs": override_value,
                },
            ),
            "manager override preview",
        )
        assert override["pricing"]["source"] == "MANAGER_OVERRIDE"
        assert override["pricing"]["total_kgs"] == override_value
        assert override["pricing"]["core_total_kgs"] == multi["pricing"]["total_kgs"]

        commit2 = assert_ok(
            client.post(
                "/api/v1/admin/pms/reservations/new/commit",
                json={
                    "room_id": room2,
                    "check_in": iso(d1),
                    "check_out": iso(d4),
                    "adults": 2,
                    "children": 0,
                    "manager_total_kgs": override_value,
                    "guest_name": "Owner Grid Manager Price",
                    "phone": "+996555010102",
                    "expected_total_kgs": override_value,
                    "expected_pricing_source": "MANAGER_OVERRIDE",
                },
            ),
            "manager override commit",
        )
        assert commit2["payment_created"] is False
        assert commit2["total_kgs"] == override_value
        created.append(commit2)

        async def block_room():
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                state = await conn.fetchval('SELECT "operationalState"::text FROM rooms WHERE id=$1', uuid.UUID(room3))
                await conn.execute('UPDATE rooms SET "operationalState"=\'TECH_BLOCK\' WHERE id=$1', uuid.UUID(room3))
                return state
            finally:
                await conn.close()

        original_state = asyncio.run(block_room())
        tech = client.post(
            "/api/v1/admin/pms/reservations/new/preview",
            json={"room_id": room3, "check_in": iso(d1), "check_out": iso(d2), "adults": 2, "children": 0},
        )
        assert tech.status_code == 409, tech.text
        assert tech.json()["detail"]["code"] == "TARGET_ROOM_TECH_BLOCK"

    asyncio.run(verify_db(created, room3, original_state))
    print("PASS: PMS owner grid Core preview/commit, 1..N nights, nightly sum, conflict, TECH_BLOCK, explicit manager override, no fake payment, audit, owner room shorthand")


if __name__ == "__main__":
    main()
