#!/usr/bin/env python3
"""Concurrent booking race acceptance: local disposable MARINA_FULL_CI only.

Two independent OWNER sessions commit an identical room/date concurrently.
Exactly one succeeds; the other must be rejected with HTTP 409.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
import os
from urllib.parse import urlsplit

import httpx


API_PATH = "/api/v1/admin/pms/reservations/new"


def validate_target() -> str:
    origin = os.environ.get("MARINA_BOOKING_TEST_API", "")
    url = urlsplit(origin)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "localhost"}
        or url.username is not None
        or url.password is not None
        or url.path not in {"", "/"}
        or url.query or url.fragment
        or os.environ.get("APP_ENV") not in {"ci", "staging"}
        or os.environ.get("PROPERTY_CODE") != "MARINA_FULL_CI"
    ):
        raise RuntimeError("Only disposable localhost MARINA_FULL_CI accepts concurrent booking writes")
    return origin.rstrip("/")


async def login(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/auth/login", json={
        "username": os.environ["BOOTSTRAP_OWNER_USERNAME"],
        "password": os.environ["BOOTSTRAP_OWNER_PASSWORD"],
    })
    assert response.status_code == 200, (response.status_code, response.text)


async def main() -> None:
    origin = validate_target()
    async with (
        httpx.AsyncClient(base_url=origin, timeout=25) as first,
        httpx.AsyncClient(base_url=origin, timeout=25) as second,
    ):
        await asyncio.gather(login(first), login(second))
        check_in = date.today() + timedelta(days=41)
        check_out = check_in + timedelta(days=2)
        availability = await first.get("/api/v1/booking/check-availability", params={
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": 2,
        })
        assert availability.status_code == 200, (availability.status_code, availability.text)
        room_id = next((
            room["id"]
            for category in availability.json().get("results", [])
            for room in category.get("available_rooms", [])
        ), None)
        assert room_id, "No available synthetic room for concurrent booking"
        base = {
            "room_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "adults": 2,
            "children": 0,
        }
        quote_response = await first.post(API_PATH + "/preview", json=base)
        assert quote_response.status_code == 200, (quote_response.status_code, quote_response.text)
        quote = quote_response.json()
        assert quote["can_commit"] is True and quote["pricing"]["total_kgs"] > 0, quote
        body = {
            **base,
            "guest_name": "Synthetic Race Guest",
            "phone": "+996555009901",
            "expected_total_kgs": quote["pricing"]["total_kgs"],
            "expected_pricing_source": quote["pricing"]["source"],
        }
        # Two different authenticated HTTP clients, no mock of the DB or API.
        responses = await asyncio.gather(
            first.post(API_PATH + "/commit", json=body),
            second.post(API_PATH + "/commit", json=body),
        )
        statuses = sorted(r.status_code for r in responses)
        assert statuses == [201, 409], [
            (r.status_code, r.text[:400]) for r in responses
        ]
        won = next(r.json() for r in responses if r.status_code == 201)
        rejected = next(r.json() for r in responses if r.status_code == 409)
        assert rejected["detail"]["code"] in {"ROOM_CONFLICT", "ROOM_CONFLICT_RACE"}, rejected
        grid = await first.get("/api/v1/pms/grid", params={
            "start": check_in.isoformat(), "end": check_out.isoformat(),
        })
        assert grid.status_code == 200, (grid.status_code, grid.text)
        matching = [
            block
            for room in grid.json()["rooms"]
            if room["id"] == room_id
            for block in room.get("blocks", [])
            if block.get("reservation_id") == won["reservation_id"]
        ]
        assert len(matching) == 1, f"Expected exactly one winner block, got {len(matching)}"
        print("MARINA_CONCURRENT_BOOKING_E2E_PASS: one 201, one 409, one inventory block")


if __name__ == "__main__":
    asyncio.run(main())
