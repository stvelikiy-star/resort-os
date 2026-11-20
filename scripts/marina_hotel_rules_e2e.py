#!/usr/bin/env python3
"""Synthetic isolated hotel rules API contract, no external AI request or customer data."""
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import asyncpg
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
                      free_cancellation_days=7, late_cancellation_penalty="1 ночь", pets_policy="Не допускаются",
                      hotel_short_description="Тестовый отель, только синтетические данные",
                      location_address="Синтетический адрес",
                      ai_faq="Вопрос: Есть парковка?\\nОтвет: уточните у администратора")
        create = await client.put("/api/v1/admin/hotel-rules", json={"expected_version": 0, "rules": policy})
        assert create.status_code == 200, (create.status_code, create.text)
        assert create.json()["version"] == 1
        assert create.json()["rules"]["free_cancellation_days"] == 7
        assert create.json()["rules"]["hotel_short_description"] == policy["hotel_short_description"]
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
        assert read.json()["rules"]["ai_faq"] == changed["ai_faq"]
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
        from app.marina_assistant import _safe_property_rules
        dsn = os.environ["DATABASE_URL"].replace("?schema=public", "")
        assert urlsplit(dsn).hostname in {"127.0.0.1", "localhost"}
        pool = await asyncpg.create_pool(dsn)
        try:
            fake_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=pool)))
            for role in ("OWNER", "MANAGER", "RECEPTION"):
                context = await _safe_property_rules(fake_request, {"property_code": "MARINA_FULL_CI", "role": role})
                assert context["available"] is True and context["version"] == 2, context
                assert context["rules"]["pets_policy"] == changed["pets_policy"], context
                assert context["rules"]["location_address"] == changed["location_address"], context
                assert context["rules"]["ai_faq"] == changed["ai_faq"], context
            from fastapi import HTTPException
            try:
                await _safe_property_rules(fake_request, {"property_code": "MARINA_FULL_CI", "role": "MAID"})
            except HTTPException as exc:
                assert exc.status_code == 403
            else:
                raise AssertionError("MAID must not access staff assistant hotel rules")
            foreign = await _safe_property_rules(fake_request, {"property_code": "FOREIGN_HOTEL", "role": "OWNER"})
            assert foreign["available"] is False, foreign
        finally:
            await pool.close()
        print("MARINA_HOTEL_RULES_E2E_PASS: 401, owner save/read, 409, 422, and scoped AI context with verified hotel FAQ")
if __name__ == "__main__":
    asyncio.run(main())
