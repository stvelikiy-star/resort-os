"""Disposable local MARINA hotel: booking, PIN, hotel identity and checkout."""
import asyncio
import os
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx


def checked(response, code=200):
    assert response.status_code == code, (response.status_code, response.text)
    return response.json()


async def main():
    base = os.environ["MARINA_BOOKING_TEST_API"]
    assert urlsplit(base).hostname in {"127.0.0.1", "localhost"}
    assert os.environ.get("PROPERTY_CODE") == "MARINA_FULL_CI"
    async with httpx.AsyncClient(base_url=base, timeout=20) as owner:
        checked(await owner.post("/api/v1/auth/login", json={
            "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
            "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"],
        }))
        checked(await owner.patch("/api/v1/admin/hotel-setup/property", json={
            "name": "Synthetic Identity Hotel", "check_out_time": "10:30",
        }))
        rules = checked(await owner.get("/api/v1/admin/hotel-rules"))
        checked(await owner.put("/api/v1/admin/hotel-rules", json={
            "expected_version": rules["version"],
            "rules": {**rules["rules"], "official_contact": "+996700000001",
                      "checkout_instructions": "Synthetic checkout instruction"},
        }))
        today = datetime.now(ZoneInfo("Asia/Bishkek")).date()
        dates = {"check_in": str(today - timedelta(days=1)), "check_out": str(today + timedelta(days=2)),
                 "adults": 2, "children": 0}
        available = checked(await owner.get("/api/v1/booking/check-availability", params=dates))
        room = next(r for category in available["results"] for r in category["available_rooms"])
        payload = {**dates, "room_id": room["id"]}
        preview = checked(await owner.post("/api/v1/admin/pms/reservations/new/preview", json=payload))
        reservation = checked(await owner.post("/api/v1/admin/pms/reservations/new/commit", json={
            **payload, "guest_name": "Synthetic Identity Guest", "phone": "+996700000010",
            "expected_total_kgs": preview["pricing"]["total_kgs"],
            "expected_pricing_source": preview["pricing"]["source"],
        }), 201)
        reservation_id = reservation["reservation_id"]
        stay = checked(await owner.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-in"))
        qr = checked(await owner.post(f'/api/v1/admin/guest-os/room-qrs/{room["id"]}/issue'), 201)
        token = qr["token"]
        async with httpx.AsyncClient(base_url=base, timeout=20) as guest:
            path = f"/api/v1/guest-os/rooms/{token}"
            before = checked(await guest.get(path))
            assert before["property"] == {"name": "Synthetic Identity Hotel"}
            assert before["guest"] is None and before["stay"] is None
            checked(await guest.post(path + "/verify", json={"pin": stay["guest_access_pin"]}))
            after = checked(await guest.get(path))
            assert after["authenticated"] is True
            assert after["property"]["check_out_time"] == "10:30"
            assert after["property"]["official_contact"] == "+996700000001"
            assert after["property"]["checkout_instructions"] == "Synthetic checkout instruction"
            request = checked(await guest.post(path + "/requests", json={
                "request_code": "ADMIN", "description": "Synthetic guest request",
            }), 201)
            checked(await guest.get(path + "/requests"))
            checked(await owner.post(f"/api/v1/admin/stays/reservations/{reservation_id}/check-out"))
            expired = checked(await guest.get(path))
            assert expired["authenticated"] is False and expired["active_stay"] is False
            assert (await guest.get(path + "/requests")).status_code == 401
        print("MARINA_GUEST_IDENTITY_E2E_PASS: booking, check-in, QR/PIN, hotel settings, request, checkout revocation")


if __name__ == "__main__":
    asyncio.run(main())
