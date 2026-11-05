#!/usr/bin/env python3
"""P0: REAL two-hotel staff lifecycle through canonical FastAPI and PostgreSQL.

Owner creates all six assignable operational roles in BOTH hotels; same
usernames cannot bleed into another hotel. Tests login/permissions, role
change, grant/revoke, credential rotation, deactivation and reactivation.
Zero mocks, isolated localhost PostgreSQL ONLY. No production data.
"""
import asyncio
from collections import Counter
import uuid

import asyncpg
from fastapi.testclient import TestClient

from app import auth
from app.app_entry import app
from app.staff_control import MANAGED_ROLES
from marina_shared_live_browser_db import PASSWORD, SERVER_ROLES, dsn

USERNAME_PREFIX = "p0-cycle-"
ASSIGNABLE = ("MANAGER", "RECEPTION", "MAID", "TECHNICIAN", "COOK", "WAITER")
assert set(ASSIGNABLE) == set(MANAGED_ROLES)
assert len(SERVER_ROLES) == 12
assert len(ASSIGNABLE) == 6


def must(response, status, label):
    assert response.status_code == status, (
        label, response.status_code, response.text[:240],
    )
    return response.json() if response.content else {}


def main():
    # The seed script's dsn() proves the database host, name, env and password
    # are disposable test-only; refuse every external or existing customer DB.
    dsn()
    assert auth.MARINA_SHARED_AUTH_PREVIEW_ENABLED and auth.MARINA_TENANT_CONTEXT_ENABLED
    assert auth.COOKIE_SECURE
    owners = {}
    identities = {}
    original_tokens = {}
    passwords = {}
    with TestClient(app, base_url="https://localhost:18000") as client:
        def session(token):
            client.cookies.clear()
            if token:
                client.cookies.set(auth.SESSION_COOKIE, token)

        def request(token, method, path, **kwargs):
            session(token)
            return client.request(method, path, **kwargs)

        def login(hotel, username, password, *, expected=200):
            session(None)
            response = client.post("/api/v1/auth/login", json={
                "tenant_code": "tenant_" + hotel.lower(),
                "property_code": "HOTEL_" + hotel,
                "username": username,
                "password": password,
            })
            data = must(response, expected, hotel + "/" + username + " login")
            if expected != 200:
                assert client.get("/api/v1/auth/me").status_code == 401
                return None
            token = client.cookies.get(auth.SESSION_COOKIE)
            assert isinstance(token, str) and token.startswith("ms1.")
            assert data["property_code"] == "HOTEL_" + hotel
            return token

        # Independent real OWNER sessions are the ONLY source of staff grants.
        for hotel in "AB":
            token = login(hotel, "owner", PASSWORD)
            me = must(request(token, "GET", "/api/v1/auth/me"), 200, "owner session")
            assert me["role"] == "OWNER"
            owners[hotel] = {"token": token, "property_id": me["property_id"],
                             "tenant_id": me["tenant_id"]}
        assert owners["A"]["property_id"] != owners["B"]["property_id"]
        assert owners["A"]["tenant_id"] != owners["B"]["tenant_id"]

        for role in ASSIGNABLE:
            username = USERNAME_PREFIX + role.lower()
            for hotel in "AB":
                key = (hotel, role)
                pwd = "synthetic-ci-staff-" + hotel + "-" + role.lower() + "-2026!"
                passwords[key] = pwd
                new = must(request(owners[hotel]["token"], "POST",
                    "/api/v1/admin/staff", json={
                        "username": username,
                        "display_name": "Synthetic " + role + " HOTEL_" + hotel,
                        "password": pwd,
                        "role": role,
                    }), 201, hotel + "/" + role + " owner create")
                assert new["role"] == role and new["username"] == username
                assert new["active"] is True
                assert "password" not in new and "password_hash" not in new
                assert uuid.UUID(new["id"])
                identities[key] = new["id"]
                assert must(request(owners[hotel]["token"], "POST",
                    "/api/v1/admin/staff", json={
                        "username": username, "display_name": "Duplicate " + role,
                        "password": pwd, "role": role,
                    }), 409, "duplicate username within same hotel")
                token = login(hotel, username, pwd)
                original_tokens[key] = token
                me = must(request(token, "GET", "/api/v1/auth/me"),
                          200, hotel + "/" + role + " auth/me")
                assert me["role"] == role and me["property_code"] == "HOTEL_" + hotel
                assert me["property_id"] == owners[hotel]["property_id"]
                assert me["tenant_id"] == owners[hotel]["tenant_id"]
                # A staff member cannot create/edit other users, even if the
                # role has read-only STAFF overview (MANAGER).
                must(request(token, "POST", "/api/v1/admin/staff", json={
                    "username": "forbidden-new-" + hotel.lower(),
                    "display_name": "Forbidden",
                    "password": pwd, "role": "MAID",
                }), 403, "nonowner cannot create staff")
                must(request(token, "PATCH",
                    "/api/v1/admin/staff/" + new["id"],
                    json={"active": False}), 403, "nonowner cannot modify staff")
                expected_overview = 200 if role == "MANAGER" else 403
                must(request(token, "GET", "/api/v1/admin/staff/overview"),
                     expected_overview, role + " overview role ceiling")

        assert len(identities) == 12
        assert len(set(identities.values())) == 12
        # Same username in two hotels resolves to unrelated identities and
        # hotel-specific credentials, not a global user namespace.
        for role in ASSIGNABLE:
            assert identities[("A", role)] != identities[("B", role)]
        login("A", USERNAME_PREFIX + "maid", passwords[("B", "MAID")], expected=401)
        # A valid owner cannot mutate another property's user by ID or
        # bypass tenancy through caller-supplied selector headers.
        must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + identities[("B", "MAID")],
            headers={"X-Property-Id": owners["B"]["property_id"]},
            json={"active": False}), 404, "foreign staff ID is concealed")
        must(request(owners["B"]["token"], "PATCH",
            "/api/v1/admin/staff/" + identities[("A", "MAID")],
            json={"module_permissions": []}), 404, "reverse foreign staff ID denied")
        owner_id = next(
            x["id"] for x in must(request(owners["A"]["token"], "GET",
                "/api/v1/admin/staff/overview"), 200, "owner A roster")["staff"]
            if x["role"] == "OWNER"
        )
        must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + owner_id,
            json={"active": False}), 403, "owner cannot disable owner account")

        a_user = identities[("A", "MAID")]
        a_pwd = passwords[("A", "MAID")]
        b_maid_token = original_tokens[("B", "MAID")]
        # Changing a role MUST invalidate the already issued session,
        # then the same human must login again under their NEW role.
        promoted = must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + a_user,
            json={"role": "RECEPTION", "display_name": "Synthetic Promoted Reception"}),
            200, "promote A maid")
        assert promoted["role"] == "RECEPTION"
        must(request(original_tokens[("A", "MAID")], "GET",
             "/api/v1/auth/me"), 401, "old MAID session revoked")
        promoted_token = login("A", USERNAME_PREFIX + "maid", a_pwd)
        must(request(promoted_token, "GET",
             "/api/v1/admin/reception/reservations"), 200,
             "promoted A reception can use reservation read")
        must(request(promoted_token, "GET", "/api/v1/ops/tasks"),
             403, "old MAID permissions not retained")
        must(request(b_maid_token, "GET", "/api/v1/ops/tasks"),
             200, "B MAID still authorized after A role change")

        # Explicit empty grant revokes PMS immediately AND after new login.
        revoked = must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + a_user,
            json={"module_permissions": []}), 200, "A receptionist revoke")
        assert revoked["module_permissions"] == []
        must(request(promoted_token, "GET", "/api/v1/auth/me"),
             401, "permission change invalidates session")
        restricted_token = login("A", USERNAME_PREFIX + "maid", a_pwd)
        restricted = must(request(restricted_token, "GET",
            "/api/v1/auth/me"), 200, "new empty grants")
        assert restricted["module_permissions"] == []
        must(request(restricted_token, "GET",
             "/api/v1/admin/reception/reservations"), 403,
             "revoked PMS permission remains denied")

        # Password rotation must revoke active sessions; old passwords must
        # never work, and all secrets are absent from audit payloads.
        changed = a_pwd + "-rotated"
        must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + a_user,
            json={"password": changed}), 200, "A password rotation")
        must(request(restricted_token, "GET", "/api/v1/auth/me"),
             401, "rotated password invalidates old session")
        login("A", USERNAME_PREFIX + "maid", a_pwd, expected=401)
        rotated_token = login("A", USERNAME_PREFIX + "maid", changed)

        # Disable immediately blocks both active session and fresh login.
        disabled = must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + a_user,
            json={"active": False}), 200, "A account disabled")
        assert disabled["active"] is False
        must(request(rotated_token, "GET", "/api/v1/auth/me"),
             401, "disabled staff session cannot be reused")
        login("A", USERNAME_PREFIX + "maid", changed, expected=401)
        # A legitimate owner can deliberately re-enable this same hotel user.
        restored = must(request(owners["A"]["token"], "PATCH",
            "/api/v1/admin/staff/" + a_user,
            json={"active": True, "module_permissions": ["PMS", "RESERVATIONS"]}),
            200, "owner reenabled A receptionist")
        assert restored["active"] is True and set(restored["module_permissions"]) == {
            "PMS", "RESERVATIONS"
        }
        after = login("A", USERNAME_PREFIX + "maid", changed)
        must(request(after, "GET",
             "/api/v1/admin/reception/reservations"), 200,
             "reenabled receptionist has explicitly restored grants")
        must(request(b_maid_token, "GET", "/api/v1/ops/tasks"),
             200, "B hotel MAID unaffected by A disable/re-enable")
        # No other hotel's employee is visible in the owner's staff overview.
        for hotel in "AB":
            rows = must(request(owners[hotel]["token"], "GET",
                "/api/v1/admin/staff/overview"), 200, "hotel-local roster")["staff"]
            for role in ASSIGNABLE:
                target = next(x for x in rows if x["id"] == identities[(hotel, role)])
                assert target["username"] == USERNAME_PREFIX + role.lower()
            foreign = "B" if hotel == "A" else "A"
            assert all(x["id"] not in {identities[(foreign, role)]
                       for role in ASSIGNABLE} for x in rows)

    asyncio.run(verify_database(owners, identities, passwords, a_pwd, changed))
    print(
        "PASS: TWO hotel owners created 6 managed roles each; 12 independent "
        "staff records + real sessions, same usernames, foreign IDs 404; "
        "role change / grant revoke / password rotation / disable / reenable "
        "invalidate sessions; second hotel's users and audits stay isolated."
    )


async def verify_database(owners, identities, passwords, first_password, new_password):
    conn = await asyncpg.connect(dsn())
    try:
        for hotel in "AB":
            property_id = uuid.UUID(owners[hotel]["property_id"])
            records = await conn.fetch(
                '''SELECT id,username,role::text AS role,"isActive","propertyId"
                   FROM staff_users
                   WHERE "propertyId"=$1 AND username LIKE $2''',
                property_id, USERNAME_PREFIX + "%",
            )
            assert len(records) == len(ASSIGNABLE)
            assert {x["username"] for x in records} == {
                USERNAME_PREFIX + r.lower() for r in ASSIGNABLE
            }
            assert {x["id"] for x in records} == {
                uuid.UUID(identities[(hotel, r)]) for r in ASSIGNABLE
            }
            actions = await conn.fetch(
                '''SELECT action,"resourceId","afterJson"::text AS audit
                   FROM audit_logs WHERE "propertyId"=$1
                   AND resource='StaffUser' AND source='STAFF_MANAGEMENT' ''',
                property_id,
            )
            assert Counter(x["action"] for x in actions)["CREATE_STAFF_USER"] == 6
            # Every mutation is recorded under its owner's actual property.
            if hotel == "A":
                assert Counter(x["action"] for x in actions)["UPDATE_STAFF_ACCESS"] >= 5
                assert await conn.fetchval(
                    '''SELECT count(*)::int FROM auth_sessions
                       WHERE "userId"=$1 AND "revokedAt" IS NOT NULL''',
                    uuid.UUID(identities[("A", "MAID")]),
                ) >= 4
            secret_values = [first_password, new_password]
            secret_values += [p for (h, _role), p in passwords.items() if h == hotel]
            for row in actions:
                for secret in secret_values:
                    assert secret not in (row["audit"] or ""), "Staff secret in audit log"
    finally:
        await conn.close()


if __name__ == "__main__":
    main()
