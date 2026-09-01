#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import asyncpg
import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Only-Strong-Password-2026")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os").split("?")[0]
PAYMENT_AMOUNT = 777


def assert_ok(response: httpx.Response, label: str) -> dict:
    if response.status_code >= 400:
        raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text}")
    return response.json()


async def payment_snapshot(reservation_id: str) -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        reservation = await conn.fetchrow(
            'SELECT "totalKgs","checkIn","checkOut" FROM reservations WHERE id=$1',
            uuid.UUID(reservation_id),
        )
        assert reservation, "reservation missing from PostgreSQL"
        payments = await conn.fetch(
            '''SELECT id,"amountKgs",status::text AS status,"idempotencyKey","externalRef"
               FROM payments WHERE "reservationId"=$1 ORDER BY "createdAt",id''',
            uuid.UUID(reservation_id),
        )
        return {
            "total_kgs": int(reservation["totalKgs"]),
            "check_in": reservation["checkIn"].isoformat(),
            "check_out": reservation["checkOut"].isoformat(),
            "payments": [
                {
                    "id": str(row["id"]),
                    "amount_kgs": int(row["amountKgs"]),
                    "status": row["status"],
                    "idempotency_key": row["idempotencyKey"],
                    "external_ref": row["externalRef"],
                }
                for row in payments
            ],
        }
    finally:
        await conn.close()


async def verify_audit(reservation_id: str, original_total: int, suggested_total: int, delta: int) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT "beforeJson","afterJson"
               FROM audit_logs
               WHERE resource='Reservation' AND "resourceId"=$1
                 AND action='PMS_SCHEDULE_MUTATION' AND result='SUCCESS'
               ORDER BY "createdAt" DESC LIMIT 1''',
            reservation_id,
        )
        assert row, "PMS schedule mutation audit is missing"
        before = row["beforeJson"]
        after = row["afterJson"]
        if isinstance(before, str):
            before = json.loads(before)
        if isinstance(after, str):
            after = json.loads(after)
        assert int(before["stored_total_kgs"]) == original_total, before
        assert int(after["stored_total_kgs"]) == original_total, after
        assert int(after["suggested_total_kgs"]) == suggested_total, after
        assert int(after["price_delta_kgs"]) == delta, after
    finally:
        await conn.close()


def main() -> None:
    today = datetime.now(ZoneInfo("Asia/Bishkek")).date()
    check_in = today + timedelta(days=1)
    original_check_out = check_in + timedelta(days=2)
    extended_check_out = check_in + timedelta(days=4)

    with httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True) as client:
        assert_ok(client.post("/api/v1/auth/login", json={"username": USERNAME, "password": PASSWORD}), "login")

        availability = assert_ok(
            client.get(
                "/api/v1/booking/check-availability",
                params={
                    "check_in": check_in.isoformat(),
                    "check_out": extended_check_out.isoformat(),
                    "adults": 2,
                    "children": 0,
                },
            ),
            "availability",
        )
        candidates = [item for item in availability["results"] if item["pricing"]["sellable"] and item["available_rooms"]]
        assert candidates, "need one sellable room for resize financial invariant"
        room_type_code = candidates[0]["room_type_code"]

        request_body = {
            "guest_name": "PMS Resize Financial Invariant",
            "phone": "+996555077700",
            "check_in": check_in.isoformat(),
            "check_out": original_check_out.isoformat(),
            "adults": 2,
            "children": 0,
            "room_type_code": room_type_code,
            "source": "CI_PMS_RESIZE_FINANCIAL",
        }
        booking_request = assert_ok(client.post("/api/v1/booking/requests", json=request_body), "booking request")
        request_id = booking_request["id"]
        assert_ok(
            client.post(f"/api/v1/admin/booking/requests/{request_id}/quote", json={"room_type_code": room_type_code}),
            "quote",
        )
        converted = assert_ok(
            client.post(
                f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
                json={
                    "amount_kgs": PAYMENT_AMOUNT,
                    "method": "MANAGER_MANUAL",
                    "provider": "MANAGER_MANUAL",
                    "external_ref": "pms-resize-financial-777",
                    "idempotency_key": "pms-resize-financial-payment-0001",
                },
            ),
            "confirm payment",
        )
        reservation_id = converted["reservation_id"]

        before = asyncio.run(payment_snapshot(reservation_id))
        assert before["check_in"] == check_in.isoformat(), before
        assert before["check_out"] == original_check_out.isoformat(), before
        assert len(before["payments"]) == 1, before
        assert before["payments"][0]["amount_kgs"] == PAYMENT_AMOUNT, before
        assert before["payments"][0]["status"] == "RECEIVED", before
        original_total = before["total_kgs"]
        original_payment = before["payments"][0].copy()

        schedule = assert_ok(client.get(f"/api/v1/admin/pms/reservations/{reservation_id}/schedule"), "schedule")
        assert len(schedule["schedule"]) == 1, schedule
        current = schedule["schedule"][0]
        assert current["start"] == check_in.isoformat(), current
        assert current["end"] == original_check_out.isoformat(), current

        proposal = {
            "segments": [
                {
                    "room_id": current["room_id"],
                    "start": check_in.isoformat(),
                    "end": extended_check_out.isoformat(),
                }
            ]
        }
        preview = assert_ok(
            client.post(f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/preview", json=proposal),
            "resize preview",
        )
        assert preview["can_commit"] is True, preview
        pricing = preview["pricing"]
        assert pricing["sellable"] is True, pricing
        assert pricing["stored_total_kgs"] == original_total, pricing
        assert pricing["stored_total_will_change_on_commit"] is False, pricing
        suggested_total = int(pricing["suggested_total_kgs"])
        delta = int(pricing["delta_kgs"])
        assert suggested_total > original_total, (
            f"extending 2 nights to 4 nights must increase Core suggested total: "
            f"stored={original_total}, suggested={suggested_total}"
        )
        assert delta == suggested_total - original_total and delta > 0, pricing

        commit_body = dict(proposal)
        commit_body["expected_version"] = preview["reservation"]["version"]
        committed = assert_ok(
            client.post(f"/api/v1/admin/pms/reservations/{reservation_id}/schedule/commit", json=commit_body),
            "resize commit",
        )
        assert committed["check_in"] == check_in.isoformat(), committed
        assert committed["check_out"] == extended_check_out.isoformat(), committed
        assert committed["stored_total_kgs"] == original_total, committed
        assert committed["pricing_preview"]["suggested_total_kgs"] == suggested_total, committed
        assert committed["pricing_preview"]["delta_kgs"] == delta, committed
        assert "stored reservation total was not changed automatically" in committed["message"], committed

        after = asyncio.run(payment_snapshot(reservation_id))
        assert after["check_out"] == extended_check_out.isoformat(), after
        assert after["total_kgs"] == original_total, (
            "PMS date mutation must not silently rewrite the commercial total; manager handles commercial adjustment separately",
            before,
            after,
        )
        assert after["payments"] == [original_payment], (
            "existing Payment fact changed or an extra payment was fabricated by PMS resize",
            before["payments"],
            after["payments"],
        )
        assert sum(item["amount_kgs"] for item in after["payments"] if item["status"] == "RECEIVED") == PAYMENT_AMOUNT

        asyncio.run(verify_audit(reservation_id, original_total, suggested_total, delta))

    print(
        "PASS: PMS resize financial invariant — Core recalculates 2→4-night suggested total and positive delta; "
        "stored commercial total remains manager-controlled; the existing 777 KGS Payment remains byte-for-byte unchanged; "
        "no payment is fabricated; audit records stored/suggested/delta values"
    )


if __name__ == "__main__":
    main()
