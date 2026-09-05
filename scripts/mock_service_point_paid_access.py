#!/usr/bin/env python3
"""Local-only HTTP mocks for Service Point paid-access CI.

The mock deliberately implements only the internal payment-bridge contract and the
small TTLock unlock response shape used by Resort Core. It is never imported by
production code.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SERVICE_KEY = os.environ.get("AUTOMATION_SERVICE_KEY", "")
PAYMENT_PORT = int(os.environ.get("PAID_ACCESS_PAYMENT_MOCK_PORT", "18081"))
TTLOCK_PORT = int(os.environ.get("PAID_ACCESS_TTLOCK_MOCK_PORT", "18082"))
LOG_PATH = Path(os.environ.get("PAID_ACCESS_MOCK_LOG", "/tmp/service-point-paid-access-mock.jsonl"))


def append_log(payload: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


class JsonHandler(BaseHTTPRequestHandler):
    server_version = "ThreeCrownsPaidAccessMock/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def read_body(self) -> bytes:
        length = int(self.headers.get("content-length", "0") or 0)
        return self.rfile.read(length)

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PaymentBridgeHandler(JsonHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/service-point-payment-intents":
            self.send_json(404, {"error": "not_found"})
            return
        if not SERVICE_KEY or self.headers.get("X-Resort-Service-Key") != SERVICE_KEY:
            self.send_json(401, {"error": "invalid_service_key"})
            return
        try:
            body = json.loads(self.read_body().decode("utf-8"))
        except Exception:
            self.send_json(400, {"error": "invalid_json"})
            return
        reference = str(body.get("reference") or "")
        provider_code = str(body.get("provider_code") or "")
        amount_kgs = body.get("amount_kgs")
        if not reference or not provider_code or not isinstance(amount_kgs, int) or amount_kgs <= 0:
            self.send_json(422, {"error": "invalid_payload"})
            return
        provider_payment_id = f"mock-{reference.lower()}"
        append_log({
            "kind": "payment_intent",
            "reference": reference,
            "provider_code": provider_code,
            "amount_kgs": amount_kgs,
            "service_point_code": body.get("service_point_code"),
        })
        self.send_json(200, {
            "provider_payment_id": provider_payment_id,
            "qr_payload": f"https://bank.example.invalid/pay/{urllib.parse.quote(reference)}",
        })


class TTLockHandler(JsonHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v3/lock/unlock":
            self.send_json(404, {"errcode": 404, "errmsg": "not_found"})
            return
        form = urllib.parse.parse_qs(self.read_body().decode("utf-8"), keep_blank_values=True)
        lock_id = (form.get("lockId") or [""])[0]
        client_id = (form.get("clientId") or [""])[0]
        access_token = (form.get("accessToken") or [""])[0]
        date_value = (form.get("date") or [""])[0]
        append_log({
            "kind": "ttlock_unlock",
            "lock_id": lock_id,
            "has_client_id": bool(client_id),
            "has_access_token": bool(access_token),
            "has_date": bool(date_value),
        })
        if not lock_id or not client_id or not access_token or not date_value:
            self.send_json(200, {"errcode": 10001, "errmsg": "missing_parameter"})
            return
        if lock_id == "99999":
            self.send_json(200, {"errcode": 20001, "errmsg": "mock_unlock_failure"})
            return
        self.send_json(200, {"errcode": 0, "description": "mock unlock accepted"})


def serve(server: ThreadingHTTPServer) -> None:
    server.serve_forever(poll_interval=0.2)


def main() -> None:
    LOG_PATH.unlink(missing_ok=True)
    payment_server = ThreadingHTTPServer(("127.0.0.1", PAYMENT_PORT), PaymentBridgeHandler)
    ttlock_server = ThreadingHTTPServer(("127.0.0.1", TTLOCK_PORT), TTLockHandler)
    payment_thread = threading.Thread(target=serve, args=(payment_server,), daemon=True)
    ttlock_thread = threading.Thread(target=serve, args=(ttlock_server,), daemon=True)
    payment_thread.start()
    ttlock_thread.start()
    print(f"paid-access mocks ready payment={PAYMENT_PORT} ttlock={TTLOCK_PORT}", flush=True)
    try:
        payment_thread.join()
    finally:
        payment_server.shutdown()
        ttlock_server.shutdown()


if __name__ == "__main__":
    main()
