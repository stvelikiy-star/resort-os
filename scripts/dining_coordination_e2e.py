#!/usr/bin/env python3
"""Synthetic E2E for restaurant reservations vs live dining-table sessions.

Requires the isolated release/staging database after release_060_e2e.py has left
its synthetic checked-in Stay active. No production or real guest data is used.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ["SMOKE_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["SMOKE_OWNER_PASSWORD"]
D0 = date.fromisoformat(os.environ["D0"])
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]


def ok(response: httpx.Response, label: str, expected: int | tuple[int, ...] = (200, 201)) -> dict[str, Any]:
    codes = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in codes:
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        raise AssertionError(f"{label}: HTTP {response.status_code}: {detail}")
    return response.json() if response.content else {}


async def release_stay() -> dict[str, str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT r.id AS reservation_id,s.id AS stay_id,room.code AS room_code
               FROM reservations r
               JOIN stays s ON s."reservationId"=r.id AND s.status='ACTIVE'
               JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               JOIN rooms room ON room.id=ra."roomId"
               WHERE r.status='CHECKED_IN' AND COALESCE(r.notes,'') LIKE '%Release 0.60 E2E%'
               ORDER BY r."createdAt" DESC LIMIT 1'''
        )
        assert row, "release E2E active stay is required"
        return {key: str(row[key]) for key in row.keys()}
    finally:
        await conn.close()


async def create_table(client: httpx.AsyncClient, label: str) -> dict[str, Any]:
    code = f"SYNC-{uuid.uuid4().hex[:6].upper()}"
    return ok(
        await client.post(
            "/api/v1/kitchen/tables",
            json={"code": code, "name": label, "seats": 4, "notes": "Dining coordination E2E"},
        ),
        f"create {label}",
    )


async def ensure_orderable_menu_item(client: httpx.AsyncClient) -> dict[str, Any]:
    menu = ok(await client.get("/api/v1/kitchen/menu"), "load kitchen menu")
    approved = [item for item in menu.get("items", []) if item.get("is_active") and not item.get("is_draft")]
    if approved:
        return approved[0]

    ok(await client.post("/api/v1/kitchen/menu/bootstrap-draft"), "bootstrap synthetic kitchen menu")
    menu = ok(await client.get("/api/v1/kitchen/menu"), "reload kitchen menu")
    candidates = [item for item in menu.get("items", []) if item.get("is_active")]
    assert candidates, "synthetic kitchen menu item is required"
    chosen = candidates[0]
    updated = ok(
        await client.patch(
            f"/api/v1/kitchen/menu/{chosen['id']}",
            json={"is_active": True, "is_draft": False},
        ),
        "approve synthetic kitchen menu item",
    )
    return updated


async def main() -> None:
    context = await release_stay()
    stay_id = context["stay_id"]
    reservation_id = context["reservation_id"]
    now = datetime.now(timezone.utc)
    starts_at = (now - timedelta(minutes=15)).isoformat()
    ends_at = (now + timedelta(minutes=90)).isoformat()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as owner:
        login = ok(
            await owner.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}),
            "owner login",
        )
        assert login["role"] == "OWNER"

        # A current reservation for another/non-hotel guest owns its window and
        # must block an unrelated live Stay from being seated on that table.
        blocked_table = await create_table(owner, "Coordination blocked table")
        external_reservation = ok(
            await owner.post(
                "/api/v1/dining/table-reservations",
                json={
                    "table_id": blocked_table["id"],
                    "guest_name": "External synthetic guest",
                    "party_size": 2,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "notes": "Current external reservation conflict",
                },
            ),
            "create current external table reservation",
        )
        blocked_session = await owner.post(
            "/api/v1/dining/sessions",
            json={
                "stay_id": stay_id,
                "table_id": blocked_table["id"],
                "service_date": str(D0),
                "meal_type": "OTHER",
                "status": "SEATED",
            },
        )
        assert blocked_session.status_code == 409, blocked_session.text
        assert blocked_session.json().get("detail", {}).get("code") == "DINING_TABLE_CURRENT_RESERVATION_CONFLICT"
        ok(
            await owner.patch(
                f"/api/v1/dining/table-reservations/{external_reservation['id']}",
                json={"status": "CANCELLED"},
            ),
            "cancel external synthetic reservation",
        )
        reopen_terminal = await owner.patch(
            f"/api/v1/dining/table-reservations/{external_reservation['id']}",
            json={"status": "BOOKED"},
        )
        assert reopen_terminal.status_code == 409, reopen_terminal.text
        assert reopen_terminal.json().get("detail", {}).get("code") == "DINING_RESERVATION_INVALID_TRANSITION"

        # A reservation linked to the same Stay is synchronized with live seating.
        source_table = await create_table(owner, "Coordination linked source")
        target_table = await create_table(owner, "Coordination linked target")
        linked_reservation = ok(
            await owner.post(
                "/api/v1/dining/table-reservations",
                json={
                    "table_id": source_table["id"],
                    "guest_name": "Release synthetic hotel guest",
                    "party_size": 2,
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "stay_id": stay_id,
                    "reservation_id": reservation_id,
                    "notes": "Stay-linked reservation synchronization",
                },
            ),
            "create stay-linked table reservation",
        )
        assert linked_reservation["status"] == "BOOKED"

        session = ok(
            await owner.post(
                "/api/v1/dining/sessions",
                json={
                    "stay_id": stay_id,
                    "table_id": source_table["id"],
                    "service_date": str(D0),
                    "meal_type": "OTHER",
                    "status": "SEATED",
                },
            ),
            "seat linked hotel guest",
        )
        session_id = session["id"]

        backward = await owner.patch(
            f"/api/v1/dining/sessions/{session_id}/status",
            json={"status": "WAITING"},
        )
        assert backward.status_code == 409, backward.text
        assert backward.json().get("detail", {}).get("code") == "DINING_SESSION_INVALID_TRANSITION"

        reservations = ok(
            await owner.get(f"/api/v1/dining/table-reservations?service_date={D0.isoformat()}"),
            "list table reservations after seating",
        )
        linked_after_seat = next(item for item in reservations["items"] if item["id"] == linked_reservation["id"])
        assert linked_after_seat["status"] == "SEATED"
        assert linked_after_seat["table_id"] == source_table["id"]
        assert linked_after_seat["stay_id"] == stay_id
        assert linked_after_seat["reservation_id"] == reservation_id

        # Closing the final kitchen order must not free a table while a live
        # dining session still owns it.
        menu_item = await ensure_orderable_menu_item(owner)
        order = ok(
            await owner.post(
                "/api/v1/kitchen/orders",
                json={
                    "source": "TABLE",
                    "table_id": source_table["id"],
                    "stay_id": stay_id,
                    "guest_count": session["party_size"],
                    "meal_type": "OTHER",
                    "notes": "Dining coordination occupancy regression",
                    "items": [{"menu_item_id": menu_item["id"], "quantity": 1}],
                },
            ),
            "create coordinated table order",
        )
        for next_status in ("ACCEPTED", "COOKING", "READY", "SERVED"):
            ok(
                await owner.patch(
                    f"/api/v1/kitchen/orders/{order['id']}/status",
                    json={"status": next_status},
                ),
                f"advance coordinated order to {next_status}",
            )
        floor_after_serve = ok(await owner.get("/api/v1/dining/floor-layout"), "floor after final table order served")
        source_after_serve = next(item for item in floor_after_serve["tables"] if item["id"] == source_table["id"])
        assert source_after_serve["status"] == "OCCUPIED", source_after_serve

        # Reservation lifecycle cannot independently close while its matching
        # live session is still authoritative.
        premature_close = await owner.patch(
            f"/api/v1/dining/table-reservations/{linked_reservation['id']}",
            json={"status": "COMPLETED"},
        )
        assert premature_close.status_code == 409, premature_close.text
        assert premature_close.json().get("detail", {}).get("code") == "DINING_RESERVATION_HAS_ACTIVE_SESSION"

        same_table = await owner.post(
            f"/api/v1/dining/sessions/{session_id}/move",
            json={"target_table_id": source_table["id"], "waiter_mode": "CLEAR"},
        )
        assert same_table.status_code == 409
        assert same_table.json().get("detail", {}).get("code") == "DINING_MOVE_SAME_TABLE"

        ok(
            await owner.patch(f"/api/v1/kitchen/tables/{target_table['id']}", json={"status": "CLEANING"}),
            "mark linked target cleaning",
        )
        unavailable = await owner.post(
            f"/api/v1/dining/sessions/{session_id}/move",
            json={"target_table_id": target_table["id"], "waiter_mode": "CLEAR"},
        )
        assert unavailable.status_code == 409
        assert unavailable.json().get("detail", {}).get("code") == "DINING_TARGET_TABLE_NOT_AVAILABLE"
        ok(
            await owner.patch(f"/api/v1/kitchen/tables/{target_table['id']}", json={"status": "AVAILABLE"}),
            "restore linked target available",
        )

        moved = ok(
            await owner.post(
                f"/api/v1/dining/sessions/{session_id}/move",
                json={"target_table_id": target_table["id"], "waiter_mode": "CLEAR"},
            ),
            "move live session with linked table reservation",
        )
        assert moved["table_id"] == target_table["id"]

        reservations_after_move = ok(
            await owner.get(f"/api/v1/dining/table-reservations?service_date={D0.isoformat()}"),
            "list table reservations after live move",
        )
        linked_after_move = next(item for item in reservations_after_move["items"] if item["id"] == linked_reservation["id"])
        assert linked_after_move["table_id"] == target_table["id"]
        assert linked_after_move["status"] == "SEATED"

        released = ok(
            await owner.patch(f"/api/v1/dining/sessions/{session_id}/status", json={"status": "RELEASED"}),
            "release linked dining session",
        )
        assert released["status"] == "RELEASED"

        reservations_after_release = ok(
            await owner.get(f"/api/v1/dining/table-reservations?service_date={D0.isoformat()}"),
            "list table reservations after release",
        )
        linked_after_release = next(item for item in reservations_after_release["items"] if item["id"] == linked_reservation["id"])
        assert linked_after_release["status"] == "COMPLETED"
        assert linked_after_release["table_id"] == target_table["id"]

        floor = ok(await owner.get("/api/v1/dining/floor-layout"), "floor after coordinated release")
        source_state = next(item for item in floor["tables"] if item["id"] == source_table["id"])["status"]
        target_state = next(item for item in floor["tables"] if item["id"] == target_table["id"])["status"]
        assert source_state == "CLEANING"
        assert target_state == "CLEANING"

        closed_session_mutation = await owner.patch(
            f"/api/v1/dining/sessions/{session_id}/status",
            json={"status": "SEATED"},
        )
        assert closed_session_mutation.status_code == 409, closed_session_mutation.text
        assert closed_session_mutation.json().get("detail", {}).get("code") == "DINING_SESSION_INVALID_TRANSITION"

        print(
            "Dining coordination E2E PASS:",
            {
                "stay_id": stay_id,
                "blocked_reservation_id": external_reservation["id"],
                "linked_reservation_id": linked_reservation["id"],
                "session_id": session_id,
                "order_id": order["id"],
                "moved_to_table_id": target_table["id"],
                "final_reservation_status": linked_after_release["status"],
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
