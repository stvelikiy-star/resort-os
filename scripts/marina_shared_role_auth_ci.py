#!/usr/bin/env python3
"""Real canonical FastAPI + disposable PostgreSQL auth/RBAC acceptance for 12 roles x 2 hotels.

No mocks, no production environment, no schema reset. Runs after the existing
two-property Chromium PMS acceptance in a separate test process so that
the live service's per-process login throttle is not bypassed.
"""
import asyncio
from datetime import date, timedelta
import json
from pathlib import Path
import sys

import asyncpg
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app import auth
from app.app_entry import app
from marina_shared_live_browser_db import PASSWORD, SERVER_ROLES, dsn

EXPECTED = {
    "OWNER": ("DASHBOARD", "PMS", "RESERVATIONS", "OPS", "STAFF"),
    "MANAGER": ("DASHBOARD", "PMS", "RESERVATIONS", "OPS", "STAFF"),
    "RECEPTION": ("PMS", "RESERVATIONS"),
    "AGENT": ("PMS",),
    "MAID": ("OPS",),
    "TECHNICIAN": ("OPS",),
    "COOK": (),
    "WAITER": (),
    "STORE_STAFF": (),
    "DINING_STAFF": (),
    "CONTENT_MANAGER": (),
    "BEACH_PARTNER": (),
}
assert set(EXPECTED) == set(SERVER_ROLES)
RECEIPTS = Path("/tmp/marina_shared_browser_receipts.json")


def mutate(sql, *args):
    async def work():
        conn = await asyncpg.connect(dsn())
        try:
            return await conn.execute(sql, *args)
        finally:
            await conn.close()
    return asyncio.run(work())


def login(client, hotel, role, *, expect=200):
    client.cookies.clear()
    answer = client.post("/api/v1/auth/login", json={
        "tenant_code": "tenant_" + hotel[-1].lower(),
        "property_code": hotel,
        "username": role.lower(),
        "password": PASSWORD,
    })
    assert answer.status_code == expect, (
        f"{hotel}/{role} login {answer.status_code}: {answer.text[:240]}"
    )
    return answer


def main():
    assert auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED and auth.MARINA_TENANT_CONTEXT_ENABLED
    dsn()  # Require localhost database, disposable name and explicit confirmation.
    receipts = json.loads(RECEIPTS.read_text())
    assert set(receipts) == {"HOTEL_A", "HOTEL_B"}
    token_cookie = auth.SESSION_COOKIE
    with TestClient(app, base_url="http://127.0.0.1:18000") as client:
        assert client.get("/api/v1/auth/me").status_code == 401
        mode = client.get("/api/v1/auth/mode")
        assert mode.status_code == 200 and mode.json()["mode"] == "shared_auth_preview"

        seen = {}
        for hotel in ("HOTEL_A", "HOTEL_B"):
            for role in SERVER_ROLES:
                answer = login(client, hotel, role)
                identity = answer.json()
                assert identity["role"] == role and identity["property_code"] == hotel
                assert isinstance(identity["property_id"], str) and identity["property_id"]
                assert isinstance(identity["tenant_id"], str) and identity["tenant_id"]
                assert isinstance(identity["module_permissions"], list)
                assert set(EXPECTED[role]).issubset(identity["module_permissions"])
                assert identity["module_permissions_custom"] is False
                token = client.cookies.get(token_cookie)
                assert token and token.startswith("ms1.")
                assert token not in seen.values(), "Distinct sign-ins cannot reuse a token"
                seen[(hotel, role)] = token

                # Forge client-selected tenant/role headers; server session wins.
                foreign = "HOTEL_B" if hotel == "HOTEL_A" else "HOTEL_A"
                headers = {"X-Tenant-Id": "tenant_" + foreign[-1].lower(),
                           "X-Property-Id": receipts[foreign]["room_id"],
                           "X-Role": "OWNER"}
                me = client.get("/api/v1/auth/me", headers=headers)
                assert me.status_code == 200 and me.json()["role"] == role
                assert me.json()["property_code"] == hotel
                assert me.json()["tenant_id"] == identity["tenant_id"]

                # Canonical routes in the *same* assembled server (no mock ASGI).
                choices = (
                    ("/api/v1/admin/dashboard", role in ("OWNER", "MANAGER")),
                    ("/api/v1/pms/grid?start=" +
                     (date.today()+timedelta(days=2)).isoformat() + "&end=" +
                     (date.today()+timedelta(days=4)).isoformat(),
                     role in ("OWNER", "MANAGER", "RECEPTION", "AGENT")),
                    ("/api/v1/admin/reception/reservations",
                     role in ("OWNER", "MANAGER", "RECEPTION")),
                    ("/api/v1/ops/tasks", role in ("OWNER", "MANAGER", "MAID", "TECHNICIAN")),
                    ("/api/v1/admin/staff/overview", role in ("OWNER", "MANAGER")),
                )
                for url, granted in choices:
                    response = client.get(url, headers=headers)
                    assert response.status_code == (200 if granted else 403), (
                        f"{hotel}/{role} {url}: {response.status_code} "
                        f"expected {200 if granted else 403} {response.text[:180]}"
                    )
                    if granted and url.startswith("/api/v1/pms/grid"):
                        data = response.json()
                        assert data["property"] == hotel
                        assert {x["code"] for x in data["rooms"]} == (
                            {"A101"} if hotel == "HOTEL_A" else {"B202"}
                        )
                    if granted and url == "/api/v1/admin/dashboard":
                        assert response.json()["property"]["code"] == hotel
                    if granted and url == "/api/v1/admin/staff/overview":
                        staff = response.json()["staff"]
                        assert len(staff) == len(SERVER_ROLES), "Staff list crossed hotel boundary"
                        assert all(item["username"] in {r.lower() for r in SERVER_ROLES}
                                   for item in staff)
                    if granted and url == "/api/v1/admin/reception/reservations":
                        own = receipts[hotel]["reservation_id"]
                        others = receipts[foreign]["reservation_id"]
                        items = response.json()["items"]
                        assert any(item["id"] == own for item in items)
                        assert not any(item["id"] == others for item in items)

        assert len(seen) == 24
        assert len(set(seen.values())) == 24
        # Negative selection with a valid owner name/password, no stored cookie.
        client.cookies.clear()
        invalid = client.post("/api/v1/auth/login", json={
            "username": "owner", "password": PASSWORD,
            "tenant_code": "tenant_a", "property_code": "HOTEL_B"})
        assert invalid.status_code == 401
        assert client.get("/api/v1/auth/me").status_code == 401
        incomplete = client.post("/api/v1/auth/login", json={
            "username": "owner", "password": PASSWORD})
        assert incomplete.status_code == 401
        assert client.get("/api/v1/auth/me").status_code == 401

        # Deliberately restore only this *separate isolated TestClient process*
        # login budget. The real running server's throttle is never changed.
        auth._preview_attempts.clear()

        # A custom module checkbox is not a new operational role in shared mode.
        # Verify already-issued session rechecks DB grants immediately.
        maid_token = seen[("HOTEL_A", "MAID")]
        mutate('''
            UPDATE staff_users SET "modulePermissions"=$1::jsonb
            WHERE username='maid' AND "propertyId"=(
                SELECT id FROM properties WHERE code='HOTEL_A')
        ''', json.dumps(["OPS", "STAFF", "DASHBOARD", "FINANCE",
                         "PMS", "RESERVATIONS", "INBOX"]))
        client.cookies.clear()
        client.cookies.set(token_cookie, maid_token)
        restricted = client.get("/api/v1/auth/me")
        assert restricted.status_code == 200
        assert restricted.json()["module_permissions"] == ["OPS"]
        assert restricted.json()["module_permissions_custom"] is True
        for forbidden in ("/api/v1/admin/dashboard", "/api/v1/pms/grid",
                          "/api/v1/admin/reception/reservations",
                          "/api/v1/admin/staff/overview"):
            assert client.get(forbidden).status_code == 403, forbidden
        assert client.get("/api/v1/ops/tasks").status_code == 200
        client.cookies.clear()
        client.cookies.set(token_cookie, seen[("HOTEL_B", "MAID")])
        assert client.get("/api/v1/auth/me").json()["module_permissions"] == ["OPS"]
        mutate('''
            UPDATE staff_users SET "modulePermissions"=NULL
            WHERE username='maid' AND "propertyId"=(
                SELECT id FROM properties WHERE code='HOTEL_A')
        ''')

        # Revoke HOTEL_A reception module through the *real owner PATCH API*.
        # Active sessions must stop immediately, HOTEL_B must be unaffected.
        client.cookies.clear()
        client.cookies.set(token_cookie, seen[("HOTEL_A", "OWNER")])
        staff = client.get("/api/v1/admin/staff/overview").json()["staff"]
        reception_id = next(s["id"] for s in staff if s["username"] == "reception")
        revoked = client.patch("/api/v1/admin/staff/"+reception_id,
                               json={"module_permissions": []})
        assert revoked.status_code == 200, revoked.text
        client.cookies.clear()
        client.cookies.set(token_cookie, seen[("HOTEL_A", "RECEPTION")])
        assert client.get("/api/v1/auth/me").status_code == 401, "Old session not revoked"
        login(client, "HOTEL_A", "RECEPTION")
        assert client.get("/api/v1/auth/me").json()["module_permissions"] == []
        assert client.get("/api/v1/admin/reception/reservations").status_code == 403
        client.cookies.clear()
        client.cookies.set(token_cookie, seen[("HOTEL_B", "RECEPTION")])
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/admin/reception/reservations").status_code == 200

        # The SQL session rows and staff roles belong to the intended properties.
        mutate('''
            UPDATE staff_users SET "modulePermissions"=NULL
            WHERE username='reception' AND "propertyId"=(
                SELECT id FROM properties WHERE code='HOTEL_A')
        ''')

    print("MARINA_SHARED_ROLE_AUTH_2_HOTEL_PASS: 24 role identities, role ceiling, grants/revocation, tenant selectors and foreign-data denial")


if __name__ == "__main__":
    main()
