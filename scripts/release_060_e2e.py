import asyncio
import base64
import os
import uuid
from datetime import date
from typing import Any

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ.get("SMOKE_OWNER_USERNAME", os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner"))
OWNER_PASSWORD = os.environ.get("SMOKE_OWNER_PASSWORD", os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Only-Strong-Password-2026"))
D0 = date.fromisoformat(os.environ["D0"])
D2 = date.fromisoformat(os.environ["D2"])
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]

# Valid 1x1 PNG. CMS verifies MIME + magic bytes; the public endpoint must return
# the exact bytes after publish.
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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
    if not response.content:
        return {}
    return response.json()


async def set_reservation_room_clean(reservation_id: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        room_id = await conn.fetchval(
            '''SELECT "roomId" FROM inventory_blocks
               WHERE "reservationId"=$1 AND active=true AND "blockType"='RESERVATION'
               ORDER BY "startDate" LIMIT 1''',
            uuid.UUID(reservation_id),
        )
        assert room_id, "reservation room block missing"
        await conn.execute(
            '''UPDATE rooms SET "operationalState"='CLEAN',"updatedAt"=now() WHERE id=$1''', room_id,
        )
    finally:
        await conn.close()


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as client:
        # 1. Auth / owner boundary.
        login = ok(
            await client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}),
            "owner login",
        )
        assert login["role"] == "OWNER"

        # 2. CMS Media: upload -> draft (invisible) -> publish -> public immutable asset.
        media = ok(
            await client.post(
                "/api/v1/admin/site/media",
                content=TINY_PNG,
                headers={"content-type": "image/png", "x-filename": "release-060.png", "x-alt-text": "Release 0.60 hero"},
            ),
            "media upload",
        )
        asset = media["asset"]
        asset_id = asset["id"]
        before_config = ok(await client.get("/api/v1/site/media-config"), "media public config before")
        before_hero = (before_config.get("slots") or {}).get("HERO")

        draft = ok(
            await client.put(
                "/api/v1/admin/site/media/slots/HERO/draft",
                json={"asset_id": asset_id, "alt_text": "Тестовый главный экран"},
            ),
            "save media draft",
        )
        assert draft["dirty"] is True
        draft_config = ok(await client.get("/api/v1/site/media-config"), "media config after draft")
        assert (draft_config.get("slots") or {}).get("HERO") == before_hero, "draft leaked to public media config"

        published = ok(await client.post("/api/v1/admin/site/media/slots/HERO/publish"), "publish media slot")
        assert published["dirty"] is False
        public_config = ok(await client.get("/api/v1/site/media-config"), "media public config after publish")
        assert public_config["slots"]["HERO"]["asset_id"] == asset_id
        media_bytes = await client.get(f"/api/v1/site/media/{asset_id}")
        assert media_bytes.status_code == 200 and media_bytes.content == TINY_PNG
        assert media_bytes.headers.get("content-type", "").startswith("image/png")
        archive_in_use = await client.post(f"/api/v1/admin/site/media/{asset_id}/archive")
        assert archive_in_use.status_code == 409, "published media must not be archivable"

        # 3. Atomic group booking provides a real reservation for the rest of E2E.
        availability = ok(
            await client.post(
                "/api/v1/admin/pms/groups/availability",
                json={"check_in": str(D0), "check_out": str(D2), "adults_per_room": 2, "children_per_room": 0},
            ),
            "group availability",
        )
        free_rooms = [item for item in availability["items"] if item["available"]]
        assert free_rooms, "no free rooms available for release E2E"
        chosen = free_rooms[: min(2, len(free_rooms))]
        group = ok(
            await client.post(
                "/api/v1/admin/pms/groups",
                json={
                    "name": "Release 0.60 E2E",
                    "contact_name": "Release Test Guest",
                    "contact_phone": "+996700060060",
                    "contact_email": "release060@example.test",
                    "check_in": str(D0),
                    "check_out": str(D2),
                    "rooms": [
                        {
                            "room_id": item["room_id"],
                            "adults": 2,
                            "children": 0,
                            "manager_total_kgs": 6000 + index * 100,
                        }
                        for index, item in enumerate(chosen)
                    ],
                    "notes": "Automated release gate",
                },
            ),
            "atomic group commit",
        )
        assert group["atomic"] is True and group["room_count"] == len(chosen)
        reservation_id = group["rooms"][0]["reservation_id"]
        room_code = group["rooms"][0]["room_code"]

        # 4. Folio separates receivables from actual payments.
        folio0 = ok(await client.get(f"/api/v1/admin/folio/reservations/{reservation_id}"), "initial folio")
        assert folio0["totals"]["extras_kgs"] == 0
        accommodation_total = folio0["totals"]["accommodation_kgs"]
        manual_charge = ok(
            await client.post(
                f"/api/v1/admin/folio/reservations/{reservation_id}/charges",
                json={"code": "E2E_SERVICE", "description": "Release E2E service", "amount_kgs": 777, "service_date": str(D0)},
            ),
            "manual folio charge",
        )
        assert manual_charge["folio"]["totals"]["extras_kgs"] == 777
        payment = ok(
            await client.post(
                f"/api/v1/admin/booking/reservations/{reservation_id}/payments",
                json={
                    "amount_kgs": 777,
                    "method": "CASH",
                    "external_ref": f"release060-{reservation_id[:8]}",
                    "note": "Release E2E cash",
                    "idempotency_key": f"release060-payment-{reservation_id}",
                },
            ),
            "folio payment fact",
        )
        assert payment["finance"]["paid_kgs"] == 777
        folio1 = ok(await client.get(f"/api/v1/admin/folio/reservations/{reservation_id}"), "folio after payment")
        assert folio1["totals"]["grand_total_kgs"] == accommodation_total + 777
        assert folio1["totals"]["paid_kgs"] == 777

        # 5. Real check-in creates Stay -> Dining entitlement.
        await set_reservation_room_clean(reservation_id)
        checkin = ok(
            await client.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-in"),
            "group member check-in",
        )
        assert checkin["status"] == "CHECKED_IN" and checkin["room_code"] == room_code
        stay_id = checkin["stay_id"]

        entitlement = ok(
            await client.put(
                f"/api/v1/dining/stays/{stay_id}/meal-plan",
                json={
                    "from_date": str(D0),
                    "through_date": str(D0),
                    "meals": ["BREAKFAST"],
                    "adult_portions": 2,
                    "child_portions": 0,
                    "notes": "E2E breakfast",
                    "replace_range": True,
                },
            ),
            "dining entitlement",
        )
        assert entitlement["updated_items"] == 1
        production = ok(
            await client.get(f"/api/v1/dining/production?from_date={D0}&through_date={D0}"),
            "chef production",
        )
        breakfast = next(meal for day in production["days"] for meal in day["meals"] if meal["meal_type"] == "BREAKFAST")
        assert breakfast["adult_portions"] >= 2
        assert any(guest["stay_id"] == stay_id for guest in breakfast["guests"])

        # 6. Visual Dining Floor + Stay-linked seating.
        table_code = f"E2E-{uuid.uuid4().hex[:5].upper()}"
        table = ok(
            await client.post(
                "/api/v1/kitchen/tables",
                json={"code": table_code, "name": "Release E2E table", "seats": 4, "notes": "release gate"},
            ),
            "create dining table",
        )
        table_id = table["id"]
        layout = ok(
            await client.patch(
                f"/api/v1/dining/floor-layout/tables/{table_id}",
                json={"floor_x": 37.5, "floor_y": 42.0, "zone_label": "E2E зал", "floor_shape": "RECTANGLE"},
            ),
            "save floor position",
        )
        assert layout["zone_label"] == "E2E зал" and layout["floor_shape"] == "RECTANGLE"
        assert abs(layout["floor_x"] - 37.5) < 0.01

        session = ok(
            await client.post(
                "/api/v1/dining/sessions",
                json={
                    "stay_id": stay_id,
                    "table_id": table_id,
                    "service_date": str(D0),
                    "meal_type": "BREAKFAST",
                    "status": "SEATED",
                },
            ),
            "seat checked-in guest",
        )
        session_id = session["id"]
        assert session["room_code"] == room_code and session["status"] == "SEATED"
        floor = ok(await client.get("/api/v1/dining/floor-layout"), "live floor")
        floor_table = next(item for item in floor["tables"] if item["id"] == table_id)
        floor_session = next(item for item in floor["sessions"] if item["id"] == session_id)
        assert floor_table["status"] == "OCCUPIED"
        assert floor_session["stay_id"] == stay_id and floor_session["room_code"] == room_code

        # 7. Kitchen lifecycle on an occupied table and folio posting.
        ok(await client.post("/api/v1/kitchen/menu/bootstrap-draft"), "bootstrap kitchen menu")
        menu = ok(await client.get("/api/v1/kitchen/menu"), "kitchen menu")
        assert menu["items"], "kitchen menu bootstrap returned no items"
        menu_item = menu["items"][0]
        ok(
            await client.patch(
                f"/api/v1/kitchen/menu/{menu_item['id']}",
                json={"is_active": True, "is_draft": False},
            ),
            "approve kitchen item",
        )
        order = ok(
            await client.post(
                "/api/v1/kitchen/orders",
                json={
                    "source": "TABLE",
                    "table_id": table_id,
                    "stay_id": stay_id,
                    "guest_count": 2,
                    "meal_type": "BREAKFAST",
                    "notes": "Release E2E order",
                    "items": [{"menu_item_id": menu_item["id"], "quantity": 2}],
                },
            ),
            "create table kitchen order",
        )
        order_id = order["id"]
        posted = ok(await client.post(f"/api/v1/admin/folio/kitchen-orders/{order_id}/post"), "post kitchen order to folio")
        assert posted["payment_created"] is False
        for next_status in ["ACCEPTED", "COOKING", "READY", "SERVED"]:
            changed = ok(
                await client.patch(f"/api/v1/kitchen/orders/{order_id}/status", json={"status": next_status}),
                f"kitchen order -> {next_status}",
            )
            assert changed["status"] == next_status

        # The DB guard must keep the table occupied while Dining Session is active.
        floor_after_served = ok(await client.get("/api/v1/dining/floor-layout"), "floor after served order")
        guarded_table = next(item for item in floor_after_served["tables"] if item["id"] == table_id)
        assert guarded_table["status"] == "OCCUPIED", "served order incorrectly freed an active guest table"

        folio2 = ok(await client.get(f"/api/v1/admin/folio/reservations/{reservation_id}"), "folio after restaurant")
        assert any(charge["source_type"] == "KITCHEN_ORDER" and charge["source_id"] == order_id for charge in folio2["charges"])
        assert folio2["totals"]["extras_kgs"] > 777

        # 8. Releasing seating, not serving food, is what moves the table to cleaning.
        released = ok(
            await client.patch(f"/api/v1/dining/sessions/{session_id}/status", json={"status": "RELEASED"}),
            "release dining session",
        )
        assert released["status"] == "RELEASED"
        floor_released = ok(await client.get("/api/v1/dining/floor-layout"), "floor after release")
        released_table = next(item for item in floor_released["tables"] if item["id"] == table_id)
        assert released_table["status"] == "CLEANING"

        print(
            "Release 0.60 E2E PASS:",
            {
                "media_asset": asset_id,
                "group_code": group["group_code"],
                "reservation_id": reservation_id,
                "stay_id": stay_id,
                "table": table_code,
                "order_id": order_id,
                "folio_extras_kgs": folio2["totals"]["extras_kgs"],
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
