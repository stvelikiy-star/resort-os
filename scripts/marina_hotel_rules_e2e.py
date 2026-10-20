#!/usr/bin/env python3
"""Synthetic isolated hotel rules API contract, no external AI request or customer data."""
import asyncio
import os
from urllib.parse import urlsplit

import httpx

async def main():
    api = os.environ.get("MARINA_BOOKING_TEST_API", "")
    url = urlsplit(api)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost"} or os.environ.get("PROPERTY_CODE") != "MARINA_FULL_CI":
        raise SystemExit("Rules smoke may only run on local MARINA_FULL_CI")
    async with httpx.AsyncClient(base_url=api, timeout=15) as client:
        unsigned = await client.get("/api/v1/admin/hotel-rules")
        assert unsigned.status_code == 401, (unsigned.status_code, unsigned.text)
        login = await client.post("/api/v1/auth/login", json={
            "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
            "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"]
        })
        assert login.status_code == 200, (login.status_code, login.text)
        response = await client.get("/api/v1/admin/hotel-rules")
        assert response.status_code == 200, (response.status_code, response.text)
        state = response.json()
        assert state["property_code"] == "MARINA_FULL_CI" and state["version"] == 0, state
        policy = dict(state["rules"])
        policy.update(prepayment_type="FIRST_NIGHT", prepayment_value=0,
                      free_cancellation_days=7, late_cancellation_penalty="1 ночь", pets_policy="Не допускаются")
        create = await client.put("/api/v1/admin/hotel-rules", json={"expected_version": 0, "rules": policy})
        assert create.status_code == 200, (create.status_code, create.text)
        assert create.json()["version"] == 1
        assert create.json()["rules"]["free_cancellation_days"] == 7
        conflict = await client.put("/api/v1/admin/hotel-rules", json={"expected_version": 0, "rules": policy})
        assert conflict.status_code == 409, (conflict.status_code, conflict.text)
        invalid = await client.put("/api/v1/admin/hotel-rules", json={
            "expected_version": 1, "rules": {**policy, "prepayment_type": "PERCENT", "prepayment_value": 110}
        })
        assert invalid.status_code == 422, (invalid.status_code, invalid.text)
        changed = dict(policy, pets_policy="Согласовывать с администратором")
        update = await client.put("/api/v1/admin/hotel-rules", json={"expected_version": 1, "rules": changed})
        assert update.status_code == 200 and update.json()["version"] == 2, update.text
        read = await client.get("/api/v1/admin/hotel-rules")
        assert read.status_code == 200 and read.json()["rules"]["pets_policy"] == changed["pets_policy"]
        print("MARINA_HOTEL_RULES_E2E_PASS: 401, owner save/read, revision 409, invalid 422, update")
if __name__ == "__main__":
    asyncio.run(main())
