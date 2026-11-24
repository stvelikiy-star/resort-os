"""Disposable two-property proof: full manual refund evidence (no funds sent)."""
import os
import uuid
from datetime import date, timedelta
from urllib.parse import urlparse
from fastapi.testclient import TestClient
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD

url = urlparse(os.getenv("DATABASE_URL", "").split("?")[0])
assert os.getenv("APP_ENV") == "staging"
assert os.getenv("MARINA_SHARED_AUTH_PREVIEW_ENABLED") == "true"
assert os.getenv("MARINA_SHARED_BROWSER_CI_CONFIRM") == "DISPOSABLE_TWO_HOTEL_BROWSER_CI"
assert os.getenv("MARINA_REFUND_EVIDENCE_CI_CONFIRM") == "ISOLATED_REFUND_EVIDENCE_ONLY"
assert url.hostname in {"localhost", "127.0.0.1"} and url.path == "/marina_shared_browser_ci"

passed = 0
def check(actual, expected, what):
    global passed
    assert actual == expected, (what, actual, expected)
    passed += 1

start = date.today() + timedelta(days=25)
reservations = {}
payments = {}
with TestClient(app, base_url="https://synthetic-staging.invalid") as client:
    def login(hotel, role):
        response = client.post("/api/v1/auth/login", json={
            "username": role.lower(), "password": PASSWORD,
            "tenant_code": "tenant_" + hotel.lower(),
            "property_code": "HOTEL_" + hotel})
        check(response.status_code, 200, hotel + role + " login")

    for hotel in ("A", "B"):
        login(hotel, "RECEPTION")
        grid = client.get("/api/v1/pms/grid", params={
            "start": start.isoformat(), "end": (start + timedelta(days=2)).isoformat()})
        check(grid.status_code, 200, "grid")
        body = {"room_id": grid.json()["rooms"][0]["id"], "check_in": start.isoformat(),
                "check_out": (start + timedelta(days=2)).isoformat(), "adults": 2, "children": 0}
        quote = client.post("/api/v1/admin/pms/reservations/new/preview", json=body)
        check(quote.status_code, 200, "quote")
        booking = client.post("/api/v1/admin/pms/reservations/new/commit", json={
            **body, "guest_name": "Synthetic Refund " + hotel, "phone": "555121212",
            "expected_total_kgs": quote.json()["pricing"]["total_kgs"],
            "expected_pricing_source": "CORE_RATE"})
        check(booking.status_code, 201, "booking")
        reservation_id = booking.json()["reservation_id"]
        payment = client.post(
            f"/api/v1/admin/booking/reservations/{reservation_id}/payments",
            json={"amount_kgs": 1000, "method": "CASH",
                  "idempotency_key": "refund-ci-" + str(uuid.uuid4())})
        check(payment.status_code, 201, "received cash")
        reservations[hotel] = reservation_id
        payments[hotel] = payment.json()["payment_id"]
        check(client.post("/api/v1/auth/logout").status_code, 204, "logout")

    for hotel in ("A", "B"):
        other = "B" if hotel == "A" else "A"
        path = (f"/api/v1/admin/booking/reservations/{reservations[hotel]}"
                f"/payments/{payments[hotel]}/confirm-manual-refund")
        payload = {"amount_kgs": 1000, "evidence_reference": "QA-EXTERNAL-" + str(uuid.uuid4()),
                   "note": "Confirmed outside system in synthetic CI"}
        login(hotel, "RECEPTION")
        check(client.post(path, json=payload).status_code, 403, "reception cannot refund")
        client.post("/api/v1/auth/logout")
        login(hotel, "OWNER")
        foreign_path = (f"/api/v1/admin/booking/reservations/{reservations[other]}"
                        f"/payments/{payments[other]}/confirm-manual-refund")
        check(client.post(foreign_path, json=payload).status_code, 404, "foreign payment")
        check(client.post(path, json={**payload, "amount_kgs": 500}).status_code,
              422, "partial refund unsupported")
        first = client.post(path, json=payload)
        check(first.status_code, 200, "record manual refund")
        check(first.json()["refund_executed_by_platform"], False, "no external payment action")
        replay = client.post(path, json=payload)
        check(replay.status_code, 200, "repeat same evidence")
        check(replay.json()["already_processed"], True, "idempotent replay")
        check(client.post(path, json={**payload, "evidence_reference": "DIFFERENT-REFERENCE"})
              .status_code, 409, "conflicting evidence")
        finance = client.get("/api/v1/admin/finance/summary", params={
            "from_date": date.today().isoformat(),
            "to_date": (date.today() + timedelta(days=40)).isoformat()})
        check(finance.status_code, 200, "finance after refund")
        check(finance.json()["reservation_ledger"][0]["received_kgs"], 0,
              "no double count refunded payment")
        check(finance.json()["refunded_snapshot_all_time"]["amount_kgs"], 1000,
              "all-time refund snapshot")
        client.post("/api/v1/auth/logout")
print("MARINA_TWO_HOTEL_MANUAL_FULL_REFUND_EVIDENCE_PASS", passed)
