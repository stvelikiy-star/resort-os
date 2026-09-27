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
RECEPTION_USERNAME = os.environ.get("RECEPTION_USERNAME", "admin")
RECEPTION_PASSWORD = os.environ.get("RECEPTION_PASSWORD", "MarinaDemo2026!")
MAID_USERNAME = os.environ.get("MAID_USERNAME", "housemaid")
MAID_PASSWORD = os.environ.get("MAID_PASSWORD", "MarinaDemo2026!")
KITCHEN_USERNAME = os.environ.get("KITCHEN_USERNAME", "kitchen")
KITCHEN_PASSWORD = os.environ.get("KITCHEN_PASSWORD", "MarinaDemo2026!")
WAITER_USERNAME = os.environ.get("WAITER_USERNAME", "waiter")
WAITER_PASSWORD = os.environ.get("WAITER_PASSWORD", "MarinaDemo2026!")
TECHNICIAN_USERNAME = os.environ.get("TECHNICIAN_USERNAME", "technician")
TECHNICIAN_PASSWORD = os.environ.get("TECHNICIAN_PASSWORD", "MarinaDemo2026!")
AGENT_USERNAME = os.environ.get("AGENT_USERNAME", "agent")
AGENT_PASSWORD = os.environ.get("AGENT_PASSWORD", "MarinaDemo2026!")
EXPECTED_GUEST_BASE_URL = os.environ.get("EXPECTED_GUEST_BASE_URL", "").rstrip("/")
EXPECTED_ROOM_COUNT = int(os.environ.get("EXPECTED_ROOM_COUNT", "12"))
EXPECTED_ROOM_TYPE_COUNT = int(os.environ.get("EXPECTED_ROOM_TYPE_COUNT", "3"))
EXPECTED_CLEAN_ROOM_COUNT = int(os.environ.get("EXPECTED_CLEAN_ROOM_COUNT", str(EXPECTED_ROOM_COUNT)))
EXPECTED_BLOCKED_ROOM_COUNT = int(os.environ.get("EXPECTED_BLOCKED_ROOM_COUNT", "0"))
EXPECTED_PUBLIC_AVAILABLE_COUNT = int(os.environ.get("EXPECTED_PUBLIC_AVAILABLE_COUNT", str(EXPECTED_CLEAN_ROOM_COUNT)))
PREPAYMENT_POLICY = os.environ.get(
    "PREPAYMENT_POLICY",
    "FIRST_NIGHT" if PROPERTY_CODE == "AK_BERMET_TEST" else "MANAGER_DECIDES",
).strip().upper()
EXPECTED_ROOM_TYPE_CODES = {
    value.strip()
    for value in os.environ.get("EXPECTED_ROOM_TYPE_CODES", "STANDARD,COMFORT,SUITE").split(",")
    if value.strip()
}


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
    reception = login(RECEPTION_USERNAME, RECEPTION_PASSWORD)

    reception_list = expect(
        reception.get("/api/v1/admin/reception/reservations", params={"limit": 50}),
        200,
        "reception workspace access",
    )
    assert isinstance(reception_list.get("items"), list)
    denied_reception_finance = reception.get(
        "/api/v1/admin/finance/summary",
        params={"from_date": today.isoformat(), "to_date": today.isoformat()},
    )
    assert denied_reception_finance.status_code == 403, denied_reception_finance.text
    denied_reception_pms = reception.get(
        "/api/v1/pms/grid",
        params={"start": today.isoformat(), "end": (today + timedelta(days=2)).isoformat()},
    )
    assert denied_reception_pms.status_code == 403, denied_reception_pms.text

    managed_agent_suffix = uuid.uuid4().hex[:8]
    managed_agent_username = f"agent-{managed_agent_suffix}"
    managed_agent_created = expect(
        owner.post(
            "/api/v1/admin/owner-corrections/agents",
            json={
                "name": f"MARINA Managed Agency {managed_agent_suffix}",
                "contact_name": "MARINA Agent Acceptance",
                "access_username": managed_agent_username,
                "access_password": AGENT_PASSWORD,
            },
        ),
        201,
        "create managed agent access",
    )
    assert managed_agent_created["access_username"] == managed_agent_username

    setup = expect(owner.get("/api/v1/admin/hotel-setup"), 200, "hotel setup")
    assert setup["property"]["code"] == PROPERTY_CODE
    assert setup["summary"]["rooms"] == EXPECTED_ROOM_COUNT, setup["summary"]
    assert setup["summary"]["room_types"] == EXPECTED_ROOM_TYPE_COUNT, setup["summary"]
    assert setup["summary"]["ready"] == EXPECTED_CLEAN_ROOM_COUNT, setup["summary"]
    assert setup["summary"]["blocked"] == EXPECTED_BLOCKED_ROOM_COUNT, setup["summary"]
    if EXPECTED_ROOM_TYPE_CODES:
        assert {item["code"] for item in setup["room_types"]} == EXPECTED_ROOM_TYPE_CODES

    grid = expect(
        owner.get("/api/v1/pms/grid", params={"start": check_in.isoformat(), "end": check_out.isoformat()}),
        200,
        "PMS grid",
    )
    assert len(grid["rooms"]) == EXPECTED_ROOM_COUNT

    public_availability = expect(
        owner.get(
            "/api/v1/booking/check-availability",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 1,
                "children": 0,
            },
        ),
        200,
        "public availability count",
    )
    public_available_count = sum(int(item.get("available_count") or 0) for item in public_availability["results"])
    assert public_available_count == EXPECTED_PUBLIC_AVAILABLE_COUNT, {
        "expected": EXPECTED_PUBLIC_AVAILABLE_COUNT,
        "actual": public_available_count,
        "results": public_availability["results"],
    }
    assert all(item.get("pricing", {}).get("sellable") is True for item in public_availability["results"])

    # Public-site contract: availability -> durable request -> owner CRM -> quote.
    site_check_in = today + timedelta(days=4)
    site_check_out = today + timedelta(days=6)
    site_availability = expect(
        owner.get(
            "/api/v1/booking/check-availability",
            params={
                "check_in": site_check_in.isoformat(),
                "check_out": site_check_out.isoformat(),
                "adults": 1,
                "children": 0,
            },
        ),
        200,
        "site availability contract",
    )
    site_options = [item for item in site_availability["results"] if item.get("pricing", {}).get("sellable")]
    assert site_options, "Public site must have at least one sellable AK BERMET/MARINA option"
    site_option = site_options[0]
    public = httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=True)
    site_suffix = uuid.uuid4().hex[:8]
    site_request = expect(
        public.post(
            "/api/v1/booking/requests",
            json={
                "guest_name": "MARINA Website Test",
                "phone": "+996755" + site_suffix[:6],
                "email": f"marina-site-{site_suffix}@example.test",
                "check_in": site_check_in.isoformat(),
                "check_out": site_check_out.isoformat(),
                "adults": 1,
                "children": 0,
                "room_type_code": site_option["room_type_code"],
                "source": "AK_BERMET_SITE_CI" if PROPERTY_CODE == "AK_BERMET_TEST" else "MARINA_SITE_CI",
                "notes": "public site -> MARINA CRM acceptance",
            },
        ),
        201,
        "public site booking request",
    )
    assert site_request["status"] == "NEW" and site_request["is_reservation"] is False
    site_request_id = site_request["id"]

    crm_requests = expect(
        owner.get("/api/v1/admin/booking/requests", params={"limit": 200}),
        200,
        "owner CRM requests",
    )
    crm_item = next((item for item in crm_requests["items"] if item["id"] == site_request_id), None)
    assert crm_item, "Public site request must appear in MARINA CRM"
    assert crm_item["status"] == "NEW"
    assert crm_item["source"] == ("AK_BERMET_SITE_CI" if PROPERTY_CODE == "AK_BERMET_TEST" else "MARINA_SITE_CI")

    quoted_site_request = expect(
        owner.post(
            f"/api/v1/admin/booking/requests/{site_request_id}/quote",
            json={"room_type_code": site_option["room_type_code"]},
        ),
        200,
        "owner quote for public site request",
    )
    assert int(quoted_site_request["quoted_total_kgs"] or 0) > 0
    if PREPAYMENT_POLICY == "FIRST_NIGHT":
        assert quoted_site_request["status"] == "AWAITING_PREPAYMENT"
        first_night_availability = expect(
            owner.get(
                "/api/v1/booking/check-availability",
                params={
                    "check_in": site_check_in.isoformat(),
                    "check_out": (site_check_in + timedelta(days=1)).isoformat(),
                    "adults": 1,
                    "children": 0,
                    "room_type_code": site_option["room_type_code"],
                },
            ),
            200,
            "first-night prepayment reference",
        )
        first_night_options = [
            item for item in first_night_availability["results"]
            if item.get("room_type_code") == site_option["room_type_code"] and item.get("pricing", {}).get("sellable")
        ]
        assert len(first_night_options) == 1, first_night_availability
        first_night_kgs = int(first_night_options[0]["pricing"]["total_kgs"])
        assert int(quoted_site_request["required_prepayment_kgs"] or 0) == first_night_kgs, {
            "required": quoted_site_request["required_prepayment_kgs"],
            "first_night": first_night_kgs,
        }
        assert quoted_site_request["prepayment_decided_by_manager"] is False
    else:
        assert quoted_site_request["status"] == "QUOTED"
        assert quoted_site_request["required_prepayment_kgs"] is None
        assert quoted_site_request["prepayment_decided_by_manager"] is True
    public.close()

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

    agent = login(managed_agent_username, AGENT_PASSWORD)
    agent_grid = expect(
        agent.get("/api/v1/pms/grid", params={"start": check_in.isoformat(), "end": check_out.isoformat()}),
        200,
        "agent PMS grid",
    )
    foreign_blocks = [block for room in agent_grid["rooms"] for block in room["blocks"]]
    assert any(
        block.get("reservation_id") is None
        and block.get("guest_name") is None
        and block.get("guest_phone") is None
        for block in foreign_blocks
    ), foreign_blocks

    denied_finance = agent.get("/api/v1/admin/reception/reservations", params={"limit": 50})
    assert denied_finance.status_code == 403, denied_finance.text

    agent_chosen = None
    agent_preview = None
    for room in agent_grid["rooms"]:
        if room["id"] == chosen["id"]:
            continue
        probe = agent.post(
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
            agent_chosen = room
            agent_preview = probe.json()
            break
    assert agent_chosen and agent_preview, "No sellable room for linked agent"
    assert agent_preview["pricing"]["source"] == "CORE_RATE"
    assert agent_preview["pricing"]["discount_percent"] == 0
    assert agent_preview["agent"]["name"]

    forbidden_override = agent.post(
        "/api/v1/admin/pms/reservations/new/preview",
        json={
            "room_id": agent_chosen["id"],
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": 1,
            "children": 0,
            "manager_total_kgs": 1,
        },
    )
    assert forbidden_override.status_code == 403, forbidden_override.text

    agent_suffix = uuid.uuid4().hex[:8]
    agent_committed = expect(
        agent.post(
            "/api/v1/admin/pms/reservations/new/commit",
            json={
                "room_id": agent_chosen["id"],
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 1,
                "children": 0,
                "guest_name": "MARINA Agent Test",
                "phone": "+996711" + agent_suffix[:6],
                "email": f"marina-agent-{agent_suffix}@example.test",
                "expected_total_kgs": agent_preview["pricing"]["total_kgs"],
                "expected_pricing_source": "CORE_RATE",
                "notes": "MARINA SMART agent booking acceptance",
            },
        ),
        201,
        "agent reservation commit",
    )
    assert agent_committed["agent_id"]
    assert agent_committed["payment_terms"] == "AGENT_CORE_RATE"
    assert agent_committed["discount_percent"] == 0

    agent_grid_after = expect(
        agent.get("/api/v1/pms/grid", params={"start": check_in.isoformat(), "end": check_out.isoformat()}),
        200,
        "agent PMS grid after own booking",
    )
    own_blocks = [
        block
        for room in agent_grid_after["rooms"]
        for block in room["blocks"]
        if block.get("booking_number") == agent_committed["booking_number"]
    ]
    assert len(own_blocks) == 1, own_blocks
    assert own_blocks[0]["guest_name"] == "MARINA Agent Test"
    assert own_blocks[0]["guest_phone"]

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
        201,
        "room QR",
    )
    token = issued["token"]
    assert issued["token_display_once"] is True
    if EXPECTED_GUEST_BASE_URL:
        assert issued["public_url"].startswith(EXPECTED_GUEST_BASE_URL + "/g/"), issued["public_url"]
    assert "3korony.com" not in issued["public_url"], issued["public_url"]

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

    waiter = login(WAITER_USERNAME, WAITER_PASSWORD)
    waiter_floor = expect(waiter.get("/api/v1/dining/floor"), 200, "Waiter dining floor access")
    assert isinstance(waiter_floor, dict)

    technician = login(TECHNICIAN_USERNAME, TECHNICIAN_PASSWORD)
    technician_tasks = expect(technician.get("/api/v1/ops/tasks", params={"limit": 50}), 200, "Technician tasks access")
    assert isinstance(technician_tasks.get("items"), list)

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
    assert report["kpi"]["room_count"] == EXPECTED_ROOM_COUNT

    guest.close()
    agent.close()
    reception.close()
    technician.close()
    waiter.close()
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
            "reception_rbac": "PASS",
            "public_site_to_crm": "PASS",
            "prepayment_policy": PREPAYMENT_POLICY,
        }
    )


if __name__ == "__main__":
    main()
