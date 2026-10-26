#!/usr/bin/env python3
"""Real synthetic MARINA booking lifecycle over HTTP. Never use on customer URLs."""
import asyncio
import os
from datetime import date, timedelta
from urllib.parse import urlsplit
import httpx

async def main():
    origin = os.environ.get("MARINA_BOOKING_TEST_API", "")
    parsed = urlsplit(origin)
    assert parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"), "Local disposable API only"
    assert os.environ.get("APP_ENV") in ("ci", "staging"), "Explicit synthetic CI/staging environment required"
    assert os.environ.get("PROPERTY_CODE") in ("MARINA_FULL_CI", "MARINA_DEMO"), "Synthetic MARINA property required"
    async with httpx.AsyncClient(base_url=origin, timeout=15) as c:
        auth = await c.post("/api/v1/auth/login", json={"username": os.environ["BOOTSTRAP_OWNER_USERNAME"], "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"]})
        assert auth.status_code == 200, (auth.status_code, auth.text)
        start = date.today() + timedelta(days=14)
        end = start + timedelta(days=2)
        avail = await c.get("/api/v1/booking/check-availability", params={"check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2})
        assert avail.status_code == 200, avail.text
        choices = avail.json().get("results", [])
        if not choices:
            # API shape may group under categories; fail closed rather than skip booking.
            raise AssertionError("No room categories returned by public availability")
        room_id = None
        for item in choices:
            rooms = item.get("available_rooms", [])
            if rooms:
                room_id = rooms[0]["id"]
                break
        assert room_id, f"No free room returned: {list(avail.json())}"
        payload = {"room_id": room_id, "check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2, "children": 0}
        preview = await c.post("/api/v1/admin/pms/reservations/new/preview", json=payload)
        assert preview.status_code == 200, (preview.status_code, preview.text)
        quote = preview.json()
        assert quote["can_commit"] is True, quote
        total = quote["pricing"]["total_kgs"]
        source = quote["pricing"]["source"]
        assert total > 0
        commit_payload = {**payload, "guest_name": "Synthetic Marina Guest", "phone": "+996555000101", "expected_total_kgs": total, "expected_pricing_source": source}
        first = await c.post("/api/v1/admin/pms/reservations/new/commit", json=commit_payload)
        assert first.status_code == 201, (first.status_code, first.text)
        booking = first.json()
        assert booking["status"] == "GUARANTEED" and booking["payment_created"] is False
        clash = await c.post("/api/v1/admin/pms/reservations/new/commit", json=commit_payload)
        assert clash.status_code == 409, (clash.status_code, clash.text)
        grid = await c.get("/api/v1/pms/grid", params={"start": start.isoformat(), "end": end.isoformat()})
        assert grid.status_code == 200, (grid.status_code, grid.text)
        assert grid.json()["property"] == os.environ["PROPERTY_CODE"]
        blocks = [b for room in grid.json()["rooms"] for b in room.get("blocks", [])]
        assert any(b.get("reservation_id") == booking["reservation_id"] for b in blocks), "Booking missing from canonical grid"
        print("MARINA_ORDINARY_BOOKING_E2E_PASS: preview, commit, price, no auto-payment, overlap 409, grid")
if __name__ == "__main__":
    asyncio.run(main())
