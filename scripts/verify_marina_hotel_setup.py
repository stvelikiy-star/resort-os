import os
import secrets
from datetime import date, timedelta

import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME") or os.environ.get("SMOKE_OWNER_USERNAME")
PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD") or os.environ.get("SMOKE_OWNER_PASSWORD")


def expect(response: httpx.Response, code: int, label: str):
    if response.status_code != code:
        raise AssertionError(f"{label}: expected {code}, got {response.status_code}: {response.text}")
    if code == 204:
        return None
    return response.json()


def main() -> None:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Owner credentials are required")

    suffix = secrets.token_hex(4).upper()
    type_code = f"CI_{suffix}"
    room_code = f"CI-{suffix}"
    prefix = f"B{suffix}-"

    with httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True) as client:
        expect(
            client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}),
            200,
            "owner login",
        )

        overview = expect(client.get("/api/v1/admin/hotel-setup"), 200, "hotel setup overview")
        assert overview["property"]["code"]
        assert isinstance(overview["rooms"], list)
        assert isinstance(overview["room_types"], list)
        assert overview["product_settings"]["check_in_time"]
        assert overview["product_settings"]["check_out_time"]
        assert overview["onboarding"]["total"] == 5
        assert set(overview["onboarding"]["steps"]) == {"property", "room_types", "rooms", "rates", "staff"}
        assert overview["onboarding"]["completed"] == sum(
            1 for value in overview["onboarding"]["steps"].values() if value
        )

        original_modules = list(overview["product_settings"]["enabled_modules"])
        modules = expect(
            client.patch("/api/v1/admin/hotel-setup/modules", json={"enabled_modules": ["GROUPS", "AGENTS"]}),
            200,
            "patch modules",
        )
        assert modules["enabled_modules"] == ["GROUPS", "AGENTS"]

        bad_module = client.patch(
            "/api/v1/admin/hotel-setup/modules",
            json={"enabled_modules": ["GROUPS", "NOT_A_MODULE"]},
        )
        assert bad_module.status_code == 422

        expect(
            client.patch("/api/v1/admin/hotel-setup/modules", json={"enabled_modules": original_modules}),
            200,
            "restore modules",
        )

        prop = overview["property"]
        current_in = overview["product_settings"]["check_in_time"]
        current_out = overview["product_settings"]["check_out_time"]
        expect(
            client.patch(
                "/api/v1/admin/hotel-setup/property",
                json={
                    "name": prop["name"],
                    "timezone": prop["timezone"],
                    "currency": prop["currency"],
                    "check_in_time": "15:00",
                    "check_out_time": "11:00",
                },
            ),
            200,
            "patch property",
        )
        bad_timezone = client.patch(
            "/api/v1/admin/hotel-setup/property",
            json={"timezone": "Invalid/Timezone"},
        )
        assert bad_timezone.status_code == 422
        expect(
            client.patch(
                "/api/v1/admin/hotel-setup/property",
                json={
                    "name": prop["name"],
                    "timezone": prop["timezone"],
                    "currency": prop["currency"],
                    "check_in_time": current_in,
                    "check_out_time": current_out,
                },
            ),
            200,
            "restore property",
        )

        room_type = expect(
            client.post(
                "/api/v1/admin/hotel-setup/room-types",
                json={
                    "code": type_code,
                    "name": f"CI category {suffix}",
                    "capacity_adults": 2,
                    "capacity_children": 1,
                    "area_label": "24 m2",
                },
            ),
            201,
            "create room type",
        )
        type_id = room_type["id"]

        room = expect(
            client.post(
                "/api/v1/admin/hotel-setup/rooms",
                json={
                    "room_type_id": type_id,
                    "code": room_code,
                    "name": f"CI Room {suffix}",
                    "building_or_zone": "CI",
                    "floor_label": "9",
                    "bed_configuration": "1 double",
                    "operational_state": "CLEAN",
                },
            ),
            201,
            "create room",
        )
        room_id = room["id"]

        grid_start = date.today()
        grid_end = grid_start + timedelta(days=7)
        grid = expect(
            client.get(
                "/api/v1/pms/grid",
                params={"start": grid_start.isoformat(), "end": grid_end.isoformat()},
            ),
            200,
            "PMS grid after room create",
        )
        assert any(item["id"] == room_id and item["code"] == room_code for item in grid["rooms"]), (
            "new room did not appear in PMS grid without manual synchronization"
        )

        duplicate = client.post(
            "/api/v1/admin/hotel-setup/rooms",
            json={"room_type_id": type_id, "code": room_code, "operational_state": "CLEAN"},
        )
        assert duplicate.status_code == 409

        blocked_delete = client.delete(f"/api/v1/admin/hotel-setup/room-types/{type_id}")
        assert blocked_delete.status_code == 409

        blocked = expect(
            client.patch(
                f"/api/v1/admin/hotel-setup/rooms/{room_id}",
                json={"operational_state": "TECH_BLOCK"},
            ),
            200,
            "block room",
        )
        assert blocked["operational_state"] == "TECH_BLOCK"

        sale_start = date.today() + timedelta(days=1)
        sale_end = sale_start + timedelta(days=1)
        blocked_availability = expect(
            client.get(
                "/api/v1/booking/check-availability",
                params={
                    "check_in": sale_start.isoformat(),
                    "check_out": sale_end.isoformat(),
                    "adults": 1,
                    "children": 0,
                    "room_type_code": type_code,
                },
            ),
            200,
            "blocked room availability",
        )
        assert blocked_availability["results"] == [], "TECH_BLOCK room leaked into sellable inventory"

        reopened = expect(
            client.patch(
                f"/api/v1/admin/hotel-setup/rooms/{room_id}",
                json={"operational_state": "CLEAN", "floor_label": "10"},
            ),
            200,
            "reopen room",
        )
        assert reopened["operational_state"] == "CLEAN"
        assert reopened["floor_label"] == "10"

        reopened_availability = expect(
            client.get(
                "/api/v1/booking/check-availability",
                params={
                    "check_in": sale_start.isoformat(),
                    "check_out": sale_end.isoformat(),
                    "adults": 1,
                    "children": 0,
                    "room_type_code": type_code,
                },
            ),
            200,
            "reopened room availability",
        )
        assert len(reopened_availability["results"]) == 1
        assert reopened_availability["results"][0]["available_count"] == 1

        bulk = expect(
            client.post(
                "/api/v1/admin/hotel-setup/rooms/bulk",
                json={
                    "room_type_id": type_id,
                    "start_number": 1,
                    "end_number": 2,
                    "pad_width": 2,
                    "prefix": prefix,
                    "building_or_zone": "CI",
                    "floor_label": "10",
                    "operational_state": "CLEAN",
                },
            ),
            201,
            "bulk create",
        )
        assert bulk["created"] == 2

        current = expect(client.get("/api/v1/admin/hotel-setup"), 200, "overview after create")
        created_rows = [item for item in current["rooms"] if item["room_type_id"] == type_id]
        assert len(created_rows) == 3

        for item in created_rows:
            expect(client.delete(f"/api/v1/admin/hotel-setup/rooms/{item['id']}"), 204, f"delete room {item['code']}")

        expect(client.delete(f"/api/v1/admin/hotel-setup/room-types/{type_id}"), 204, "delete room type")

        final = expect(client.get("/api/v1/admin/hotel-setup"), 200, "final overview")
        assert not any(item["id"] == type_id for item in final["room_types"])
        assert not any(item["code"] == room_code or item["code"].startswith(prefix) for item in final["rooms"])

        compact = expect(
            client.post(
                "/api/v1/admin/hotel-setup/compact-demo",
                json={"confirmation": "CREATE_COMPACT_DEMO"},
            ),
            200,
            "rebuild compact demo",
        )
        assert compact["rooms"] == 12
        assert compact["room_types"] == 3

        compact_overview = expect(client.get("/api/v1/admin/hotel-setup"), 200, "compact overview")
        assert compact_overview["summary"]["rooms"] == 12
        assert compact_overview["summary"]["room_types"] == 3
        assert {item["code"] for item in compact_overview["room_types"]} == {"STANDARD", "COMFORT", "SUITE"}
        assert {item["code"] for item in compact_overview["rooms"]} == {
            "101", "102", "103", "104",
            "201", "202", "203", "204",
            "301", "302", "303", "304",
        }

    print("MARINA_HOTEL_SETUP_VERIFY_PASS")


if __name__ == "__main__":
    main()
