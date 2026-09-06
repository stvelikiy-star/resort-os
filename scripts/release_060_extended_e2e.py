import asyncio
import os
import uuid
from datetime import date
from typing import Any

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ["SMOKE_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["SMOKE_OWNER_PASSWORD"]
D0 = date.fromisoformat(os.environ["D0"])
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]


def fail(response: httpx.Response, label: str) -> None:
    try:
        detail: Any = response.json()
    except Exception:
        detail = response.text
    raise AssertionError(f"{label}: HTTP {response.status_code}: {detail}")


def ok(response: httpx.Response, label: str, expected: int | tuple[int, ...] = (200, 201)) -> dict[str, Any]:
    codes = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in codes:
        fail(response, label)
    return response.json() if response.content else {}


async def release_stay() -> dict[str, str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT r.id AS reservation_id,s.id AS stay_id,ra."roomId" AS room_id,room.code AS room_code
               FROM reservations r
               JOIN stays s ON s."reservationId"=r.id AND s.status='ACTIVE'
               JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               JOIN rooms room ON room.id=ra."roomId"
               WHERE r.status='CHECKED_IN' AND COALESCE(r.notes,'') LIKE '%Release 0.60 E2E%'
               ORDER BY r."createdAt" DESC LIMIT 1'''
        )
        assert row, "base release E2E did not leave an active Release 0.60 stay"
        return {key: str(row[key]) for key in row.keys()}
    finally:
        await conn.close()


async def main() -> None:
    context = await release_stay()
    reservation_id = context["reservation_id"]
    stay_id = context["stay_id"]
    room_id = context["room_id"]
    room_code = context["room_code"]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as owner:
        login = ok(
            await owner.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}),
            "owner login",
        )
        assert login["role"] == "OWNER"

        # 1. Dining session transfer must be atomic: old table -> CLEANING, target -> OCCUPIED.
        source_code = f"XFER-{uuid.uuid4().hex[:5].upper()}"
        target_code = f"XFER-{uuid.uuid4().hex[:5].upper()}"
        source = ok(
            await owner.post(
                "/api/v1/kitchen/tables",
                json={"code": source_code, "name": "E2E transfer source", "seats": 4, "notes": "extended release gate"},
            ),
            "create transfer source table",
        )
        target = ok(
            await owner.post(
                "/api/v1/kitchen/tables",
                json={"code": target_code, "name": "E2E transfer target", "seats": 4, "notes": "extended release gate"},
            ),
            "create transfer target table",
        )
        source_id = source["id"]
        target_id = target["id"]
        ok(
            await owner.patch(
                f"/api/v1/dining/floor-layout/tables/{source_id}",
                json={"floor_x": 25.0, "floor_y": 68.0, "zone_label": "E2E transfer", "floor_shape": "RECTANGLE"},
            ),
            "position transfer source",
        )
        ok(
            await owner.patch(
                f"/api/v1/dining/floor-layout/tables/{target_id}",
                json={"floor_x": 45.0, "floor_y": 68.0, "zone_label": "E2E transfer", "floor_shape": "ROUND"},
            ),
            "position transfer target",
        )
        session = ok(
            await owner.post(
                "/api/v1/dining/sessions",
                json={
                    "stay_id": stay_id,
                    "table_id": source_id,
                    "service_date": str(D0),
                    "meal_type": "OTHER",
                    "status": "SEATED",
                },
            ),
            "seat guest for transfer",
        )
        session_id = session["id"]
        moved = ok(
            await owner.post(
                f"/api/v1/dining/sessions/{session_id}/move",
                json={"target_table_id": target_id, "waiter_mode": "CLEAR"},
            ),
            "transactional table transfer",
        )
        assert moved["table_id"] == target_id and moved["waiter_id"] is None
        floor = ok(await owner.get("/api/v1/dining/floor-layout"), "floor after transfer")
        source_after = next(item for item in floor["tables"] if item["id"] == source_id)
        target_after = next(item for item in floor["tables"] if item["id"] == target_id)
        assert source_after["status"] == "CLEANING"
        assert target_after["status"] == "OCCUPIED"
        active_session = next(item for item in floor["sessions"] if item["id"] == session_id)
        assert active_session["table_id"] == target_id and active_session["room_code"] == room_code

        released = ok(
            await owner.patch(f"/api/v1/dining/sessions/{session_id}/status", json={"status": "RELEASED"}),
            "release transferred dining session",
        )
        assert released["status"] == "RELEASED"
        floor_released = ok(await owner.get("/api/v1/dining/floor-layout"), "floor after transferred session release")
        assert next(item for item in floor_released["tables"] if item["id"] == target_id)["status"] == "CLEANING"

        # 2. Guest OS admission is QR + active stay + one-time PIN, never room number alone.
        pin = ok(
            await owner.post(f"/api/v1/admin/guest-access/reservations/{reservation_id}/pin"),
            "reissue Guest OS PIN",
        )
        guest_pin = pin["guest_access_pin"]
        assert guest_pin.isdigit() and len(guest_pin) == 6
        qr = ok(
            await owner.post(f"/api/v1/admin/guest-os/room-qrs/{room_id}/rotate"),
            "rotate/issue Guest OS room QR",
        )
        room_token = qr["token"]

        # 3. Publish one approved item for OTHER. This avoids inventing owner meal times.
        ok(await owner.post("/api/v1/kitchen/menu/bootstrap-draft"), "bootstrap kitchen menu")
        menu = ok(await owner.get("/api/v1/kitchen/menu"), "load kitchen menu")
        assert menu["items"], "kitchen menu is empty"
        menu_item = menu["items"][0]
        ok(
            await owner.patch(
                f"/api/v1/kitchen/menu/{menu_item['id']}",
                json={"is_active": True, "is_draft": False},
            ),
            "approve guest menu item",
        )
        ok(
            await owner.post(
                "/api/v1/dining/menu-day/publish",
                json={"service_date": str(D0), "meal_type": "OTHER", "menu_item_ids": [menu_item["id"]]},
            ),
            "publish hotel-local guest menu",
        )

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as guest:
            before = ok(await guest.get(f"/api/v1/guest-os/rooms/{room_token}"), "Guest OS context before PIN")
            assert before["active_stay"] is True and before["authenticated"] is False
            verified = ok(
                await guest.post(f"/api/v1/guest-os/rooms/{room_token}/verify", json={"pin": guest_pin}),
                "Guest OS PIN verification",
            )
            assert verified["verified"] is True and verified["room_code"] == room_code
            after = ok(await guest.get(f"/api/v1/guest-os/rooms/{room_token}"), "Guest OS context after PIN")
            assert after["authenticated"] is True

            guest_menu = ok(
                await guest.get(f"/api/v1/guest-os/rooms/{room_token}/kitchen/menu"),
                "Guest OS published menu",
            )
            assert guest_menu["delivery"]["enabled"] is True
            assert guest_menu["delivery"]["fee_kgs"] == 200
            selected = next(
                item for item in guest_menu["items"]
                if item["id"] == menu_item["id"] and "OTHER" in item["meal_types"]
            )
            order = ok(
                await guest.post(
                    f"/api/v1/guest-os/rooms/{room_token}/kitchen/orders",
                    json={
                        "guest_count": 2,
                        "meal_type": "OTHER",
                        "delivery_to_room": True,
                        "notes": "Extended release E2E room delivery",
                        "items": [{"menu_item_id": selected["id"], "quantity": 1}],
                    },
                ),
                "Guest OS room-delivery order",
            )
            assert order["delivery_to_room"] is True
            assert order["delivery_fee_kgs"] == 200
            assert order["total_kgs"] == order["subtotal_kgs"] + 200
            assert order["financial_posting"] == "OPEN_FOLIO_CHARGE_NOT_PAYMENT"
            guest_order_id = order["id"]

        # 4. Kitchen can fulfill the room order, while finance remains a folio receivable only.
        for next_status in ["ACCEPTED", "COOKING", "READY", "SERVED"]:
            changed = ok(
                await owner.patch(f"/api/v1/kitchen/orders/{guest_order_id}/status", json={"status": next_status}),
                f"Guest OS order -> {next_status}",
            )
            assert changed["status"] == next_status

        folio = ok(await owner.get(f"/api/v1/admin/folio/reservations/{reservation_id}"), "folio after Guest OS delivery")
        charge = next(
            item for item in folio["charges"]
            if item["source_type"] == "KITCHEN_ORDER" and item["source_id"] == guest_order_id
        )
        assert charge["amount_kgs"] == order["total_kgs"]
        assert folio["totals"]["paid_kgs"] == 777, "Guest OS order must never fabricate payment truth"

        print(
            "Release 0.60 extended E2E PASS:",
            {
                "reservation_id": reservation_id,
                "stay_id": stay_id,
                "room_code": room_code,
                "transfer_from": source_code,
                "transfer_to": target_code,
                "guest_order_id": guest_order_id,
                "delivery_fee_kgs": order["delivery_fee_kgs"],
                "paid_kgs": folio["totals"]["paid_kgs"],
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
