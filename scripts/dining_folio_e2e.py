#!/usr/bin/env python3
"""Synthetic E2E for explicit restaurant order -> guest Folio posting.

Proves the financial boundary: posting creates one idempotent OPEN receivable,
never a Payment, and cancelling the unpaid order voids that open charge.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import asyncpg
import httpx

BASE_URL = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
OWNER_USERNAME = os.environ["SMOKE_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["SMOKE_OWNER_PASSWORD"]
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


async def context() -> dict[str, str]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            '''SELECT s.id AS stay_id,r.id AS reservation_id
               FROM reservations r
               JOIN stays s ON s."reservationId"=r.id AND s.status='ACTIVE'
               WHERE r.status='CHECKED_IN' AND COALESCE(r.notes,'') LIKE '%Release 0.60 E2E%'
               ORDER BY r."createdAt" DESC LIMIT 1'''
        )
        assert row, "release E2E active stay is required"
        return {"stay_id": str(row["stay_id"]), "reservation_id": str(row["reservation_id"])}
    finally:
        await conn.close()


async def payment_count(reservation_id: str) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return int(await conn.fetchval('SELECT count(*)::int FROM payments WHERE "reservationId"=$1', reservation_id) or 0)
    finally:
        await conn.close()


async def charge_status(order_id: str) -> tuple[int, str | None]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            '''SELECT status FROM guest_folio_charges
               WHERE "sourceType"='KITCHEN_ORDER' AND "sourceId"=$1 ORDER BY "createdAt"''',
            order_id,
        )
        return len(rows), rows[-1]["status"] if rows else None
    finally:
        await conn.close()


async def main() -> None:
    ctx = await context()
    before_payments = await payment_count(ctx["reservation_id"])

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as owner:
        login = ok(
            await owner.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD}),
            "owner login",
        )
        assert login["role"] == "OWNER"

        ok(await owner.post("/api/v1/kitchen/menu/bootstrap-draft"), "bootstrap menu")
        menu = ok(await owner.get("/api/v1/kitchen/menu"), "load menu")
        item = menu["items"][0]
        ok(
            await owner.patch(
                f"/api/v1/kitchen/menu/{item['id']}",
                json={"is_active": True, "is_draft": False},
            ),
            "approve menu item",
        )

        order = ok(
            await owner.post(
                "/api/v1/kitchen/orders",
                json={
                    "source": "MANAGER",
                    "stay_id": ctx["stay_id"],
                    "guest_count": 1,
                    "notes": "Dining Folio E2E explicit posting",
                    "items": [{"menu_item_id": item["id"], "quantity": 1}],
                },
            ),
            "create stay-linked restaurant order",
        )
        order_id = order["id"]

        candidates = ok(await owner.get("/api/v1/dining/folio-orders"), "list folio candidates")
        candidate = next(entry for entry in candidates["items"] if entry["id"] == order_id)
        assert candidate["eligible_to_post"] is True
        assert candidate["folio_charge_id"] is None
        assert candidate["financial_truth"] == "NOT_POSTED"

        posted = ok(
            await owner.post(f"/api/v1/dining/orders/{order_id}/folio"),
            "post restaurant order to folio",
        )
        assert posted["payment_created"] is False
        assert posted["idempotent_replay"] is False
        assert posted["financial_truth"] == "OPEN_FOLIO_CHARGE_NOT_PAYMENT"

        replay = ok(
            await owner.post(f"/api/v1/dining/orders/{order_id}/folio"),
            "idempotent folio replay",
        )
        assert replay["charge_id"] == posted["charge_id"]
        assert replay["idempotent_replay"] is True
        assert replay["payment_created"] is False

        charge_count, status_before_cancel = await charge_status(order_id)
        assert charge_count == 1
        assert status_before_cancel == "OPEN"
        assert await payment_count(ctx["reservation_id"]) == before_payments

        cancelled = ok(
            await owner.patch(f"/api/v1/kitchen/orders/{order_id}/status", json={"status": "CANCELLED"}),
            "cancel unpaid restaurant order",
        )
        assert cancelled["status"] == "CANCELLED"
        charge_count_after, status_after_cancel = await charge_status(order_id)
        assert charge_count_after == 1
        assert status_after_cancel == "VOID"
        assert await payment_count(ctx["reservation_id"]) == before_payments

        print(
            "Dining Folio E2E PASS:",
            {
                "stay_id": ctx["stay_id"],
                "reservation_id": ctx["reservation_id"],
                "order_id": order_id,
                "charge_id": posted["charge_id"],
                "payment_count_unchanged": before_payments,
                "cancelled_charge_status": status_after_cancel,
            },
        )


if __name__ == "__main__":
    asyncio.run(main())
