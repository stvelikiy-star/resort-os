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


def call(method: str, path: str, payload: dict | None = None, cookie_header: str | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "three-crowns-finance-control-ci"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {}


def login_cookie(username: str, password: str) -> str:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(req, timeout=20) as response:
        assert response.status == 200
        json.loads(response.read().decode("utf-8"))
    cookie = "; ".join(f"{item.name}={item.value}" for item in jar)
    assert cookie
    return cookie


def detail_code(body: dict) -> str | None:
    detail = body.get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


def assert_error(result: tuple[int, dict], status: int, code: str | None = None) -> dict:
    actual_status, body = result
    assert actual_status == status, (actual_status, body)
    if code is not None:
        assert detail_code(body) == code, body
    return body


async def local_today() -> date:
    conn = await asyncpg.connect(DB)
    try:
        value = await conn.fetchval("SELECT (now() AT TIME ZONE timezone)::date FROM properties WHERE code='THREE_CROWNS'")
        assert value
        return value
    finally:
        await conn.close()


async def request_side_effects(request_id: str) -> dict:
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
            '''SELECT count(*)::int FROM audit_logs
               WHERE action=$1 AND "resourceId"=$2 AND result='SUCCESS' ''',
            action,
            resource_id,
        ))
    finally:
        await conn.close()


async def reservation_snapshot(reservation_id: str) -> dict:
    conn = await asyncpg.connect(DB)
    try:
        row = await conn.fetchrow(
            '''
            SELECT r."totalKgs",r.status::text AS status,
                   COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::int AS received_kgs
            FROM reservations r
            LEFT JOIN payments p ON p."reservationId"=r.id
            WHERE r.id=$1::uuid
            GROUP BY r.id,r."totalKgs",r.status
            ''',
            reservation_id,
        )
        assert row
        return dict(row)
    finally:
        await conn.close()


async def set_room_clean_for_reservation(reservation_id: str) -> str:
    conn = await asyncpg.connect(DB)
    try:
        room_id = await conn.fetchval(
            '''SELECT ib."roomId" FROM inventory_blocks ib
               WHERE ib."reservationId"=$1::uuid AND ib.active=true AND ib."blockType"='RESERVATION'
               ORDER BY ib."startDate",ib."endDate" LIMIT 1''',
            reservation_id,
        )
        assert room_id
        await conn.execute(
            '''UPDATE rooms SET "operationalState"='CLEAN',"updatedAt"=now() WHERE id=$1''',
            room_id,
        )
        return str(room_id)
    finally:
        await conn.close()


async def set_reservation_status(reservation_id: str, value: str) -> None:
    conn = await asyncpg.connect(DB)
    try:
        await conn.execute(
            '''UPDATE reservations SET status=$2::"ReservationStatus","updatedAt"=now() WHERE id=$1::uuid''',
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
            SET "paidAt"=(($2::date + $3::time) AT TIME ZONE prop.timezone),"updatedAt"=now()
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


def availability(check_in: date, check_out: date) -> list[dict]:
    query = urllib.parse.urlencode({
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "adults": 2,
        "children": 0,
    })
    status, body = call("GET", f"/api/v1/booking/check-availability?{query}")
    assert status == 200, (status, body)
    return [item for item in body.get("results", []) if item.get("pricing", {}).get("sellable")]


def create_and_quote(owner_cookie: str, suffix: str, check_in: date, check_out: date) -> tuple[str, int]:
    sellable = availability(check_in, check_out)
    assert sellable, (check_in, check_out)
    room_type_code = sellable[0]["room_type_code"]
    status, created = call(
        "POST",
        "/api/v1/booking/requests",
        {
            "guest_name": f"Finance Control CI {suffix}",
            "phone": f"+996700{suffix[-6:].zfill(6)}",
            "email": f"finance-{suffix}@example.com",
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
        {"room_type_code": room_type_code},
        owner_cookie,
    )
    assert status == 200, (status, quoted)
    assert quoted["status"] == "QUOTED" and int(quoted["quoted_total_kgs"]) > 0, quoted
    return request_id, int(quoted["quoted_total_kgs"])


def confirm_request_payment(
    owner_cookie: str,
    request_id: str,
    *,
    amount: int,
    key: str,
    external_ref: str,
    method: str = "MANAGER_MANUAL_CONFIRMATION",
) -> tuple[int, dict]:
    return call(
        "POST",
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        {
            "amount_kgs": amount,
            "method": method,
            "external_ref": external_ref,
            "idempotency_key": key,
        },
        owner_cookie,
    )


def add_reservation_payment(
    owner_cookie: str,
    reservation_id: str,
    *,
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
        owner_cookie,
    )


def finance_summary(owner_cookie: str, day_from: date, day_to: date | None = None) -> dict:
    day_to = day_to or day_from
    query = urllib.parse.urlencode({"from_date": day_from.isoformat(), "to_date": day_to.isoformat()})
    status, body = call("GET", f"/api/v1/admin/finance/summary?{query}", cookie_header=owner_cookie)
    assert status == 200, (status, body)
    return body


def main() -> None:
    today = asyncio.run(local_today())
    owner = login_cookie(OWNER_USERNAME, OWNER_PASSWORD)
    reception = login_cookie(RECEPTION_USERNAME, RECEPTION_PASSWORD)
    suffix = uuid.uuid4().hex[:8]

    # 1. Manager-owned payment requirement: commercial condition only, no Payment/Reservation side effect.
    req_id, quoted_total = create_and_quote(owner, f"require-{suffix}", today + timedelta(days=3), today + timedelta(days=5))
    before = asyncio.run(request_side_effects(req_id))
    assert before["payment_count"] == 0 and before["reservation_count"] == 0
    required_amount = max(1, quoted_total // 3)
    status, requirement = call(
        "POST",
        f"/api/v1/admin/finance/requests/{req_id}/payment-requirement",
        {"amount_kgs": required_amount},
        owner,
    )
    assert status == 200, (status, requirement)
    assert requirement["required_prepayment_kgs"] == required_amount
    assert requirement["payment_created"] is False and requirement["reservation_created"] is False
    assert requirement["payment_method"] == "MANAGER_DECIDES"
    after = asyncio.run(request_side_effects(req_id))
    assert after["status"] == "AWAITING_PREPAYMENT"
    assert int(after["requiredPrepaymentKgs"]) == required_amount
    assert after["payment_count"] == 0 and after["reservation_count"] == 0
    assert asyncio.run(audit_count("SET_PAYMENT_REQUIREMENT", req_id)) == 1

    assert_error(
        call(
            "POST",
            f"/api/v1/admin/finance/requests/{req_id}/payment-requirement",
            {"amount_kgs": required_amount + 1},
            reception,
        ),
        403,
    )
    assert_error(
        call(
            "POST",
            f"/api/v1/admin/finance/requests/{req_id}/payment-requirement",
            {"amount_kgs": quoted_total + 1},
            owner,
        ),
        422,
        "PAYMENT_REQUIREMENT_EXCEEDS_QUOTE",
    )

    # 2. Partial payments + idempotency + external-ref conflict.
    debt_request, debt_quote = create_and_quote(owner, f"debt-{suffix}", today, today + timedelta(days=2))
    primary_key = f"finance-debt-primary-{suffix}"
    primary_ref = f"FIN-DEBT-PRIMARY-{suffix}"
    status, created = confirm_request_payment(
        owner,
        debt_request,
        amount=1000,
        key=primary_key,
        external_ref=primary_ref,
    )
    assert status == 201, (status, created)
    assert created["idempotent_replay"] is False
    debt_reservation = created["reservation_id"]

    replay_status, replay = confirm_request_payment(
        owner,
        debt_request,
        amount=1000,
        key=primary_key,
        external_ref=primary_ref,
    )
    assert replay_status == 201 and replay["idempotent_replay"] is True
    assert replay["payment_id"] == created["payment_id"]
    assert_error(
        confirm_request_payment(
            owner,
            debt_request,
            amount=1001,
            key=primary_key,
            external_ref=primary_ref,
        ),
        409,
        "IDEMPOTENCY_PAYLOAD_MISMATCH",
    )

    extra_key = f"finance-debt-extra-{suffix}"
    extra_ref = f"FIN-DEBT-EXTRA-{suffix}"
    status, extra = add_reservation_payment(
        owner,
        debt_reservation,
        amount=500,
        key=extra_key,
        external_ref=extra_ref,
        note="Finance Control partial payment",
    )
    assert status == 201 and extra["idempotent_replay"] is False, (status, extra)
    replay_status, replay_extra = add_reservation_payment(
        owner,
        debt_reservation,
        amount=500,
        key=extra_key,
        external_ref=extra_ref,
        note="Finance Control partial payment",
    )
    assert replay_status == 201 and replay_extra["idempotent_replay"] is True
    assert replay_extra["payment_id"] == extra["payment_id"]
    assert_error(
        add_reservation_payment(
            owner,
            debt_reservation,
            amount=500,
            key=f"finance-debt-ref-conflict-{suffix}",
            external_ref=extra_ref,
            note="must conflict",
        ),
        409,
        "PAYMENT_EXTERNAL_REF_CONFLICT",
    )

    debt_before_checkout = asyncio.run(reservation_snapshot(debt_reservation))
    assert int(debt_before_checkout["received_kgs"]) == 1500
    assert int(debt_before_checkout["totalKgs"]) == debt_quote
    assert debt_quote > 1500

    # 3. A checked-out guest with unpaid balance must remain visible as a debtor.
    asyncio.run(set_room_clean_for_reservation(debt_reservation))
    status, check_in = call("POST", f"/api/v1/admin/stays/reservations/{debt_reservation}/check-in", cookie_header=owner)
    assert status == 200 and check_in["status"] == "CHECKED_IN", (status, check_in)
    status, check_out = call("POST", f"/api/v1/admin/stays/reservations/{debt_reservation}/check-out", cookie_header=owner)
    assert status == 200 and check_out["status"] == "CHECKED_OUT", (status, check_out)
    debt_after_checkout = asyncio.run(reservation_snapshot(debt_reservation))
    assert debt_after_checkout["status"] == "CHECKED_OUT"
    assert int(debt_after_checkout["totalKgs"]) == debt_quote
    assert int(debt_after_checkout["received_kgs"]) == 1500

    summary = finance_summary(owner, today)
    debt_item = next((item for item in summary["debtors"] if item["reservation_id"] == debt_reservation), None)
    assert debt_item, summary["debtors"]
    assert debt_item["status"] == "CHECKED_OUT"
    assert debt_item["balance_stage"] == "CHECKED_OUT_BALANCE"
    assert debt_item["remaining_kgs"] == debt_quote - 1500
    assert summary["receivables_snapshot"]["checked_out_kgs"] >= debt_quote - 1500

    # Finance summary itself remains manager-only.
    query = urllib.parse.urlencode({"from_date": today.isoformat(), "to_date": today.isoformat()})
    assert_error(call("GET", f"/api/v1/admin/finance/summary?{query}", cookie_header=reception), 403)

    # 4. Cancelled reservation with received money is an explicit reconciliation exception.
    cancel_request, _ = create_and_quote(owner, f"cancel-{suffix}", today + timedelta(days=3), today + timedelta(days=5))
    status, cancelled_payment = confirm_request_payment(
        owner,
        cancel_request,
        amount=700,
        key=f"finance-cancel-{suffix}",
        external_ref=f"FIN-CANCEL-{suffix}",
    )
    assert status == 201, (status, cancelled_payment)
    cancelled_reservation = cancelled_payment["reservation_id"]
    asyncio.run(set_reservation_status(cancelled_reservation, "CANCELLED"))

    # 5. Overpayment must be surfaced; its payment is moved to 00:30 hotel-local tomorrow
    #    to prove report boundaries use the property's timezone, not UTC date boundaries.
    over_request, over_quote = create_and_quote(owner, f"over-{suffix}", today + timedelta(days=3), today + timedelta(days=5))
    status, over_created = confirm_request_payment(
        owner,
        over_request,
        amount=1000,
        key=f"finance-over-primary-{suffix}",
        external_ref=f"FIN-OVER-PRIMARY-{suffix}",
    )
    assert status == 201, (status, over_created)
    over_reservation = over_created["reservation_id"]
    over_extra_amount = over_quote + 500
    status, over_extra = add_reservation_payment(
        owner,
        over_reservation,
        amount=over_extra_amount,
        key=f"finance-over-extra-{suffix}",
        external_ref=f"FIN-OVER-EXTRA-{suffix}",
        note="Finance Control timezone-boundary overpayment",
        method="CARD",
    )
    assert status == 201, (status, over_extra)
    local_tomorrow = today + timedelta(days=1)
    asyncio.run(move_payment_to_local_time(over_extra["payment_id"], local_tomorrow, "00:30"))

    current_summary = finance_summary(owner, today)
    cancelled_exception = next(
        (item for item in current_summary["finance_exceptions"]["cancelled_with_received"] if item["reservation_id"] == cancelled_reservation),
        None,
    )
    assert cancelled_exception and cancelled_exception["received_kgs"] == 700
    over_exception = next(
        (item for item in current_summary["finance_exceptions"]["overpaid_reservations"] if item["reservation_id"] == over_reservation),
        None,
    )
    assert over_exception, current_summary["finance_exceptions"]
    assert over_exception["overpaid_kgs"] == 1500

    tomorrow_summary = finance_summary(owner, local_tomorrow)
    tomorrow_day = next((item for item in tomorrow_summary["received_by_day"] if str(item["local_date"]) == local_tomorrow.isoformat()), None)
    assert tomorrow_day, tomorrow_summary["received_by_day"]
    assert int(tomorrow_day["amount_kgs"]) == over_extra_amount, tomorrow_summary["received_by_day"]
    assert int(tomorrow_summary["period_payments"]["received_kgs"]) == over_extra_amount, tomorrow_summary["period_payments"]

    recent = next((item for item in tomorrow_summary["recent_payments"] if item["id"] == over_extra["payment_id"]), None)
    assert recent, tomorrow_summary["recent_payments"]
    assert recent["note"] == "Finance Control timezone-boundary overpayment"
    assert recent["recorded_by_staff_id"]

    print(
        "PASS: finance control reconciles manager terms, idempotent payments, debtors, "
        "checked-out balances, exceptions and Asia/Bishkek reporting boundaries"
    )


if __name__ == "__main__":
    main()
