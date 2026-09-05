#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from http.cookiejar import CookieJar

import asyncpg

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DB = os.environ["DATABASE_URL"].replace("?schema=public", "")
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]


def call(method: str, path: str, payload: dict | None = None, cookie_header: str | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


def assert_error(result: tuple[int, dict], code: str) -> dict:
    status, body = result
    assert status == 409, (status, body)
    detail = body.get("detail")
    assert isinstance(detail, dict), body
    assert detail.get("code") == code, body
    return detail


def login_cookie() -> str:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=json.dumps({"username": OWNER_USERNAME, "password": OWNER_PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=15) as response:
        assert response.status == 200
        json.loads(response.read().decode("utf-8"))
    cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in jar)
    assert cookie_header
    return cookie_header


def create_and_quote(cookie: str, suffix: str, room_type_code: str, check_in: str, check_out: str) -> str:
    status, created = call(
        "POST",
        "/api/v1/booking/requests",
        {
            "guest_name": f"Idempotency CI {suffix}",
            "phone": f"+99670000{suffix.zfill(4)[-4:]}",
            "check_in": check_in,
            "check_out": check_out,
            "adults": 2,
            "children": 0,
            "source": "PAYMENT_IDEMPOTENCY_CI",
        },
    )
    assert status == 201, (status, created)
    request_id = created["id"]
    status, quote = call(
        "POST",
        f"/api/v1/admin/booking/requests/{request_id}/quote",
        {"room_type_code": room_type_code},
        cookie,
    )
    assert status == 200, (status, quote)
    assert quote["status"] == "QUOTED"
    assert quote["quoted_total_kgs"] > 0
    return request_id


def confirm(cookie: str, request_id: str, *, amount: int, method: str, external_ref: str, key: str) -> tuple[int, dict]:
    return call(
        "POST",
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        {
            "amount_kgs": amount,
            "method": method,
            "external_ref": external_ref,
            "idempotency_key": key,
        },
        cookie,
    )


def add_payment(
    cookie: str,
    reservation_id: str,
    *,
    amount: int,
    method: str,
    external_ref: str,
    note: str,
    key: str,
    paid_at: str | None = None,
) -> tuple[int, dict]:
    payload = {
        "amount_kgs": amount,
        "method": method,
        "external_ref": external_ref,
        "note": note,
        "idempotency_key": key,
    }
    if paid_at is not None:
        payload["paid_at"] = paid_at
    return call(
        "POST",
        f"/api/v1/admin/booking/reservations/{reservation_id}/payments",
        payload,
        cookie,
    )


async def db_count(query: str, *args) -> int:
    conn = await asyncpg.connect(DB)
    try:
        return int(await conn.fetchval(query, *args))
    finally:
        await conn.close()


def main() -> None:
    check_in = (date.today() + timedelta(days=2)).isoformat()
    check_out = (date.today() + timedelta(days=4)).isoformat()

    status, availability = call(
        "GET",
        f"/api/v1/booking/check-availability?check_in={check_in}&check_out={check_out}&adults=2&children=0",
    )
    assert status == 200, (status, availability)
    sellable = [item for item in availability["results"] if item["pricing"]["sellable"]]
    assert sellable, availability
    room_type = sellable[0]["room_type_code"]

    cookie = login_cookie()

    # Primary ReservationRequest -> Reservation payment contract.
    request1 = create_and_quote(cookie, "101", room_type, check_in, check_out)
    primary_key = "ci-primary-idempotency-payload-001"
    primary_ref = "ci-primary-external-ref-001"
    first_status, first = confirm(
        cookie,
        request1,
        amount=1234,
        method="MANAGER_MANUAL",
        external_ref=primary_ref,
        key=primary_key,
    )
    assert first_status == 201, (first_status, first)
    assert first["idempotent_replay"] is False
    reservation1 = first["reservation_id"]

    replay_status, replay = confirm(
        cookie,
        request1,
        amount=1234,
        method="  MANAGER_MANUAL  ",
        external_ref=f"  {primary_ref}  ",
        key=primary_key,
    )
    assert replay_status == 201, (replay_status, replay)
    assert replay["idempotent_replay"] is True
    assert replay["payment_id"] == first["payment_id"]

    mismatch = confirm(
        cookie,
        request1,
        amount=1235,
        method="MANAGER_MANUAL",
        external_ref=primary_ref,
        key=primary_key,
    )
    detail = assert_error(mismatch, "IDEMPOTENCY_PAYLOAD_MISMATCH")
    assert "amount_kgs" in detail["mismatched_fields"]

    mismatch = confirm(
        cookie,
        request1,
        amount=1234,
        method="CASH",
        external_ref=primary_ref,
        key=primary_key,
    )
    detail = assert_error(mismatch, "IDEMPOTENCY_PAYLOAD_MISMATCH")
    assert "method" in detail["mismatched_fields"]

    mismatch = confirm(
        cookie,
        request1,
        amount=1234,
        method="MANAGER_MANUAL",
        external_ref="ci-primary-external-ref-other",
        key=primary_key,
    )
    detail = assert_error(mismatch, "IDEMPOTENCY_PAYLOAD_MISMATCH")
    assert "external_ref" in detail["mismatched_fields"]

    assert_error(
        confirm(
            cookie,
            request1,
            amount=1234,
            method="MANAGER_MANUAL",
            external_ref="ci-primary-second-operation",
            key="ci-primary-second-key-001",
        ),
        "REQUEST_ALREADY_CONVERTED",
    )

    request2 = create_and_quote(cookie, "102", room_type, check_in, check_out)
    assert_error(
        confirm(
            cookie,
            request2,
            amount=1234,
            method="MANAGER_MANUAL",
            external_ref="ci-primary-cross-request",
            key=primary_key,
        ),
        "IDEMPOTENCY_CONFLICT",
    )
    assert_error(
        confirm(
            cookie,
            request2,
            amount=2222,
            method="CARD",
            external_ref=primary_ref,
            key="ci-primary-external-ref-conflict-002",
        ),
        "PAYMENT_EXTERNAL_REF_CONFLICT",
    )

    second_status, second = confirm(
        cookie,
        request2,
        amount=2222,
        method="CARD",
        external_ref="ci-primary-external-ref-002",
        key="ci-primary-idempotency-payload-002",
    )
    assert second_status == 201, (second_status, second)
    reservation2 = second["reservation_id"]

    # Additional reservation-payment contract, including note and explicit paid_at binding.
    extra_key = "ci-extra-idempotency-payload-001"
    extra_ref = "ci-extra-external-ref-001"
    payment_event = (datetime.now(timezone.utc) - timedelta(minutes=10)).replace(microsecond=123000)
    payment_event_iso = payment_event.isoformat()
    extra_status, extra = add_payment(
        cookie,
        reservation1,
        amount=500,
        method="CASH",
        external_ref=extra_ref,
        note="front desk receipt",
        key=extra_key,
        paid_at=payment_event_iso,
    )
    assert extra_status == 201, (extra_status, extra)
    assert extra["idempotent_replay"] is False

    extra_replay_status, extra_replay = add_payment(
        cookie,
        reservation1,
        amount=500,
        method="  CASH  ",
        external_ref=f"  {extra_ref}  ",
        note="  front desk receipt  ",
        key=extra_key,
        paid_at=payment_event_iso,
    )
    assert extra_replay_status == 201, (extra_replay_status, extra_replay)
    assert extra_replay["idempotent_replay"] is True
    assert extra_replay["payment_id"] == extra["payment_id"]

    # Older/retrying clients that omit paid_at do not accidentally replace or conflict
    # with the stored event time; the existing payment is simply replayed.
    omitted_time_status, omitted_time = add_payment(
        cookie,
        reservation1,
        amount=500,
        method="CASH",
        external_ref=extra_ref,
        note="front desk receipt",
        key=extra_key,
    )
    assert omitted_time_status == 201, (omitted_time_status, omitted_time)
    assert omitted_time["idempotent_replay"] is True
    assert omitted_time["payment_id"] == extra["payment_id"]

    detail = assert_error(
        add_payment(
            cookie,
            reservation1,
            amount=501,
            method="CASH",
            external_ref=extra_ref,
            note="front desk receipt",
            key=extra_key,
            paid_at=payment_event_iso,
        ),
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )
    assert "amount_kgs" in detail["mismatched_fields"]

    detail = assert_error(
        add_payment(
            cookie,
            reservation1,
            amount=500,
            method="CASH",
            external_ref=extra_ref,
            note="changed note",
            key=extra_key,
            paid_at=payment_event_iso,
        ),
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )
    assert "note" in detail["mismatched_fields"]

    detail = assert_error(
        add_payment(
            cookie,
            reservation1,
            amount=500,
            method="CASH",
            external_ref=extra_ref,
            note="front desk receipt",
            key=extra_key,
            paid_at=(payment_event + timedelta(minutes=1)).isoformat(),
        ),
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )
    assert "paid_at" in detail["mismatched_fields"]

    assert_error(
        add_payment(
            cookie,
            reservation2,
            amount=500,
            method="CASH",
            external_ref="ci-extra-cross-reservation-ref",
            note="cross reservation",
            key=extra_key,
        ),
        "IDEMPOTENCY_CONFLICT",
    )
    assert_error(
        add_payment(
            cookie,
            reservation1,
            amount=600,
            method="CASH",
            external_ref=extra_ref,
            note="new operation",
            key="ci-extra-new-key-same-ref-001",
        ),
        "PAYMENT_EXTERNAL_REF_CONFLICT",
    )

    # Concurrent same-key primary conversion: exactly one write, one deterministic conflict.
    request3 = create_and_quote(cookie, "103", room_type, check_in, check_out)
    concurrent_key = "ci-primary-concurrent-key-001"
    concurrent_ref = "ci-primary-concurrent-ref-001"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                confirm,
                cookie,
                request3,
                amount=amount,
                method="CASH",
                external_ref=concurrent_ref,
                key=concurrent_key,
            )
            for amount in (777, 888)
        ]
        concurrent_results = [future.result() for future in futures]
    statuses = sorted(status for status, _ in concurrent_results)
    assert statuses == [201, 409], concurrent_results
    loser = next(result for result in concurrent_results if result[0] == 409)
    assert_error(loser, "IDEMPOTENCY_PAYLOAD_MISMATCH")
    assert asyncio.run(db_count('SELECT count(*) FROM payments WHERE "idempotencyKey"=$1', concurrent_key)) == 1
    assert asyncio.run(db_count('SELECT count(*) FROM reservations WHERE "requestId"=$1::uuid', request3)) == 1

    # Concurrent external-reference collision across reservations: no 500/duplicate write.
    race_ref = "ci-extra-concurrent-external-ref-001"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                add_payment,
                cookie,
                reservation_id,
                amount=amount,
                method="CASH",
                external_ref=race_ref,
                note="external ref race",
                key=key,
            )
            for reservation_id, amount, key in (
                (reservation1, 311, "ci-extra-race-key-001"),
                (reservation2, 322, "ci-extra-race-key-002"),
            )
        ]
        race_results = [future.result() for future in futures]
    statuses = sorted(status for status, _ in race_results)
    assert statuses == [201, 409], race_results
    loser = next(result for result in race_results if result[0] == 409)
    assert_error(loser, "PAYMENT_EXTERNAL_REF_CONFLICT")
    assert asyncio.run(
        db_count(
            'SELECT count(*) FROM payments WHERE provider=\'MANAGER_MANUAL\' AND "externalRef"=$1',
            race_ref,
        )
    ) == 1

    print("PASS: payment idempotency is payload/time-bound, scope-bound, and concurrency-safe")


if __name__ == "__main__":
    main()