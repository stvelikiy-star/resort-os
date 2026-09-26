#!/usr/bin/env python3
import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "MARINA_TEST")
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "marina")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "MarinaDemo2026!")
MAID_USERNAME = os.environ.get("MAID_USERNAME", "housemaid")
MAID_PASSWORD = os.environ.get("MAID_PASSWORD", "MarinaDemo2026!")
KITCHEN_USERNAME = os.environ.get("KITCHEN_USERNAME", "kitchen")
KITCHEN_PASSWORD = os.environ.get("KITCHEN_PASSWORD", "MarinaDemo2026!")


def expect(response: httpx.Response, status: int | tuple[int, ...], label: str):
    allowed = (status,) if isinstance(status, int) else status
    if response.status_code not in allowed:
        raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text}")
    if not response.content:
        return {}
    return response.json()


async def local_today() -> date:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        value = await conn.fetchval(
            "SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code=$1",
            PROPERTY_CODE,
        )
        assert value, "MARINA test property missing"
        return value
    finally:
        await conn.close()


async def guest_id_for_reservation(reservation_id: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        value = await conn.fetchval(
            'SELECT "primaryGuestId" FROM reservations WHERE id=$1',
            uuid.UUID(reservation_id),
        )
        assert value
        return str(value)
    finally:
        await conn.close()


def login(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=True)
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    body = expect(response, 200, f"login {username}")
    assert body["username"] == username
    return client


def main() -> None:
    today = asyncio.run(local_today())
    check_in = today - timedelta(days=1)
    check_out = today + timedelta(days=2)

    owner = login(OWNER_USERNAME, OWNER_PASSWORD)
    setup = expect(owner.get("/api/v1/admin/hotel-setup"), 200, "hotel setup")
    assert setup["property"]["code"] == PROPERTY_CODE
    assert setup["summary"]["rooms"] == 12, setup["summary"]
    assert setup["summary"]["room_types"] == 3, setup["summary"]
    assert {item["code"] for item in setup["room_types"]} == {"STANDARD", "COMFORT", "SUITE"}

    grid = expect(
        owner.get("/api/v1/pms/grid", params={"start": check_in.isoformat(), "end": check_out.isoformat()}),
        200,
        "PMS grid",
    )
    assert len(grid["rooms"]) == 12

    chosen = None
    preview = None
    for room in grid["rooms"]:
        probe = owner.post(
            "/api/v1/admin/pms/reservations/new/preview",
            json={
                "room_id": room["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 1,
                "children": 0,
            },
        )
        if probe.status_code == 200 and probe.json().get("can_commit"):
            chosen = room
            preview = probe.json()
            break
    assert chosen and preview, "No sellable MARINA test room"

    suffix = uuid.uuid4().hex[:8]
    committed = expect(
        owner.post(
            "/api/v1/admin/pms/reservations/new/commit",
            json={
                "room_id": chosen["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 1,
                "children": 0,
                "guest_name": "MARINA Client Test",
                "phone": "+996700" + suffix[:6],
                "email": f"marina-client-{suffix}@example.test",
                "expected_total_kgs": preview["pricing"]["total_kgs"],
                "expected_pricing_source": preview["pricing"]["source"],
                "notes": "MARINA SMART compact client-cycle acceptance",
            },
        ),
        201,
        "reservation commit",
    )
    assert committed["status"] == "GUARANTEED"
    assert committed["payment_created"] is False
    reservation_id = committed["reservation_id"]

    folio = expect(
        owner.get(f"/api/v1/admin/folio/reservations/{reservation_id}"),
        200,
        "reservation folio",
    )
    assert folio["totals"]["accommodation_kgs"] == committed["total_kgs"]
    assert folio["totals"]["paid_kgs"] == 0

    reception = expect(
        owner.get("/api/v1/admin/reception/reservations", params={"limit": 500}),
        200,
        "reception list",
    )
    assert any(item["id"] == reservation_id for item in reception["items"])

    checkin = expect(
        owner.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-in"),
        200,
        "check-in",
    )
    assert checkin["status"] == "CHECKED_IN"
    assert checkin["room_code"] == chosen["code"]
    stay_id = checkin["stay_id"]
    pin = checkin["guest_access_pin"]
    assert pin.isdigit() and len(pin) == 6

    issued = expect(
        owner.post(f"/api/v1/admin/guest-os/room-qrs/{chosen['id']}/issue"),
        200,
        "room QR",
    )
    token = issued["token"]
    assert issued["token_display_once"] is True

    guest = httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=True)
    verified = expect(
        guest.post(f"/api/v1/guest-os/rooms/{token}/verify", json={"pin": pin}),
        200,
        "guest PIN verification",
    )
    assert verified["verified"] is True

    request = expect(
        guest.post(
            f"/api/v1/guest-os/rooms/{token}/requests",
            json={"request_code": "TOWELS", "description": "MARINA client cycle towels"},
        ),
        201,
        "guest service request",
    )
    request_id = request["id"]

    maid = login(MAID_USERNAME, MAID_PASSWORD)
    maid_queue = expect(
        maid.get("/api/v1/ops/guest-requests", params={"status": "ACTIVE", "limit": 300}),
        200,
        "housemaid queue",
    )
    assert any(item["id"] == request_id for item in maid_queue["items"])
    claimed = expect(maid.post(f"/api/v1/ops/guest-requests/{request_id}/claim"), 200, "housemaid claim")
    assert claimed["status"] == "IN_PROGRESS"
    completed = expect(maid.post(f"/api/v1/ops/guest-requests/{request_id}/complete"), 200, "housemaid complete")
    assert completed["status"] == "DONE"

    guest_id = asyncio.run(guest_id_for_reservation(reservation_id))
    crm = expect(owner.get(f"/api/v1/admin/guest-crm/{guest_id}"), 200, "guest CRM")
    assert crm["guest"]["first_name"] == "MARINA Client Test"
    assert any(item["id"] == stay_id for item in crm["stays"])
    assert any(item["id"] == request_id for stay in crm["stays"] for item in stay["requests"])

    kitchen = login(KITCHEN_USERNAME, KITCHEN_PASSWORD)
    kitchen_menu = expect(kitchen.get("/api/v1/kitchen/menu"), 200, "Kitchen menu access")
    assert isinstance(kitchen_menu.get("items"), list)
    denied_pms = kitchen.get("/api/v1/pms/grid", params={"start": today.isoformat(), "end": check_out.isoformat()})
    assert denied_pms.status_code == 403, denied_pms.text

    checkout = expect(
        owner.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-out"),
        200,
        "check-out",
    )
    assert checkout["status"] == "CHECKED_OUT"

    setup_after = expect(owner.get("/api/v1/admin/hotel-setup"), 200, "hotel setup after checkout")
    room_after = next(item for item in setup_after["rooms"] if item["id"] == chosen["id"])
    assert room_after["operational_state"] == "DIRTY"

    departure_tasks = expect(
        maid.get("/api/v1/ops/tasks", params={"type": "HOUSEKEEPING", "limit": 250}),
        200,
        "departure housekeeping task",
    )
    assert any(item.get("room_id") == chosen["id"] and item["status"] in {"OPEN", "IN_PROGRESS", "IN_INSPECTION"} for item in departure_tasks["items"])

    report = expect(
        owner.get(
            "/api/v1/admin/reports/overview",
            params={"from_date": (today - timedelta(days=7)).isoformat(), "to_date": (today + timedelta(days=30)).isoformat()},
        ),
        200,
        "owner report",
    )
    assert report["kpi"]["room_count"] == 12

    guest.close()
    kitchen.close()
    maid.close()
    owner.close()

    print("MARINA_CLIENT_CYCLE_E2E_PASS")
    print(
        {
            "property": PROPERTY_CODE,
            "room": chosen["code"],
            "reservation_id": reservation_id,
            "stay_id": stay_id,
            "guest_request_id": request_id,
            "payment_profile": "NO_PAYMENTS",
        }
    )


if __name__ == "__main__":
    main()
