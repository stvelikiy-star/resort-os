#!/usr/bin/env python3
"""Two independent hotel OWNER identities -> existing GreenAPI QR endpoints.

Real PostgreSQL sessions and full shared Core routing, synthetic provider
responses ONLY. This verifies credential selection, NOT WhatsApp delivery.
"""
import asyncio
import base64
import json
import os
from unittest.mock import patch

import asyncpg
from fastapi.testclient import TestClient

from marina_shared_live_browser_db import dsn

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nrc6-synthetic-png-only").decode()
A_TOKEN = "SyntheticProviderA_rc6_token_never_real"
B_TOKEN = "SyntheticProviderB_rc6_token_never_real"


async def prepare_accounts():
    conn = await asyncpg.connect(dsn())
    try:
        result = []
        for hotel in "AB":
            row = await conn.fetchrow(
                """SELECT p.id,p."tenantId" FROM properties p
                   JOIN tenants t ON t.id=p."tenantId"
                   WHERE p.code=$1 AND t.status='ACTIVE'""",
                "HOTEL_" + hotel,
            )
            assert row
            result.append({
                "tenant_id": str(row["tenantId"]),
                "property_id": str(row["id"]),
                "property_code": "HOTEL_" + hotel,
                "provider_origin": "https://7103.api.greenapi.com",
                "instance": "7103000001" if hotel == "A" else "7103000002",
                "token": A_TOKEN if hotel == "A" else B_TOKEN,
            })
        assert result[0]["property_id"] != result[1]["property_id"]
        assert result[0]["tenant_id"] != result[1]["tenant_id"]
        return result
    finally:
        await conn.close()


def expect(response, status, label):
    assert response.status_code == status, (
        label, response.status_code, str(response.text)[:180]
    )
    return response.json() if response.content else {}


def login(client, hotel, role, password):
    body = expect(client.post("/api/v1/auth/login", json={
        "tenant_code": "tenant_" + hotel.lower(), "property_code": "HOTEL_" + hotel,
        "username": role, "password": password,
    }), 200, hotel + " " + role + " login")
    assert body["property_code"] == "HOTEL_" + hotel


def main():
    assert os.environ.get("MARINA_SHARED_GREEN_RC6_CI_CONFIRM") == (
        "DISPOSABLE_TWO_HOTEL_GREEN_QR_CI_ONLY"
    )
    dsn()
    accounts = asyncio.run(prepare_accounts())
    os.environ["MARINA_SHARED_GREEN_RC6_CONFIG_JSON"] = json.dumps(accounts)
    assert os.environ.get("MARINA_SHARED_GREEN_RC6_ENABLED") == "true"
    assert os.environ.get("ENABLE_GREEN_API_CONNECTION") == "true"
    # Full, already-composed canonical app. Never use a fake login dependency.
    from app.app_entry import app
    from app import whatsapp_connection as wa
    from app.shared_green_rc6 import green_rc6_allowed
    assert green_rc6_allowed("GET", "/api/v1/admin/whatsapp/connection")
    assert green_rc6_allowed("POST", "/api/v1/admin/whatsapp/connection/qr")
    assert not green_rc6_allowed("POST", "/api/v1/admin/whatsapp/send-text")
    assert not green_rc6_allowed("GET", "/api/v1/admin/whatsapp/connection/foreign")

    requested = []

    async def synthetic_green(config, method):
        requested.append((config, method))
        if method == "qr":
            return {"type": "qrCode", "message": PNG}
        if method == "getStateInstance":
            return {"stateInstance": "authorized"}
        raise AssertionError("An unreviewed Green API method was requested")

    pwd = os.environ["MARINA_SHARED_BROWSER_CI_PASSWORD"]
    wa._windows.clear()
    with patch.object(wa, "_provider", side_effect=synthetic_green):
        with TestClient(app, base_url="https://green-rc6-ci.invalid") as anonymous, \
                TestClient(app, base_url="https://green-rc6-ci.invalid") as owner_a, \
                TestClient(app, base_url="https://green-rc6-ci.invalid") as owner_b, \
                TestClient(app, base_url="https://green-rc6-ci.invalid") as manager, \
                TestClient(app, base_url="https://green-rc6-ci.invalid") as reception:
            login(owner_a, "A", "owner", pwd)
            login(owner_b, "B", "owner", pwd)
            login(manager, "A", "manager", pwd)
            login(reception, "B", "reception", pwd)
            path = "/api/v1/admin/whatsapp/connection"
            expect(anonymous.get(path), 401, "anonymous pairing denied")
            expect(manager.get(path), 403, "manager pairing denied")
            expect(reception.post(path + "/qr"), 403, "reception pairing denied")

            for hotel, session, token, instance in (
                ("A", owner_a, A_TOKEN, "7103000001"),
                ("B", owner_b, B_TOKEN, "7103000002"),
            ):
                spoof = {"X-Property-Id": accounts[1 if hotel == "A" else 0]["property_id"],
                         "X-Tenant-Id": accounts[1 if hotel == "A" else 0]["tenant_id"]}
                status = expect(session.get(path, headers=spoof), 200, "owner status")
                assert status["configured"] is True and status["account_authorized"] is True
                assert status["messaging_verified"] is False and status["ai_auto_send"] is False
                assert "no-store" in session.get(path).headers["cache-control"]
                qr = expect(session.post(path + "/qr", headers=spoof), 200, "owner QR")
                assert qr["qr_data_url"] == "data:image/png;base64," + PNG
                assert token not in str(qr) and token not in str(status)
                assert requested[-1][0][1:] == (instance, token)
                assert requested[-1][1] == "qr"

            assert requested[0][0][1] == "7103000001"
            assert requested[0][0][2] == A_TOKEN
            assert requested[2][0][1] == "7103000002"
            assert requested[2][0][2] == B_TOKEN
            count = len(requested)
            for path2, method in (
                ("/api/v1/admin/inbox/outbound-capabilities", "GET"),
                ("/api/v1/admin/whatsapp/send-text", "POST"),
                ("/api/v1/admin/whatsapp/connection/export-credentials", "GET"),
            ):
                response = owner_a.get(path2) if method == "GET" else owner_a.post(path2)
                expect(response, 503, "unreviewed provider route")
            assert len(requested) == count

            # An owner must never get another hotel's account just by sending
            # a header or by supplying a malformed/ambiguous config map.
            with patch.dict(os.environ, {
                "MARINA_SHARED_GREEN_RC6_CONFIG_JSON": json.dumps(accounts[1:]),
            }):
                expect(owner_a.get(path), 503, "missing property binding")
            with patch.dict(os.environ, {
                "MARINA_SHARED_GREEN_RC6_CONFIG_JSON": json.dumps([
                    {**accounts[0], "instance": accounts[1]["instance"]}, accounts[1],
                ]),
            }):
                expect(owner_a.get(path), 503, "duplicate provider instance")
            with patch.dict(os.environ, {"MARINA_SHARED_GREEN_RC6_CONFIRM": "wrong"}):
                expect(owner_a.get(path), 503, "missing explicit RC6 approval")
            with patch.dict(os.environ, {"MARINA_SHARED_GREEN_RC6_ENABLED": "false"}):
                expect(owner_a.get(path), 503, "RC6 off")
            assert len(requested) == count
    print(
        "PASS: full shared API with DB OWNER A/B sessions uses separate bound "
        "GreenAPI QR instance/token; spoof headers ignored; manager/reception "
        "denied; provider sends/AI auto-send 503; all provider responses mock-only"
    )


if __name__ == "__main__":
    main()
