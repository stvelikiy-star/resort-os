#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from xml.etree import ElementTree

import asyncpg
import httpx

BASE = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DB = os.environ["DATABASE_URL"].split("?", 1)[0]
OWNER = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]
SERVICE_KEY = os.environ["AUTOMATION_SERVICE_KEY"]
MOCK_LOG = Path(os.environ.get("PAID_ACCESS_MOCK_LOG", "/tmp/service-point-paid-access-mock.jsonl"))


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"PASS: {message}")


def is_svg_document(value: str | None) -> bool:
    if not value:
        return False
    try:
        root = ElementTree.fromstring(value)
    except ElementTree.ParseError:
        return False
    return root.tag.rsplit("}", 1)[-1].lower() == "svg"


async def db_value(sql: str, *args):
    conn = await asyncpg.connect(DB)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def db_row(sql: str, *args):
    conn = await asyncpg.connect(DB)
    try:
        return await conn.fetchrow(sql, *args)
    finally:
        await conn.close()


async def db_execute(sql: str, *args):
    conn = await asyncpg.connect(DB)
    try:
        return await conn.execute(sql, *args)
    finally:
        await conn.close()


def mock_events(kind: str) -> list[dict]:
    if not MOCK_LOG.exists():
        return []
    rows = []
    for line in MOCK_LOG.read_text(encoding="utf-8").splitlines():
        try:
            body = json.loads(line)
        except json.JSONDecodeError:
            continue
        if body.get("kind") == kind:
            rows.append(body)
    return rows


def confirm(client: httpx.Client, intent: dict, *, event_id: str, amount_kgs: int | None = None, with_key: bool = True):
    headers = {"X-Resort-Service-Key": SERVICE_KEY} if with_key else {}
    return client.post(
        f"/api/v1/integrations/service-point-payments/{intent['provider_code']}/confirm",
        headers=headers,
        json={
            "reference": intent["reference"],
            "provider_payment_id": intent["provider_payment_id"],
            "amount_kgs": amount_kgs if amount_kgs is not None else intent["amount_kgs"],
            "currency": "KGS",
            "status": "PAID",
            "event_id": event_id,
        },
    )


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=30.0)
    login = client.post("/api/v1/auth/login", json={"username": OWNER, "password": OWNER_PASSWORD})
    check(login.status_code == 200, "owner login")

    payments_before = asyncio.run(db_value("SELECT count(*)::int FROM payments"))
    point_code = f"WC_CI_{uuid.uuid4().hex[:8].upper()}"
    point_create = client.post(
        "/api/v1/admin/service-points",
        json={
            "code": point_code,
            "name": "CI наружный туалет",
            "category": "RESTROOM",
            "zone_label": "CI paid access",
            "request_options": [
                {"code": "CLEANLINESS", "label": "Нужна уборка", "task_type": "HOUSEKEEPING", "priority": "NORMAL"},
            ],
        },
    )
    check(point_create.status_code == 201, f"paid access service point created: {point_create.text}")
    point_id = point_create.json()["id"]

    issue = client.post(f"/api/v1/admin/service-points/{point_id}/qr/issue")
    check(issue.status_code == 201, f"service point QR issued: {issue.text}")
    token = issue.json()["token"]

    configure = client.put(
        f"/api/v1/admin/service-point-payments/service-points/{point_id}",
        json={
            "mode": "PAID_LOCK",
            "amount_kgs": 50,
            "provider_code": "MBANK",
            "lock_provider_code": "TTLOCK",
            "lock_external_id": "12345",
            "is_active": True,
        },
    )
    check(configure.status_code == 200, f"paid lock profile configured: {configure.text}")
    check(configure.json()["runtime"]["ready"] is True, "paid access is runtime-ready only with configured bridge and TTLock")

    profile = client.get(f"/api/v1/service-point-payments/points/{token}/profile")
    check(profile.status_code == 200, profile.text)
    check(profile.json()["mode"] == "PAID_LOCK" and profile.json()["amount_kgs"] == 50, "public point exposes server-side price")

    intent = client.post(
        f"/api/v1/service-point-payments/points/{token}/intents",
        json={"client_request_id": f"ci-{uuid.uuid4()}"},
    )
    check(intent.status_code == 201, f"payment intent created: {intent.text}")
    intent_body = intent.json()
    check(intent_body["status"] == "AWAITING_PAYMENT", "payment intent waits for provider confirmation")
    check(is_svg_document(intent_body.get("payment_qr_svg")), "bank QR is generated from provider bridge payload")
    check(intent_body["amount_kgs"] == 50, "payment intent amount is immutable server truth")

    payments_mid = asyncio.run(db_value("SELECT count(*)::int FROM payments"))
    check(payments_mid == payments_before, "service point payment intent does not create accommodation Payment")

    unauthorized = confirm(client, intent_body, event_id=f"evt-{uuid.uuid4()}", with_key=False)
    check(unauthorized.status_code == 401, "provider confirmation is not public")

    mismatch = confirm(client, intent_body, event_id=f"evt-{uuid.uuid4()}", amount_kgs=51)
    check(mismatch.status_code == 409, "wrong provider amount cannot unlock")
    status_after_mismatch = client.get(f"/api/v1/service-point-payments/points/{token}/intents/{intent_body['id']}")
    check(status_after_mismatch.json()["status"] == "AWAITING_PAYMENT", "amount mismatch leaves intent unpaid")

    # Change live profile after intent creation. The already-created intent must keep
    # its original lock target, otherwise a configuration edit could unlock the wrong door.
    reconfigure = client.put(
        f"/api/v1/admin/service-point-payments/service-points/{point_id}",
        json={
            "mode": "PAID_LOCK",
            "amount_kgs": 50,
            "provider_code": "MBANK",
            "lock_provider_code": "TTLOCK",
            "lock_external_id": "54321",
            "is_active": True,
        },
    )
    check(reconfigure.status_code == 200, reconfigure.text)

    event_id = f"evt-{uuid.uuid4()}"
    paid = confirm(client, intent_body, event_id=event_id)
    check(paid.status_code == 200, f"verified payment accepted: {paid.text}")
    check(paid.json()["payment_status"] == "PAID", "bank confirmation becomes verified paid state")
    check(paid.json()["unlock"]["status"] == "UNLOCKED", "verified payment triggers TTLock unlock")

    stored = asyncio.run(db_row(
        '''SELECT i.status::text AS status,i."paidAt",i."unlockedAt",i."lockExternalId",a.status::text AS action_status,a."lockExternalId" AS action_lock
           FROM service_point_payment_intents i
           JOIN service_point_lock_actions a ON a."intentId"=i.id
           WHERE i.id=$1''',
        uuid.UUID(intent_body["id"]),
    ))
    check(stored is not None and stored["status"] == "UNLOCKED", "unlocked state persisted")
    check(stored["paidAt"] is not None and stored["unlockedAt"] is not None, "paid and unlocked timestamps persisted")
    check(stored["lockExternalId"] == "12345" and stored["action_lock"] == "12345", "payment intent snapshots original lock target")
    check(stored["action_status"] == "SUCCEEDED", "lock action ledger records successful actuation")
    ttlock_calls = mock_events("ttlock_unlock")
    check(bool(ttlock_calls) and ttlock_calls[-1]["lock_id"] == "12345", "TTLock adapter received snapshotted lockId")

    duplicate = confirm(client, intent_body, event_id=event_id)
    check(duplicate.status_code == 200, duplicate.text)
    check(duplicate.json()["unlock"]["status"] == "UNLOCKED", "duplicate paid webhook is idempotent")
    event_count = asyncio.run(db_value(
        '''SELECT count(*)::int FROM service_point_payment_events WHERE "providerCode"='MBANK' AND "providerEventId"=$1''',
        event_id,
    ))
    check(event_count == 1, "provider event id is deduplicated")

    audit_count = asyncio.run(db_value(
        '''SELECT count(*)::int FROM audit_logs WHERE resource='ServicePointPaymentIntent' AND "resourceId"=$1
             AND action='UNLOCK_SERVICE_POINT' AND result='SUCCESS' ''',
        intent_body["id"],
    ))
    check(audit_count == 1, "successful unlock is auditable without provider secrets")

    # Prove late bank confirmation never auto-opens a door. Manager may explicitly
    # retry the unlock after reviewing the real paid event. Backdate the intent as a
    # whole so the database invariant expiresAt > createdAt remains true while the
    # provider confirmation still arrives after expiry.
    late_intent_response = client.post(
        f"/api/v1/service-point-payments/points/{token}/intents",
        json={"client_request_id": f"ci-late-{uuid.uuid4()}"},
    )
    check(late_intent_response.status_code == 201, late_intent_response.text)
    late_intent = late_intent_response.json()
    asyncio.run(db_execute(
        '''UPDATE service_point_payment_intents
           SET "createdAt"=now()-interval '11 minutes',
               "expiresAt"=now()-interval '1 second'
           WHERE id=$1''',
        uuid.UUID(late_intent["id"]),
    ))
    calls_before_late = len(mock_events("ttlock_unlock"))
    late = confirm(client, late_intent, event_id=f"evt-late-{uuid.uuid4()}")
    check(late.status_code == 200, late.text)
    check(late.json()["unlock"]["failure_code"] == "LATE_PAYMENT_REQUIRES_REVIEW", "late paid event is held for manual review")
    check(len(mock_events("ttlock_unlock")) == calls_before_late, "late payment does not auto-actuate TTLock")
    late_stored = asyncio.run(db_row(
        '''SELECT status::text AS status,"paidAt","failureCode" FROM service_point_payment_intents WHERE id=$1''',
        uuid.UUID(late_intent["id"]),
    ))
    check(late_stored["status"] == "UNLOCK_FAILED" and late_stored["paidAt"] is not None, "late payment is retained as paid, not lost")

    manual_retry = client.post(f"/api/v1/admin/service-point-payments/intents/{late_intent['id']}/retry-unlock")
    check(manual_retry.status_code == 200 and manual_retry.json()["status"] == "UNLOCKED", "manager can explicitly release already-paid late access")

    # Prove a real lock failure never asks the guest to pay again and never mutates hotel finance.
    failure_config = client.put(
        f"/api/v1/admin/service-point-payments/service-points/{point_id}",
        json={
            "mode": "PAID_LOCK",
            "amount_kgs": 50,
            "provider_code": "MBANK",
            "lock_provider_code": "TTLOCK",
            "lock_external_id": "99999",
            "is_active": True,
        },
    )
    check(failure_config.status_code == 200, failure_config.text)
    failed_intent_response = client.post(
        f"/api/v1/service-point-payments/points/{token}/intents",
        json={"client_request_id": f"ci-fail-{uuid.uuid4()}"},
    )
    check(failed_intent_response.status_code == 201, failed_intent_response.text)
    failed_intent = failed_intent_response.json()
    failed = confirm(client, failed_intent, event_id=f"evt-fail-{uuid.uuid4()}")
    check(failed.status_code == 200, failed.text)
    check(failed.json()["payment_status"] == "PAID" and failed.json()["unlock"]["status"] == "UNLOCK_FAILED", "paid-but-lock-failed remains a paid incident")
    failed_status = client.get(f"/api/v1/service-point-payments/points/{token}/intents/{failed_intent['id']}").json()
    check(failed_status["status"] == "UNLOCK_FAILED" and failed_status["failure_code"] == "TTLOCK_20001", "TTLock provider failure is visible and retryable")

    payments_after = asyncio.run(db_value("SELECT count(*)::int FROM payments"))
    check(payments_after == payments_before, "entire paid access lifecycle leaves accommodation payments unchanged")

    print("SERVICE POINT PAID ACCESS E2E: PASS")
    client.close()


if __name__ == "__main__":
    main()
