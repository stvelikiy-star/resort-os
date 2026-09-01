#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, timedelta
from http.cookiejar import CookieJar

import asyncpg

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DB = os.environ["DATABASE_URL"].replace("?schema=public", "")
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
RECEPTION_USERNAME = os.environ.get("FINANCE_RECEPTION_USERNAME", "finance-ci-reception")
RECEPTION_PASSWORD = os.environ.get("FINANCE_RECEPTION_PASSWORD", "Finance-Reception-CI-2026")


def call(method: str, path: str, payload: dict | None = None, cookie: str | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "three-crowns-finance-control-ci"}
    if cookie:
        headers["Cookie"] = cookie
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


def login(username: str, password: str) -> str:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    request = urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=20) as response:
        assert response.status == 200
        response.read()
    cookie = "; ".join(f"{item.name}={item.value}" for item in jar)
    assert cookie
    return cookie


def detail_code(body: dict) -> str | None:
    detail = body.get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def expect_error(result: tuple[int, dict], status: int, code: str | None = None) -> dict:
    actual, body = result
    assert actual == status, (actual, body)
    if code:
        assert detail_code(body) == code, body
    return body


async def db_local_today() -> date:
    conn = await asyncpg.connect(DB)
    try:
        value = await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
        assert value
        return value
    finally:
        await conn.close()


async def request_state(request_id: str) -> dict:
    conn = await asyncpg.connect(DB)
    try:
        row = await conn.fetchrow(
            '''
            SELECT rr.status::text AS status,rr."quotedTotalKgs",rr."requiredPrepaymentKgs",
                   (SELECT count(*)::int FROM payments p WHERE p."requestId"=rr.id) AS payment_count,
                   (SELECT count(*)::int FROM reservations r WHERE r."requestId"=rr.id) AS reservation_count
            FROM reservation_requests rr WHERE rr.id=$1::uuid
            ''',
            request_id,
        )
        assert row
        return dict(row)
    finally:
        await conn.close()


async def audit_count(action: str, resource_id: str) -> int:
    conn = await asyncpg.connect(DB)
    try:
        return int(await conn.fetchval(
            "SELECT count(*)::int FROM audit_logs WHERE action=$1 AND \"resourceId\"=$2 AND result='SUCCESS'",
            action,
            resource_id,
        ))
    finally:
        await conn.close()


async def reservation_state(reservation_id: str) -> dict:
    conn = await asyncpg.connect(DB)
    try:
        row = await conn.fetchrow(
            '''
            SELECT r."totalKgs",r.status::text AS status,r."checkIn",r."checkOut",
                   COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::int AS received_kgs
            FROM reservations r
            LEFT JOIN payments p ON p."reservationId"=r.id
            WHERE r.id=$1::uuid
            GROUP BY r.id,r."totalKgs",r.status,r."checkIn",r."checkOut"
            ''',
            reservation_id,
        )
        assert row
        return dict(row)
    finally:
        await conn.close()


async def prepare_valid_one_night_checkout_fixture(reservation_id: str, local_today: date) -> str:
    """Make the CI booking represent a stay that began yesterday.

    The clean test DB has no historic occupancy. Moving the planned start and its
    inventory segment back one day allows the real early-checkout guard to remain
    strict: check-in today followed by checkout today represents one night, not a
    forbidden zero-night stay.
    """
    conn = await asyncpg.connect(DB)
    try:
        room_id = await conn.fetchval(
            '''SELECT "roomId" FROM inventory_blocks
               WHERE "reservationId"=$1::uuid AND active=true AND "blockType"='RESERVATION'
               ORDER BY "startDate" LIMIT 1''',
            reservation_id,
        )
        assert room_id
        yesterday = local_today - timedelta(days=1)
        async with conn.transaction():
            await conn.execute(
                'UPDATE reservations SET "checkIn"=$2,"updatedAt"=now() WHERE id=$1::uuid',
                reservation_id,
                yesterday,
            )
            await conn.execute(
                '''UPDATE inventory_blocks SET "startDate"=$2,"updatedAt"=now()
                   WHERE "reservationId"=$1::uuid AND active=true AND "blockType"='RESERVATION' ''',
                reservation_id,
                yesterday,
            )
            await conn.execute(
                'UPDATE rooms SET "operationalState"=\'CLEAN\',"updatedAt"=now() WHERE id=$1',
                room_id,
            )
        return str(room_id)
    finally:
        await conn.close()


async def set_reservation_status(reservation_id: str, value: str) -> None:
    conn = await asyncpg.connect(DB)
    try:
        await conn.execute(
            'UPDATE reservations SET status=$2::"ReservationStatus","updatedAt"=now() WHERE id=$1::uuid',
            reservation_id,
            value,
        )
    finally:
        await conn.close()


async def move_payment_to_local_time(payment_id: str, local_date: date, local_time: str = "00:30") -> None:
    conn = await asyncpg.connect(DB)
    try:
        await conn.execute(
            '''
            UPDATE payments p
            SET "paidAt"=((($2::date + $3::text::time) AT TIME ZONE prop.timezone) AT TIME ZONE 'UTC'),"updatedAt"=now()
            FROM reservations r
            JOIN properties prop ON prop.id=r."propertyId"
            WHERE p.id=$1::uuid AND r.id=p."reservationId"
            ''',
            payment_id,
            local_date,
            local_time,
        )
    finally:
        await conn.close()


def sellable_options(check_in: date, check_out: date) -> list[dict]:
    query = urllib.parse.urlencode({
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "adults": 2,
        "children": 0,
    })
    status, body = call("GET", f"/api/v1/booking/check-availability?{query}")
    assert status == 200, (status, body)
    return [item for item in body.get("results", []) if item.get("pricing", {}).get("sellable")]


def create_and_quote(owner: str, suffix: str, check_in: date, check_out: date) -> tuple[str, int]:
    options = sellable_options(check_in, check_out)
    assert options, (check_in, check_out)
    status, created = call(
        "POST",
        "/api/v1/booking/requests",
        {
            "guest_name": f"Finance Control CI {suffix}",
            "phone": f"+996700{uuid.uuid4().int % 1000000:06d}",
            "email": f"finance-{uuid.uuid4().hex[:10]}@example.com",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": 2,
            "children": 0,
            "source": "FINANCE_CONTROL_CI",
        },
    )
    assert status == 201, (status, created)
    request_id = created["id"]
    status, quoted = call(
        "POST",
        f"/api/v1/admin/booking/requests/{request_id}/quote",
        {"room_type_code": options[0]["room_type_code"]},
        owner,
    )
    assert status == 200, (status, quoted)
    assert quoted["status"] == "QUOTED" and int(quoted["quoted_total_kgs"]) > 0
    return request_id, int(quoted["quoted_total_kgs"])


def confirm_request_payment(owner: str, request_id: str, amount: int, key: str, external_ref: str) -> tuple[int, dict]:
    return call(
        "POST",
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        {
            "amount_kgs": amount,
            "method": "MANAGER_MANUAL_CONFIRMATION",
            "external_ref": external_ref,
            "idempotency_key": key,
        },
        owner,
    )


def add_reservation_payment(
    owner: str,
    reservation_id: str,
    amount: int,
    key: str,
    external_ref: str,
    note: str,
    method: str = "CASH",
) -> tuple[int, dict]:
    return call(
        "POST",
        f"/api/v1/admin/booking/reservations/{reservation_id}/payments",
        {
            "amount_kgs": amount,
            "method": method,
            "external_ref": external_ref,
            "note": note,
            "idempotency_key": key,
        },
        owner,
    )


def finance_summary(owner: str, day_from: date, day_to: date | None = None) -> dict:
    day_to = day_to or day_from
    query = urllib.parse.urlencode({"from_date": day_from.isoformat(), "to_date": day_to.isoformat()})
    status, body = call("GET", f"/api/v1/admin/finance/summary?{query}", cookie=owner)
    assert status == 200, (status, body)
    return body


def main() -> None:
    today = asyncio.run(db_local_today())
    owner = login(OWNER_USERNAME, OWNER_PASSWORD)
    reception = login(RECEPTION_USERNAME, RECEPTION_PASSWORD)
    suffix = uuid.uuid4().hex[:8]

    # 1. Explicit manager commercial requirement has no payment/reservation side effect.
    requirement_request, quoted_total = create_and_quote(
        owner, f"require-{suffix}", today + timedelta(days=3), today + timedelta(days=5)
    )
    before = asyncio.run(request_state(requirement_request))
    assert before["payment_count"] == 0 and before["reservation_count"] == 0
    required = max(2, quoted_total // 3)
    status, body = call(
        "POST",
        f"/api/v1/admin/finance/requests/{requirement_request}/payment-requirement",
        {"amount_kgs": required},
        owner,
    )
    assert status == 200, (status, body)
    assert body["required_prepayment_kgs"] == required
    assert body["payment_created"] is False and body["reservation_created"] is False
    state = asyncio.run(request_state(requirement_request))
    assert state["status"] == "AWAITING_PREPAYMENT"
    assert int(state["requiredPrepaymentKgs"]) == required
    assert state["payment_count"] == 0 and state["reservation_count"] == 0
    assert asyncio.run(audit_count("SET_PAYMENT_REQUIREMENT", requirement_request)) == 1

    expect_error(
        call(
            "POST",
            f"/api/v1/admin/finance/requests/{requirement_request}/payment-requirement",
            {"amount_kgs": required + 1},
            reception,
        ),
        403,
    )
    expect_error(
        call(
            "POST",
            f"/api/v1/admin/finance/requests/{requirement_request}/payment-requirement",
            {"amount_kgs": quoted_total + 1},
            owner,
        ),
        422,
        "PAYMENT_REQUIREMENT_EXCEEDS_QUOTE",
    )
    expect_error(
        confirm_request_payment(
            owner,
            requirement_request,
            required - 1,
            f"finance-require-low-{suffix}",
            f"FIN-REQUIRE-LOW-{suffix}",
        ),
        409,
        "PAYMENT_BELOW_MANAGER_REQUIREMENT",
    )
    unchanged = asyncio.run(request_state(requirement_request))
    assert unchanged["status"] == "AWAITING_PREPAYMENT"
    assert int(unchanged["requiredPrepaymentKgs"]) == required
    assert unchanged["payment_count"] == 0 and unchanged["reservation_count"] == 0

    status, converted = confirm_request_payment(
        owner,
        requirement_request,
        required,
        f"finance-require-ok-{suffix}",
        f"FIN-REQUIRE-OK-{suffix}",
    )
    assert status == 201, (status, converted)
    assert converted["required_prepayment_kgs"] == required
    assert converted["manager_requirement_applied"] is True
    converted_state = asyncio.run(request_state(requirement_request))
    assert converted_state["status"] == "CONVERTED"
    assert int(converted_state["requiredPrepaymentKgs"]) == required

    # 2. Partial payments, replay idempotency, payload mismatch and external-ref conflict.
    debt_request, debt_quote = create_and_quote(owner, f"debt-{suffix}", today, today + timedelta(days=2))
    primary_key = f"finance-debt-primary-{suffix}"
    primary_ref = f"FIN-DEBT-PRIMARY-{suffix}"
    status, created = confirm_request_payment(owner, debt_request, 1000, primary_key, primary_ref)
    assert status == 201 and created["idempotent_replay"] is False, (status, created)
    debt_reservation = created["reservation_id"]

    replay_status, replay = confirm_request_payment(owner, debt_request, 1000, primary_key, primary_ref)
    assert replay_status == 201 and replay["idempotent_replay"] is True
    assert replay["payment_id"] == created["payment_id"]
    expect_error(
        confirm_request_payment(owner, debt_request, 1001, primary_key, primary_ref),
        409,
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )

    extra_key = f"finance-debt-extra-{suffix}"
    extra_ref = f"FIN-DEBT-EXTRA-{suffix}"
    status, extra = add_reservation_payment(
        owner, debt_reservation, 500, extra_key, extra_ref, "Finance Control partial payment"
    )
    assert status == 201 and extra["idempotent_replay"] is False, (status, extra)
    replay_status, replay_extra = add_reservation_payment(
        owner, debt_reservation, 500, extra_key, extra_ref, "Finance Control partial payment"
    )
    assert replay_status == 201 and replay_extra["idempotent_replay"] is True
    assert replay_extra["payment_id"] == extra["payment_id"]
    expect_error(
        add_reservation_payment(
            owner,
            debt_reservation,
            500,
            f"finance-ref-conflict-{suffix}",
            extra_ref,
            "must conflict",
        ),
        409,
        "PAYMENT_EXTERNAL_REF_CONFLICT",
    )
    pre_checkout = asyncio.run(reservation_state(debt_reservation))
    assert int(pre_checkout["received_kgs"]) == 1500
    assert int(pre_checkout["totalKgs"]) == debt_quote and debt_quote > 1500

    # 3. Real Stay lifecycle: checked-out debt must not disappear.
    asyncio.run(prepare_valid_one_night_checkout_fixture(debt_reservation, today))
    status, checked_in = call(
        "POST", f"/api/v1/admin/stays/reservations/{debt_reservation}/check-in", cookie=owner
    )
    assert status == 200 and checked_in["status"] == "CHECKED_IN", (status, checked_in)
    status, checked_out = call(
        "POST", f"/api/v1/admin/stays/reservations/{debt_reservation}/check-out", cookie=owner
    )
    assert status == 200 and checked_out["status"] == "CHECKED_OUT", (status, checked_out)
    post_checkout = asyncio.run(reservation_state(debt_reservation))
    assert post_checkout["status"] == "CHECKED_OUT"
    assert int(post_checkout["totalKgs"]) == debt_quote
    assert int(post_checkout["received_kgs"]) == 1500
    assert post_checkout["checkOut"] == today

    summary = finance_summary(owner, today)
    debtor = next((item for item in summary["debtors"] if item["reservation_id"] == debt_reservation), None)
    assert debtor
    assert debtor["status"] == "CHECKED_OUT" and debtor["balance_stage"] == "CHECKED_OUT_BALANCE"
    assert debtor["remaining_kgs"] == debt_quote - 1500
    assert summary["receivables_snapshot"]["checked_out_kgs"] >= debt_quote - 1500

    query = urllib.parse.urlencode({"from_date": today.isoformat(), "to_date": today.isoformat()})
    expect_error(call("GET", f"/api/v1/admin/finance/summary?{query}", cookie=reception), 403)

    # 4. A cancelled reservation with received money is a reconciliation exception.
    cancelled_request, _ = create_and_quote(
        owner, f"cancel-{suffix}", today + timedelta(days=3), today + timedelta(days=5)
    )
    status, cancelled_payment = confirm_request_payment(
        owner,
        cancelled_request,
        700,
        f"finance-cancel-{suffix}",
        f"FIN-CANCEL-{suffix}",
    )
    assert status == 201, (status, cancelled_payment)
    cancelled_reservation = cancelled_payment["reservation_id"]
    asyncio.run(set_reservation_status(cancelled_reservation, "CANCELLED"))

    # 5. Overpayment + 00:30 Asia/Bishkek reporting boundary.
    over_request, over_quote = create_and_quote(
        owner, f"over-{suffix}", today + timedelta(days=3), today + timedelta(days=5)
    )
    status, over_created = confirm_request_payment(
        owner,
        over_request,
        1000,
        f"finance-over-primary-{suffix}",
        f"FIN-OVER-PRIMARY-{suffix}",
    )
    assert status == 201, (status, over_created)
    over_reservation = over_created["reservation_id"]
    over_extra_amount = over_quote + 500
    status, over_extra = add_reservation_payment(
        owner,
        over_reservation,
        over_extra_amount,
        f"finance-over-extra-{suffix}",
        f"FIN-OVER-EXTRA-{suffix}",
        "Finance Control timezone-boundary overpayment",
        method="CARD",
    )
    assert status == 201, (status, over_extra)
    local_tomorrow = today + timedelta(days=1)
    asyncio.run(move_payment_to_local_time(over_extra["payment_id"], local_tomorrow, "00:30"))

    current = finance_summary(owner, today)
    cancelled_exception = next(
        (item for item in current["finance_exceptions"]["cancelled_with_received"] if item["reservation_id"] == cancelled_reservation),
        None,
    )
    assert cancelled_exception and cancelled_exception["received_kgs"] == 700
    over_exception = next(
        (item for item in current["finance_exceptions"]["overpaid_reservations"] if item["reservation_id"] == over_reservation),
        None,
    )
    assert over_exception and over_exception["overpaid_kgs"] == 1500

    tomorrow = finance_summary(owner, local_tomorrow)
    tomorrow_day = next(
        (item for item in tomorrow["received_by_day"] if str(item["local_date"]) == local_tomorrow.isoformat()),
        None,
    )
    assert tomorrow_day and int(tomorrow_day["amount_kgs"]) == over_extra_amount
    assert int(tomorrow["period_payments"]["received_kgs"]) == over_extra_amount
    recent = next((item for item in tomorrow["recent_payments"] if item["id"] == over_extra["payment_id"]), None)
    assert recent
    assert recent["note"] == "Finance Control timezone-boundary overpayment"
    assert recent["recorded_by_staff_id"]

    print(
        "PASS: finance control reconciles manager terms, enforced requirements, idempotent payments, "
        "valid stay checkout debt, exceptions and Asia/Bishkek calendar boundaries"
    )


if __name__ == "__main__":
    main()
