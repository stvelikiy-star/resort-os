#!/usr/bin/env python3
"""Real HTTPS + PostgreSQL, two unrelated hotels, canonical Guest OS routes.

CI ONLY. No mocks, no production host, no demo, no persistent user data.
The full shared platform still blocks Guest OS with 503 until separately approved.
"""
import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import asyncpg
import httpx

from marina_shared_live_browser_db import dsn, PASSWORD

ORIGIN = "https://localhost:18443"
CERT = Path(os.environ.get("MARINA_GUEST_QR_CI_CERT", "/tmp/marina-guest-qr-ci/cert.pem"))
COOKIE = "tc_guest_session"


def assert_status(response: httpx.Response, status: int, operation: str):
    assert response.status_code == status, (
        f"{operation}: {response.status_code}, expected {status}; "
        f"body code {str(response.json().get('detail', ''))[:200] if response.headers.get('content-type', '').startswith('application/json') else ''}"
    )
    return response.json() if response.content else {}


def client(label: str) -> httpx.Client:
    return httpx.Client(base_url=ORIGIN, verify=str(CERT), trust_env=False,
                        headers={"User-Agent": "marina-guest-ci-" + label}, timeout=20.0)


def hotel_login(session: httpx.Client, hotel: str):
    code = "HOTEL_" + hotel
    body = dict(username="owner", password=PASSWORD, property_code=code,
                tenant_code="tenant_" + hotel.lower())
    result = assert_status(session.post("/api/v1/auth/login", json=body), 200, "owner login " + code)
    assert result["property_code"] == code
    me = assert_status(session.get("/api/v1/auth/me"), 200, "auth me " + code)
    assert me["property_code"] == code
    return me


async def database_rooms() -> dict:
    conn = await asyncpg.connect(dsn())
    try:
        rows = await conn.fetch(
            """SELECT p.id AS property_id, p.code, r.id AS room_id, r.code AS room_code
               FROM properties p JOIN rooms r ON r."propertyId"=p.id ORDER BY p.code"""
        )
        assert len(rows) == 2
        return {r["code"][-1]: dict(r) for r in rows}
    finally:
        await conn.close()


async def database_evidence(fixtures):
    conn = await asyncpg.connect(dsn())
    try:
        for hotel, data in fixtures.items():
            pid = data["property_id"]
            qr = await conn.fetchrow(
                """SELECT "tokenHash",status::text AS status,"roomId"
                   FROM room_qrs WHERE id=$1 AND "propertyId"=$2""",
                uuid.UUID(data["qr_id"]), pid,
            )
            assert qr and qr["status"] == "ACTIVE" and qr["roomId"] == data["room_id"]
            assert qr["tokenHash"] == "sha256:" + hashlib.sha256(data["token"].encode()).hexdigest()
            assert qr["tokenHash"] != data["token"]
            session_count = await conn.fetchval(
                """SELECT count(*)::int FROM guest_sessions
                   WHERE "propertyId"=$1 AND "stayId"=$2 AND status='ACTIVE'""",
                pid, uuid.UUID(data["stay_id"]),
            )
            assert session_count == 1, (hotel, session_count)
            task = await conn.fetchrow(
                """SELECT "propertyId","roomId","stayId",source,type::text AS type
                   FROM operational_tasks WHERE id=$1""",
                uuid.UUID(data["task_id"]),
            )
            assert task and task["propertyId"] == pid
            assert task["roomId"] == data["room_id"]
            assert task["stayId"] == uuid.UUID(data["stay_id"])
            assert task["source"] == "GUEST_OS_ADMIN" and task["type"] == "GUEST_REQUEST"
            assert await conn.fetchval(
                """SELECT count(*)::int FROM operational_tasks
                   WHERE id=$1 AND "propertyId"<>$2""",
                uuid.UUID(data["task_id"]), pid,
            ) == 0
        assert len({v["stay_id"] for v in fixtures.values()}) == 2
        assert len({v["task_id"] for v in fixtures.values()}) == 2
        assert len({v["qr_id"] for v in fixtures.values()}) == 2
    finally:
        await conn.close()


async def database_checkout(fixtures):
    conn = await asyncpg.connect(dsn())
    try:
        for data in fixtures.values():
            assert await conn.fetchval(
                """SELECT count(*)::int FROM guest_sessions
                   WHERE "stayId"=$1 AND status='ACTIVE'""", uuid.UUID(data["stay_id"])
            ) == 0
            assert await conn.fetchval(
                """SELECT count(*)::int FROM room_assignments
                   WHERE "stayId"=$1 AND "endedAt" IS NULL""", uuid.UUID(data["stay_id"])
            ) == 0
            status = await conn.fetchval(
                'SELECT status::text FROM stays WHERE id=$1', uuid.UUID(data["stay_id"])
            )
            assert status == "CHECKED_OUT", status
    finally:
        await conn.close()


def main():
    assert os.environ.get("MARINA_GUEST_QR_CI_CONFIRM") == "ISOLATED_TWO_HOTEL_GUEST_QR_CI_ONLY"
    dsn()
    assert CERT.is_file()
    rooms = asyncio.run(database_rooms())
    owner = {h: client("owner-" + h) for h in ("A", "B")}
    guest = {h: client("guest-" + h) for h in ("A", "B")}
    anonymous = client("anonymous")
    brute = client("brute-pin-a")
    fixtures = {}
    try:
        assert_status(anonymous.get("/api/v1/auth/mode"), 200, "mode")
        # Only reviewed routers are mounted in this acceptance-only process.
        assert_status(anonymous.get("/api/v1/admin/inbox/conversations"), 404, "unmounted inbox")
        identities = {h: hotel_login(owner[h], h) for h in ("A", "B")}
        assert identities["A"]["tenant_id"] != identities["B"]["tenant_id"]
        assert identities["A"]["property_id"] != identities["B"]["property_id"]
        today = datetime.now(ZoneInfo("Asia/Bishkek")).date()
        start, end = today - timedelta(days=1), today + timedelta(days=1)
        for h in ("A", "B"):
            code = "HOTEL_" + h
            room = rooms[h]
            room_id = str(room["room_id"])
            # Property headers cannot override the authenticated hotel's context.
            foreign_id = str(rooms["B" if h == "A" else "A"]["room_id"])
            spoof = {"X-Property-Id": identities["B" if h == "A" else "A"]["property_id"],
                     "X-Tenant-Id": identities["B" if h == "A" else "A"]["tenant_id"]}
            assert_status(owner[h].post("/api/v1/admin/guest-os/room-qrs/" + foreign_id + "/issue",
                                        headers=spoof), 404, "foreign QR issue")
            assert_status(owner[h].post("/api/v1/admin/guest-os/room-qrs/" + foreign_id + "/rotate",
                                        headers=spoof), 404, "foreign QR rotate")

            issued = assert_status(owner[h].post(
                "/api/v1/admin/guest-os/room-qrs/" + room_id + "/issue"), 201, "QR issue")
            token = issued["token"]
            assert issued["room_id"] == room_id and issued["token_display_once"] is True
            assert "<svg" in issued["qr_svg"]
            link = urlsplit(issued["public_url"])
            assert link.scheme == "https" and link.netloc == "localhost:18443"
            assert link.path == "/g/" + token and not link.query and not link.fragment
            assert_status(owner[h].post(
                "/api/v1/admin/guest-os/room-qrs/" + room_id + "/issue"), 409, "duplicate QR issue")
            before = assert_status(anonymous.get(
                "/api/v1/guest-os/rooms/" + token), 200, "public QR before stay")
            assert before["authenticated"] is False and before["guest"] is None and before["stay"] is None
            assert before["active_stay"] is False
            assert before["property"] == {"name": "CI Hotel " + h}

            body = dict(room_id=room_id, check_in=start.isoformat(),
                        check_out=end.isoformat(), adults=1, children=0)
            preview = assert_status(owner[h].post(
                "/api/v1/admin/pms/reservations/new/preview", json=body), 200, "booking preview")
            assert preview["can_commit"] is True and preview["pricing"]["source"] == "CORE_RATE"
            created = assert_status(owner[h].post(
                "/api/v1/admin/pms/reservations/new/commit",
                json={**body, "guest_name": "Synthetic Hotel " + h + " Guest",
                      "phone": "+9965551000" + ("01" if h == "A" else "02"),
                      "expected_total_kgs": preview["pricing"]["total_kgs"],
                      "expected_pricing_source": preview["pricing"]["source"]}),
                201, "booking commit")
            reservation_id = created["reservation_id"]
            checkin = assert_status(owner[h].post(
                "/api/v1/admin/stays/reservations/" + reservation_id + "/check-in"),
                200, "check-in")
            pin = checkin["guest_access_pin"]
            assert len(pin) == 6 and pin.isdigit() and checkin["guest_access_pin_display_once"]
            assert_status(owner["B" if h == "A" else "A"].post(
                "/api/v1/admin/stays/reservations/" + reservation_id + "/check-out"),
                404, "foreign checkout")
            fixtures[h] = dict(property_id=room["property_id"], room_id=room["room_id"],
                               room_code=room["room_code"], qr_id=issued["qr_id"],
                               token=token, reservation_id=reservation_id,
                               stay_id=checkin["stay_id"], pin=pin)

        assert fixtures["A"]["token"] != fixtures["B"]["token"]
        for h in ("A", "B"):
            own = fixtures[h]
            other = fixtures["B" if h == "A" else "A"]
            listing = assert_status(owner[h].get(
                "/api/v1/admin/guest-os/room-qrs"), 200, "QR list")
            assert listing["property"] == "HOTEL_" + h
            assert {i["room_id"] for i in listing["items"]} == {str(own["room_id"])}
            assert other["qr_id"] not in {i["qr_id"] for i in listing["items"]}
            locked = assert_status(anonymous.get(
                "/api/v1/guest-os/rooms/" + own["token"]), 200, "QR unverified")
            assert locked["active_stay"] is True and locked["verification_required"] is True
            assert locked["guest"] is None and locked["stay"] is None
            # No client-supplied tenant ID can turn another hotel's QR into authority.
            foreign = assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + other["token"],
                headers={"X-Property-Id": identities[h]["property_id"]}), 200, "foreign anonymous")
            assert foreign["authenticated"] is False and foreign["guest"] is None

        for h in ("A", "B"):
            own = fixtures[h]
            auth = assert_status(guest[h].post(
                "/api/v1/guest-os/rooms/" + own["token"] + "/verify",
                json={"pin": own["pin"]}), 200, "guest PIN verify")
            assert auth["verified"] is True
            cookie_header = guest[h].cookies.get(COOKIE)
            assert cookie_header and len(cookie_header) >= 40
            received_cookie = guest[h].post  # keep client alive for session continuity
            del received_cookie
            private = assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + own["token"]), 200, "guest personal room")
            assert private["authenticated"] is True
            assert private["guest"]["first_name"] == "Synthetic Hotel " + h + " Guest"
            assert private["property"]["name"] == "CI Hotel " + h
            # Foreign QR still returns public non-PII even with an active guest session.
            other = fixtures["B" if h == "A" else "A"]
            cross = assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + other["token"]), 200, "foreign cookie room context")
            assert cross["authenticated"] is False and cross["guest"] is None and cross["stay"] is None
            assert_status(guest[h].post(
                "/api/v1/guest-os/rooms/" + other["token"] + "/requests",
                json={"request_code": "ADMIN"}), 401, "foreign guest task denial")
            # Local guest may request only their own property's service.
            made = assert_status(guest[h].post(
                "/api/v1/guest-os/rooms/" + own["token"] + "/requests",
                json={"request_code": "ADMIN", "description": "Synthetic call to reception"}),
                201, "guest service task")
            assert made["request_code"] == "ADMIN" and made["status"] == "OPEN"
            own["task_id"] = made["id"]
            assert_status(guest[h].post(
                "/api/v1/guest-os/rooms/" + own["token"] + "/requests",
                json={"request_code": "ADMIN"}), 409, "guest request deduplication")
            tasks = assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + own["token"] + "/requests"), 200, "local tasks")
            assert {task["id"] for task in tasks["items"]} == {own["task_id"]}
            assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + other["token"] + "/requests"),
                401, "foreign task list denied")

        asyncio.run(database_evidence(fixtures))
        # Five bad PIN attempts MUST throttle even when spoofed XFF and User-Agent change.
        wrong = "000000" if fixtures["A"]["pin"] != "000000" else "111111"
        for attempt in range(5):
            response = brute.post(
                "/api/v1/guest-os/rooms/" + fixtures["A"]["token"] + "/verify",
                json={"pin": wrong}, headers={"X-Forwarded-For": f"203.0.113.{attempt + 1}",
                                                   "User-Agent": f"spoofed-agent-{attempt}"})
            assert_status(response, 401 if attempt < 4 else 429, "PIN spoof-resistant rate limit")
        assert_status(brute.post(
            "/api/v1/guest-os/rooms/" + fixtures["A"]["token"] + "/verify",
            json={"pin": fixtures["A"]["pin"]}, headers={"X-Forwarded-For": "203.0.113.250",
                                                "User-Agent": "another-spoofed-agent"}),
            429, "PIN lockout persists")

        assert_status(guest["A"].post("/api/v1/guest-os/logout"), 200, "guest logout A")
        assert_status(guest["A"].get("/api/v1/guest-os/rooms/" + fixtures["A"]["token"]),
                      200, "anonymous after logout")
        assert_status(guest["A"].get("/api/v1/guest-os/rooms/" + fixtures["A"]["token"] + "/requests"),
                      401, "guest logout revoked tasks")
        assert assert_status(guest["B"].get(
            "/api/v1/guest-os/rooms/" + fixtures["B"]["token"]), 200,
            "hotel B unaffected by A logout")["authenticated"] is True

        for h in ("A", "B"):
            data = fixtures[h]
            checked = assert_status(owner[h].post(
                "/api/v1/admin/stays/reservations/" + data["reservation_id"] + "/check-out"),
                200, "hotel checkout")
            assert checked["status"] == "CHECKED_OUT"
            after = assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + data["token"]), 200, "QR after checkout")
            assert after["authenticated"] is False and after["guest"] is None and after["stay"] is None
            assert_status(guest[h].get(
                "/api/v1/guest-os/rooms/" + data["token"] + "/requests"), 401, "revoke after checkout")
        asyncio.run(database_checkout(fixtures))

        # An owner's rotation only revokes its original hotel's QR.
        original = fixtures["A"]["token"]
        rotated = assert_status(owner["A"].post(
            "/api/v1/admin/guest-os/room-qrs/" + str(fixtures["A"]["room_id"]) + "/rotate"),
            201, "rotate QR A")
        assert rotated["token"] != original and rotated["token_display_once"] is True
        assert_status(anonymous.get("/api/v1/guest-os/rooms/" + original), 404, "old QR revoked")
        after_rotation = assert_status(anonymous.get(
            "/api/v1/guest-os/rooms/" + rotated["token"]), 200, "new QR active")
        assert after_rotation["active_stay"] is False and after_rotation["guest"] is None
        still_b = assert_status(anonymous.get(
            "/api/v1/guest-os/rooms/" + fixtures["B"]["token"]), 200, "B QR unchanged")
        assert still_b["qr_valid"] is True
        assert_status(anonymous.get(
            "/api/v1/guest-os/rooms/" + "unknown-valid-length-token-xxxx"), 404, "unknown QR")
        print("PASS: 2 hotels / 1 HTTPS origin / real PostgreSQL / login / booking / QR / PIN / "
              "XFF-resistant throttle / guest requests / isolation both directions / logout / "
              "checkout revocation / QR rotation (synthetic CI ONLY)")
    finally:
        for obj in [*owner.values(), *guest.values(), anonymous, brute]:
            obj.close()


if __name__ == "__main__":
    main()
