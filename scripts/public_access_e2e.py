#!/usr/bin/env python3
"""End-to-end contract for paid public QR access.

The test uses only synthetic access points and a local HMAC-verifying controller.
It proves:
- quote/checkout is bound to the configured access point price;
- payment truth can only arrive through the authenticated service callback;
- underpayment/conflicting truth is rejected;
- unpaid access cannot unlock;
- a confirmed payment is consumed only after the physical controller confirms;
- controller failure is fail-closed and preserves PAID for a safe retry;
- a successful grant is one-time and cannot be replayed.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import asyncpg
import httpx

CORE_API_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
SERVICE_KEY = os.environ["AUTOMATION_SERVICE_KEY"]
CONTROLLER_URL = os.environ["SMART_ACCESS_CONTROLLER_URL"].rstrip("/")
CONTROLLER_SECRET = os.environ["SMART_ACCESS_HMAC_SECRET"].encode("utf-8")


class ControllerState:
    requests: list[dict] = []


class ControllerHandler(BaseHTTPRequestHandler):
    server_version = "ThreeCrownsMockAccess/1.0"

    def log_message(self, _format: str, *_args) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        expected = hmac.new(CONTROLLER_SECRET, body, hashlib.sha256).hexdigest()
        supplied = self.headers.get("X-Resort-Signature", "")
        if self.path != "/unlock" or not hmac.compare_digest(expected, supplied):
            self.send_response(403)
            self.end_headers()
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return
        ControllerState.requests.append(payload)
        if str(payload.get("access_point_code", "")).endswith("_FAIL"):
            self.send_response(503)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def start_controller() -> ThreadingHTTPServer:
    parsed = urlsplit(CONTROLLER_URL)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
        raise RuntimeError("CI smart-access controller must use localhost with an explicit port")
    server = ThreadingHTTPServer(("127.0.0.1", parsed.port), ControllerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def insert_point(conn: asyncpg.Connection, code: str, price: int) -> uuid.UUID:
    property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", PROPERTY_CODE)
    assert property_id, f"Property {PROPERTY_CODE} is not loaded"
    point_id = uuid.uuid4()
    await conn.execute(
        '''INSERT INTO smart_access_points
           (id,"propertyId",code,name,kind,"priceKgs",active,"controllerRef","createdAt","updatedAt")
           VALUES($1,$2,$3,$4,'TOILET',$5,true,$6,now(),now())''',
        point_id,
        property_id,
        code,
        f"CI платный туалет {code}",
        price,
        f"controller:{code}",
    )
    return point_id


async def checkout(client: httpx.AsyncClient, code: str, expected_price: int) -> dict:
    quote = await client.get(f"{CORE_API_URL}/api/v1/public/access/{code}")
    assert quote.status_code == 200, quote.text
    q = quote.json()
    assert q["code"] == code
    assert q["kind"] == "TOILET"
    assert q["price_kgs"] == expected_price
    assert q["payment_required"] is True

    created = await client.post(f"{CORE_API_URL}/api/v1/public/access/{code}/checkout")
    assert created.status_code == 201, created.text
    intent = created.json()
    assert intent["amount_kgs"] == expected_price
    assert len(intent["token"]) >= 20
    assert "intent_id=" in intent["checkout_url"]
    assert f"amount_kgs={expected_price}" in intent["checkout_url"]
    assert f"access_point={code}" in intent["checkout_url"]
    return intent


async def status_for(client: httpx.AsyncClient, intent: dict) -> str:
    response = await client.post(
        f"{CORE_API_URL}/api/v1/public/access/intents/{intent['intent_id']}/status",
        json={"token": intent["token"]},
    )
    assert response.status_code == 200, response.text
    return response.json()["status"]


async def confirm_paid(client: httpx.AsyncClient, intent: dict, expected_price: int, external_ref: str) -> None:
    endpoint = f"{CORE_API_URL}/api/v1/automation/public-access/{intent['intent_id']}/paid"
    payload = {"amount_kgs": expected_price, "provider": "CI_PROVIDER", "external_ref": external_ref}

    unauthenticated = await client.post(endpoint, json=payload)
    assert unauthenticated.status_code == 401, unauthenticated.text

    wrong_amount = await client.post(
        endpoint,
        headers={"X-Resort-Service-Key": SERVICE_KEY},
        json={**payload, "amount_kgs": expected_price - 1},
    )
    assert wrong_amount.status_code == 409, wrong_amount.text

    paid = await client.post(endpoint, headers={"X-Resort-Service-Key": SERVICE_KEY}, json=payload)
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["status"] == "PAID" and body["idempotent"] is False

    duplicate = await client.post(endpoint, headers={"X-Resort-Service-Key": SERVICE_KEY}, json=payload)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["idempotent"] is True


async def main() -> int:
    controller = start_controller()
    point_ids: list[uuid.UUID] = []
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        suffix = uuid.uuid4().hex[:10].upper()
        ok_code = f"CI_TOILET_{suffix}"
        fail_code = f"CI_TOILET_{suffix}_FAIL"
        price = 75
        point_ids.append(await insert_point(conn, ok_code, price))
        point_ids.append(await insert_point(conn, fail_code, price))

        async with httpx.AsyncClient(timeout=8.0) as client:
            ok_intent = await checkout(client, ok_code, price)
            assert await status_for(client, ok_intent) == "PENDING"

            unpaid_unlock = await client.post(
                f"{CORE_API_URL}/api/v1/public/access/intents/{ok_intent['intent_id']}/unlock",
                json={"token": ok_intent["token"]},
            )
            assert unpaid_unlock.status_code == 409, unpaid_unlock.text
            assert ControllerState.requests == [], "Unpaid request reached physical controller"

            await confirm_paid(client, ok_intent, price, f"CI-PAID-{suffix}")
            assert await status_for(client, ok_intent) == "PAID"

            unlocked = await client.post(
                f"{CORE_API_URL}/api/v1/public/access/intents/{ok_intent['intent_id']}/unlock",
                json={"token": ok_intent["token"]},
            )
            assert unlocked.status_code == 200, unlocked.text
            assert unlocked.json()["status"] == "USED"
            assert await status_for(client, ok_intent) == "USED"
            assert len(ControllerState.requests) == 1
            assert ControllerState.requests[0]["access_point_code"] == ok_code
            assert ControllerState.requests[0]["action"] == "UNLOCK"

            replay = await client.post(
                f"{CORE_API_URL}/api/v1/public/access/intents/{ok_intent['intent_id']}/unlock",
                json={"token": ok_intent["token"]},
            )
            assert replay.status_code == 409, replay.text
            assert len(ControllerState.requests) == 1, "Used payment was replayed to controller"

            ok_row = await conn.fetchrow(
                '''SELECT status,provider,"externalRef","usedAt" FROM public_access_payment_intents WHERE id=$1''',
                uuid.UUID(ok_intent["intent_id"]),
            )
            assert ok_row and ok_row["status"] == "USED" and ok_row["usedAt"] is not None
            assert ok_row["provider"] == "CI_PROVIDER" and ok_row["externalRef"] == f"CI-PAID-{suffix}"
            ok_grants = await conn.fetch(
                '''SELECT status,"usedAt" FROM smart_access_grants WHERE "accessPointId"=$1 ORDER BY "createdAt"''',
                point_ids[0],
            )
            assert len(ok_grants) == 1 and ok_grants[0]["status"] == "USED" and ok_grants[0]["usedAt"] is not None

            fail_intent = await checkout(client, fail_code, price)
            await confirm_paid(client, fail_intent, price, f"CI-FAIL-{suffix}")
            failed_unlock = await client.post(
                f"{CORE_API_URL}/api/v1/public/access/intents/{fail_intent['intent_id']}/unlock",
                json={"token": fail_intent["token"]},
            )
            assert failed_unlock.status_code == 503, failed_unlock.text
            assert await status_for(client, fail_intent) == "PAID", "Controller failure consumed payment"
            assert len(ControllerState.requests) == 2
            assert ControllerState.requests[-1]["access_point_code"] == fail_code

            fail_row = await conn.fetchrow(
                '''SELECT status,"usedAt" FROM public_access_payment_intents WHERE id=$1''',
                uuid.UUID(fail_intent["intent_id"]),
            )
            assert fail_row and fail_row["status"] == "PAID" and fail_row["usedAt"] is None
            failed_grants = await conn.fetch(
                '''SELECT status,"usedAt" FROM smart_access_grants WHERE "accessPointId"=$1 ORDER BY "createdAt"''',
                point_ids[1],
            )
            assert len(failed_grants) == 1 and failed_grants[0]["status"] == "REVOKED" and failed_grants[0]["usedAt"] is None

        print("PASS: public QR quote and checkout preserve the configured price")
        print("PASS: unauthenticated/underpaid callbacks and unpaid unlock are rejected")
        print("PASS: authenticated provider callback is idempotent and establishes PAID truth")
        print("PASS: successful physical confirmation consumes payment exactly once")
        print("PASS: controller failure is fail-closed and preserves PAID for retry")
        return 0
    finally:
        if point_ids:
            await conn.execute('DELETE FROM smart_access_points WHERE id = ANY($1::uuid[])', point_ids)
        await conn.close()
        controller.shutdown()
        controller.server_close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
