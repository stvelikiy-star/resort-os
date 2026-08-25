#!/usr/bin/env python3
"""Prepare synthetic Resort OS demo bookings through real Core APIs.

This script is intentionally DEVELOPMENT-ONLY. It creates clearly marked
DEMO_SHOWCASE requests/reservations so the PMS chessboard is populated for a
presentation without bypassing booking invariants.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.cookiejar import CookieJar


CORE_BASE_URL = os.environ.get("CORE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
APP_ENV = os.environ.get("APP_ENV", "development").lower()
USERNAME = os.environ.get("DEMO_OWNER_USERNAME") or os.environ.get("BOOTSTRAP_OWNER_USERNAME")
PASSWORD = os.environ.get("DEMO_OWNER_PASSWORD") or os.environ.get("BOOTSTRAP_OWNER_PASSWORD")

DEMO_GUESTS = [
    ("DEMO · Айдана", "+996700900001"),
    ("DEMO · Тимур", "+996700900002"),
    ("DEMO · Алия", "+996700900003"),
    ("DEMO · Руслан", "+996700900004"),
    ("DEMO · Динара", "+996700900005"),
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def api(opener: urllib.request.OpenerDirector, method: str, path: str, payload=None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{CORE_BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {body}") from exc


def main() -> None:
    if APP_ENV in {"production", "prod"}:
        fail("prepare_demo_showcase.py is disabled when APP_ENV=production")
    if not USERNAME or not PASSWORD:
        fail("Set DEMO_OWNER_USERNAME/DEMO_OWNER_PASSWORD or BOOTSTRAP_OWNER_USERNAME/BOOTSTRAP_OWNER_PASSWORD")

    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    print(f"Core: {CORE_BASE_URL}")
    print("Checking health...")
    api(opener, "GET", "/health")

    print(f"Logging in as {USERNAME!r}...")
    api(opener, "POST", "/api/v1/auth/login", {"username": USERNAME, "password": PASSWORD})

    # Use hotel-relative near-future dates. Availability itself determines which
    # categories are safe/sellable under the currently loaded rate periods.
    first_check_in = date.today() + timedelta(days=1)
    summary: list[dict] = []

    for index, (guest_name, phone) in enumerate(DEMO_GUESTS):
        check_in = first_check_in + timedelta(days=index)
        nights = 2 + (index % 3)
        check_out = check_in + timedelta(days=nights)
        query = urllib.parse.urlencode(
            {
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 2,
                "children": 0,
            }
        )
        availability = api(opener, "GET", f"/api/v1/booking/check-availability?{query}")
        sellable = [
            item
            for item in availability.get("results", [])
            if item.get("pricing", {}).get("sellable") and item.get("available_count", 0) > 0
        ]
        if not sellable:
            print(f"SKIP {guest_name}: no sellable category for {check_in} -> {check_out}")
            continue

        # Spread the demo across categories when enough availability exists.
        room_type = sellable[index % len(sellable)]
        request_item = api(
            opener,
            "POST",
            "/api/v1/booking/requests",
            {
                "guest_name": guest_name,
                "phone": phone,
                "email": None,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": 2,
                "children": 0,
                "room_type_code": room_type["room_type_code"],
                "source": "DEMO_SHOWCASE",
                "notes": "Synthetic development demo data. Not a real guest booking.",
            },
        )
        request_id = request_item["id"]
        quote = api(
            opener,
            "POST",
            f"/api/v1/admin/booking/requests/{request_id}/quote",
            {"room_type_code": room_type["room_type_code"]},
        )

        # This is explicitly a synthetic manager-recorded demo fact. There is no
        # global prepayment percentage in Core; the amount exists only to exercise
        # the real manager-controlled conversion path during the demo.
        demo_payment = 1000 + index * 500
        reservation = api(
            opener,
            "POST",
            f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
            {
                "amount_kgs": demo_payment,
                "method": "DEMO_MANUAL",
                "provider": "DEMO_SHOWCASE",
                "external_ref": f"DEMO-{check_in:%Y%m%d}-{index + 1}",
                "idempotency_key": f"demo-showcase-{check_in:%Y%m%d}-{index + 1}-{request_id}",
            },
        )
        summary.append(
            {
                "guest": guest_name,
                "request_id": request_id,
                "booking_number": reservation.get("booking_number"),
                "reservation_id": reservation.get("reservation_id"),
                "room_code": reservation.get("room_code"),
                "room_type": quote.get("room_type_name"),
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "stay_total_kgs": quote.get("quoted_total_kgs"),
                "demo_payment_kgs": demo_payment,
            }
        )
        print(
            f"OK {guest_name}: {reservation.get('booking_number')} · room {reservation.get('room_code')} · "
            f"{check_in} -> {check_out}"
        )

    if not summary:
        fail("No demo reservation could be created. Check rate periods and availability.")

    output = os.environ.get("DEMO_SHOWCASE_OUTPUT", "/tmp/three-crowns-demo-showcase.json")
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(f"Created {len(summary)} synthetic reservations. Summary: {output}")
    print("All records are marked DEMO_SHOWCASE / DEMO_MANUAL and must not be treated as real guests or money.")


if __name__ == "__main__":
    main()
