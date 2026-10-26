#!/usr/bin/env python3
"""Synthetic MARINA only: owner creates, grants, revokes and disables staff access."""
import asyncio
import os
from urllib.parse import urlsplit

import httpx


async def main():
    origin = os.environ.get("MARINA_BOOKING_TEST_API", "")
    parsed = urlsplit(origin)
    assert parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}, "Disposable localhost only"
    assert os.environ.get("APP_ENV") in {"ci", "staging"}
    assert os.environ.get("PROPERTY_CODE") == "MARINA_FULL_CI", "Never test against a customer property"

    username = "synthetic-rbac-maid"
    password = "Synthetic-RBAC-Maid-2026!"
    url = "/api/v1/admin/staff"
    async with httpx.AsyncClient(base_url=origin, timeout=20) as owner:
        login = await owner.post("/api/v1/auth/login", json={
            "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
            "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"],
        })
        assert login.status_code == 200, (login.status_code, login.text)
        created = await owner.post(url, json={
            "username": username, "display_name": "Synthetic RBAC Maid",
            "password": password, "role": "MAID",
        })
        assert created.status_code == 201, (created.status_code, created.text)
        staff_id = created.json()["id"]
        staff_url = f"{url}/{staff_id}"

        async with httpx.AsyncClient(base_url=origin, timeout=20) as staff:
            signed_in = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
            assert signed_in.status_code == 200, (signed_in.status_code, signed_in.text)
            denied = await staff.get("/api/v1/pms/grid", params={"start": "2026-11-01", "end": "2026-11-02"})
            assert denied.status_code == 403, (denied.status_code, denied.text)
            assert (await staff.post(url, json={
                "username": "forbidden-child", "display_name": "Forbidden Child",
                "password": password, "role": "MAID",
            })).status_code == 403
            grant = await owner.patch(staff_url, json={"module_permissions": ["PMS"]})
            assert grant.status_code == 200, (grant.status_code, grant.text)
            assert grant.json()["module_permissions"] == ["PMS"]
            assert (await staff.get("/api/v1/auth/me")).status_code == 401, "Grant must revoke old session"
            again = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
            assert again.status_code == 200, (again.status_code, again.text)
            allowed = await staff.get("/api/v1/pms/grid", params={"start": "2026-11-01", "end": "2026-11-02"})
            assert allowed.status_code == 200, (allowed.status_code, allowed.text)
            # Module grants may allow calendar access but never owner-only cancellation.
            cancel = await staff.post("/api/v1/admin/pms/reservations/00000000-0000-0000-0000-000000000000/cancel")
            assert cancel.status_code == 403, (cancel.status_code, cancel.text)
            if os.environ.get("ENABLE_PAYMENT_OPERATIONS", "false").lower() == "true":
                # PMS module permission alone may never create a RECEIVED payment.
                denied_payment = await staff.post(
                    "/api/v1/admin/booking/reservations/00000000-0000-0000-0000-000000000000/payments",
                    json={"amount_kgs": 100, "method": "CASH", "idempotency_key": "synthetic-denied-payment"},
                )
                assert denied_payment.status_code == 403, (denied_payment.status_code, denied_payment.text)
                denied_review = await staff.get(
                    "/api/v1/admin/booking/reservations/00000000-0000-0000-0000-000000000000/cancellation-finance-review",
                )
                assert denied_review.status_code == 403, (denied_review.status_code, denied_review.text)
            assert (await staff.patch(staff_url, json={"active": False})).status_code == 403

            revoked = await owner.patch(staff_url, json={"module_permissions": []})
            assert revoked.status_code == 200 and revoked.json()["module_permissions"] == [], revoked.text
            assert (await staff.get("/api/v1/auth/me")).status_code == 401, "Revoking PMS must revoke existing session"
            again = await staff.post("/api/v1/auth/login", json={"username": username, "password": password})
            assert again.status_code == 200, (again.status_code, again.text)
            denied_again = await staff.get("/api/v1/pms/grid", params={"start": "2026-11-01", "end": "2026-11-02"})
            assert denied_again.status_code == 403, (denied_again.status_code, denied_again.text)

            deactivated = await owner.patch(staff_url, json={"active": False})
            assert deactivated.status_code == 200 and deactivated.json()["active"] is False, deactivated.text
            assert (await staff.get("/api/v1/auth/me")).status_code == 401
            assert (await staff.post("/api/v1/auth/login", json={
                "username": username, "password": password,
            })).status_code == 401

    print("MARINA_STAFF_ACCESS_E2E_PASS: staff login, grant, strict cancellation, session revocation, re-login, deactivation")


if __name__ == "__main__":
    asyncio.run(main())
