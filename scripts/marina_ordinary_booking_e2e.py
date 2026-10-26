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
        cancelled = await c.post(f"/api/v1/admin/pms/reservations/{booking['reservation_id']}/cancel")
        assert cancelled.status_code == 200, (cancelled.status_code, cancelled.text)
        assert cancelled.json()["status"] == "CANCELLED"
        assert cancelled.json()["released_blocks"] >= 1
        assert cancelled.json()["payment_refunded"] is False
        repeat = await c.post(f"/api/v1/admin/pms/reservations/{booking['reservation_id']}/cancel")
        assert repeat.status_code == 409, (repeat.status_code, repeat.text)
        refreshed = await c.get("/api/v1/pms/grid", params={"start": start.isoformat(), "end": end.isoformat()})
        assert refreshed.status_code == 200, refreshed.text
        remaining = [b for room in refreshed.json()["rooms"] for b in room.get("blocks", [])]
        assert not any(b.get("reservation_id") == booking["reservation_id"] for b in remaining), "Cancelled reservation still blocks the grid"
        available_again = await c.post("/api/v1/admin/pms/reservations/new/preview", json=payload)
        assert available_again.status_code == 200, (available_again.status_code, available_again.text)
        assert available_again.json()["can_commit"] is True, "Room was not released after cancellation"
        guests_response = await c.get("/api/v1/admin/intelligence/guests", params={"search": commit_payload["phone"]})
        assert guests_response.status_code == 200, (guests_response.status_code, guests_response.text)
        profiles = guests_response.json().get("items", [])
        assert profiles, "Cancelled guest disappeared from guest directory"
        history_matches = []
        for profile in profiles:
            detail_response = await c.get(f"/api/v1/admin/intelligence/guests/{profile['id']}")
            assert detail_response.status_code == 200, (detail_response.status_code, detail_response.text)
            history_matches.extend(item for item in detail_response.json().get("reservations", []) if item["id"] == booking["reservation_id"])
        assert len(history_matches) == 1, "Cancelled reservation missing or duplicated in guest history"
        history = history_matches[0]
        assert history["status"] == "CANCELLED", history
        assert history["total_kgs"] == total, "Original booking price must remain in historical facts"
        assert history["paid_kgs"] == 0 and history["outstanding_kgs"] == 0, "Unpaid cancelled booking must not show a debt"
        cancelled_folio = await c.get(f"/api/v1/admin/folio/reservations/{booking['reservation_id']}")
        assert cancelled_folio.status_code == 200, (cancelled_folio.status_code, cancelled_folio.text)
        assert cancelled_folio.json()["totals"]["remaining_kgs"] == 0, "Cancelled reservation cannot create a collectible folio debt"
        assert cancelled_folio.json()["totals"]["paid_kgs"] == 0
        closed_readiness = await c.get(f"/api/v1/admin/booking/reservations/{booking['reservation_id']}/acquiring-readiness")
        assert closed_readiness.status_code == 200, (closed_readiness.status_code, closed_readiness.text)
        assert closed_readiness.json()["payment_collection_eligible"] is False
        assert closed_readiness.json()["remaining_kgs"] == 0
        assert closed_readiness.json()["remaining_tyiyn"] == 0
        closed_payment = await c.post(f"/api/v1/admin/booking/reservations/{booking['reservation_id']}/payments", json={
            "amount_kgs": 100, "method": "CASH", "idempotency_key": f"synthetic-closed-{booking['reservation_id']}",
        })
        assert closed_payment.status_code == 409, (closed_payment.status_code, closed_payment.text)
        assert closed_payment.json()["detail"]["code"] == "PAYMENT_REQUIRES_CLOSED_BOOKING_REVIEW"
        closed_folio_again = await c.get(f"/api/v1/admin/folio/reservations/{booking['reservation_id']}")
        assert closed_folio_again.status_code == 200
        assert closed_folio_again.json()["totals"]["paid_kgs"] == 0, "Blocked payment must never mutate the ledger"


        # A returning guest must retain one CRM identity and both historical bookings.
        # The cancelled booking releases inventory, so the same stay may be rebooked.
        rebook = await c.post("/api/v1/admin/pms/reservations/new/commit", json=commit_payload)
        assert rebook.status_code == 201, (rebook.status_code, rebook.text)
        rebooked = rebook.json()
        assert rebooked["reservation_id"] != booking["reservation_id"]
        refreshed_guests = await c.get("/api/v1/admin/intelligence/guests", params={"search": commit_payload["phone"]})
        assert refreshed_guests.status_code == 200, (refreshed_guests.status_code, refreshed_guests.text)
        matches = [profile for profile in refreshed_guests.json().get("items", []) if profile.get("phone") == commit_payload["phone"]]
        assert len(matches) == 1, "Returning guest created a duplicate CRM profile"
        profile_detail = await c.get(f"/api/v1/admin/intelligence/guests/{matches[0]['id']}")
        assert profile_detail.status_code == 200, (profile_detail.status_code, profile_detail.text)
        guest_history = profile_detail.json()
        reservations_by_id = {item["id"]: item for item in guest_history["reservations"]}
        bookings = (booking["reservation_id"], rebooked["reservation_id"])
        assert all(item in reservations_by_id for item in bookings), "One of the returning guest bookings disappeared"
        assert reservations_by_id[booking["reservation_id"]]["status"] == "CANCELLED"
        assert reservations_by_id[booking["reservation_id"]]["outstanding_kgs"] == 0
        assert reservations_by_id[rebooked["reservation_id"]]["status"] == "GUARANTEED"
        assert guest_history["lifetime"]["booked_value_kgs"] >= rebooked["total_kgs"]
        assert guest_history["lifetime"]["reservation_count"] >= 2
        # An open folio receivable is a financial obligation, even when no
        # payment or checked-in stay exists. Never release the room silently.
        charge = await c.post(
            f"/api/v1/admin/folio/reservations/{rebooked['reservation_id']}/charges",
            json={"code": "TEST_EXTRA", "description": "Synthetic guest extra", "amount_kgs": 350},
        )
        assert charge.status_code == 201, (charge.status_code, charge.text)
        assert charge.json()["folio"]["totals"]["extras_kgs"] >= 350
        blocked_cancel = await c.post(f"/api/v1/admin/pms/reservations/{rebooked['reservation_id']}/cancel")
        assert blocked_cancel.status_code == 409, (blocked_cancel.status_code, blocked_cancel.text)
        assert blocked_cancel.json()["detail"]["code"] == "CANCELLATION_REQUIRES_FINANCE_OR_STAY_REVIEW"
        protected_grid = await c.get("/api/v1/pms/grid", params={"start": start.isoformat(), "end": end.isoformat()})
        assert protected_grid.status_code == 200, protected_grid.text
        protected_blocks = [block for room in protected_grid.json()["rooms"] for block in room.get("blocks", [])]
        assert any(block.get("reservation_id") == rebooked["reservation_id"] for block in protected_blocks), (
            "A financially unresolved booking lost its room block"
        )
        closed_charge = await c.patch(
            f"/api/v1/admin/folio/charges/{charge.json()['charge_id']}",
            json={"status": "WAIVED", "reason": "Synthetic owner-reviewed folio correction"},
        )
        assert closed_charge.status_code == 200, (closed_charge.status_code, closed_charge.text)
        closed_totals = closed_charge.json()["folio"]["totals"]
        assert closed_totals["extras_kgs"] == 0
        assert closed_totals["remaining_kgs"] == rebooked["total_kgs"]
        assert (await c.patch(
            f"/api/v1/admin/folio/charges/{charge.json()['charge_id']}",
            json={"status": "WAIVED", "reason": "Duplicate synthetic waiver"},
        )).status_code == 409, "Double closing a folio charge must be rejected"
        approved_cancel = await c.post(f"/api/v1/admin/pms/reservations/{rebooked['reservation_id']}/cancel")
        assert approved_cancel.status_code == 200, (approved_cancel.status_code, approved_cancel.text)
        final_folio = await c.get(f"/api/v1/admin/folio/reservations/{rebooked['reservation_id']}")
        assert final_folio.status_code == 200
        assert final_folio.json()["totals"]["remaining_kgs"] == 0
        assert final_folio.json()["totals"]["extras_kgs"] == 0
        print("MARINA_ORDINARY_BOOKING_E2E_PASS: booking, rebook, financial hold, reviewed waiver, cancellation, zero collectible folio debt")

if __name__ == "__main__":
    asyncio.run(main())
