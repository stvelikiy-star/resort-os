#!/usr/bin/env python3
"""Synthetic E2E for Chef OS cutoff snapshots and late-change deltas.

Runs only against the isolated release/staging database. It deliberately proves
that unset owner meal times fail closed, that OWNER may explicitly force a
baseline for exceptional operation, and that a later entitlement edit changes
only the delta while the frozen baseline remains immutable.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date
from typing import Any

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ["SMOKE_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["SMOKE_OWNER_PASSWORD"]
D0 = date.fromisoformat(os.environ["D0"])
DATABASE_URL = os.environ["DATABASE_URL"].split("?", 1)[0]


def ok(response: httpx.Response, label: str, expected: int | tuple[int, ...] = (200, 201)) -> dict[str, Any]:
    codes = (expected,) if isinstance(expected, int) else expected
    if response.status_code not in codes:
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        raise AssertionError(f"{label}: HTTP {response.status_code}: {detail}")
    return response.json() if response.content else {}


async def release_stay() -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        stay_id = await conn.fetchval(
            '''SELECT s.id
               FROM reservations r
               JOIN stays s ON s."reservationId"=r.id AND s.status='ACTIVE'
               WHERE r.status='CHECKED_IN' AND COALESCE(r.notes,'') LIKE '%Release 0.60 E2E%'
               ORDER BY r."createdAt" DESC LIMIT 1'''
        )
        assert stay_id, "release E2E active stay is required"
        return str(stay_id)
    finally:
        await conn.close()


def breakfast_snapshot(body: dict[str, Any]) -> dict[str, Any]:
    return next(
        meal
        for day in body["days"]
        if day["service_date"] == str(D0)
        for meal in day["meals"]
        if meal["meal_type"] == "BREAKFAST"
    )


async def main() -> None:
    stay_id = await release_stay()
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as owner:
        login = ok(
            await owner.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}),
            "owner login",
        )
        assert login["role"] == "OWNER"

        entitlements = ok(
            await owner.get(f"/api/v1/dining/stays/{stay_id}/entitlements"),
            "load release dining entitlement",
        )
        breakfast = next(
            item
            for item in entitlements["items"]
            if item["service_date"] == str(D0) and item["meal_type"] == "BREAKFAST" and item["status"] == "ACTIVE"
        )
        entitlement_id = breakfast["id"]
        original_adults = int(breakfast["adult_portions"])
        original_children = int(breakfast["child_portions"])

        before = ok(
            await owner.get(f"/api/v1/dining/production-snapshots?from_date={D0}&through_date={D0}"),
            "production snapshot state before freeze",
        )
        before_breakfast = breakfast_snapshot(before)
        assert before_breakfast["state"] == "OPEN"
        assert before_breakfast["current_adult_portions"] >= original_adults

        ordinary = await owner.post(
            "/api/v1/dining/production-snapshots",
            json={"service_date": str(D0), "meal_type": "BREAKFAST"},
        )
        if before_breakfast["cutoff_status"] == "UNCONFIGURED":
            assert ordinary.status_code == 409, ordinary.text
            assert ordinary.json().get("detail", {}).get("code") == "DINING_PRODUCTION_SNAPSHOT_TIME_NOT_CONFIGURED"
        elif before_breakfast["cutoff_status"] == "BEFORE_CUTOFF":
            assert ordinary.status_code == 409, ordinary.text
            assert ordinary.json().get("detail", {}).get("code") == "DINING_PRODUCTION_SNAPSHOT_TOO_EARLY"
        else:
            assert ordinary.status_code in {200, 201}, ordinary.text

        if ordinary.status_code in {200, 201}:
            frozen = ordinary.json()
        else:
            frozen = ok(
                await owner.post(
                    "/api/v1/dining/production-snapshots",
                    json={
                        "service_date": str(D0),
                        "meal_type": "BREAKFAST",
                        "force_before_cutoff": True,
                        "notes": "Synthetic release-gate Chef OS baseline",
                    },
                ),
                "force production snapshot",
            )
            assert frozen["forced"] is True

        assert frozen["state"] == "FROZEN"
        frozen_total = int(frozen["frozen_total_portions"])
        frozen_adult = int(frozen["frozen_adult_portions"])
        frozen_child = int(frozen["frozen_child_portions"])
        assert frozen_total == frozen_adult + frozen_child

        idempotent = ok(
            await owner.post(
                "/api/v1/dining/production-snapshots",
                json={
                    "service_date": str(D0),
                    "meal_type": "BREAKFAST",
                    "force_before_cutoff": True,
                    "notes": "Must not rewrite the baseline",
                },
            ),
            "idempotent production snapshot",
        )
        assert idempotent["idempotent"] is True
        assert int(idempotent["frozen_total_portions"]) == frozen_total

        changed = ok(
            await owner.patch(
                f"/api/v1/dining/entitlements/{entitlement_id}",
                json={
                    "adult_portions": original_adults + 1,
                    "child_portions": original_children,
                    "notes": "Synthetic late Chef OS delta",
                },
            ),
            "late dining entitlement change",
        )
        assert changed["adult_portions"] == original_adults + 1

        after = ok(
            await owner.get(f"/api/v1/dining/production-snapshots?from_date={D0}&through_date={D0}"),
            "production snapshot after late change",
        )
        after_breakfast = breakfast_snapshot(after)
        assert after_breakfast["state"] == "FROZEN"
        assert after_breakfast["frozen_total_portions"] == frozen_total
        assert after_breakfast["delta_adult_portions"] == 1
        assert after_breakfast["delta_total_portions"] == 1
        assert after_breakfast["changed_since_snapshot"] is True

        print(
            "Chef production snapshot E2E PASS:",
            {
                "stay_id": stay_id,
                "entitlement_id": entitlement_id,
                "snapshot_id": frozen["id"],
                "frozen_total": frozen_total,
                "late_delta": after_breakfast["delta_total_portions"],
                "cutoff_status": before_breakfast["cutoff_status"],
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
