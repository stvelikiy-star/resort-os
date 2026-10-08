#!/usr/bin/env python3
"""Two-tenant MARINA SMART staging isolation gate.

This gate is intentionally staging-only. It performs authenticated reads and
cross-tenant denial probes. The quote probes must fail before any mutation and
require an explicit staging confirmation string.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta
from urllib.parse import urlsplit
from uuid import UUID

import httpx

CONFIRMATION = "I_UNDERSTAND_STAGING_ONLY"


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def validate_base_url(value: str) -> str:
    parsed = urlsplit(value)
    allowed_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not allowed_local:
        raise RuntimeError("MARINA_STAGING_BASE_URL must use HTTPS outside local CI")
    if not parsed.netloc:
        raise RuntimeError("MARINA_STAGING_BASE_URL must include a host")
    return value.rstrip("/")


def validate_uuid(name: str, value: str) -> str:
    try:
        return str(UUID(value))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a UUID") from exc


async def login(client: httpx.AsyncClient, username: str, password: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    if response.status_code != 200:
        raise RuntimeError(f"login failed for {username}: HTTP {response.status_code}")
    me = await client.get("/api/v1/auth/me")
    if me.status_code != 200:
        raise RuntimeError(f"/auth/me failed for {username}: HTTP {me.status_code}")
    body = me.json()
    if body.get("role") not in {"OWNER", "MANAGER"}:
        raise RuntimeError(f"{username} must be OWNER or MANAGER for this gate")
    for key in ("tenant_id", "property_id", "property_code"):
        if not body.get(key):
            raise RuntimeError(f"{username} /auth/me has no trusted {key}")
    return body


async def get_json(
    client: httpx.AsyncClient,
    path: str,
    *,
    params: dict | None = None,
    expected: int = 200,
    label: str,
) -> dict:
    response = await client.get(path, params=params)
    if response.status_code != expected:
        raise RuntimeError(f"{label}: expected HTTP {expected}, found {response.status_code}")
    return response.json()


async def expect_denied(
    client: httpx.AsyncClient,
    path: str,
    *,
    method: str = "GET",
    json_body: dict | None = None,
    label: str,
) -> None:
    if method == "POST":
        response = await client.post(path, json=json_body or {})
    else:
        response = await client.get(path)
    if response.status_code not in {403, 404}:
        raise RuntimeError(
            f"{label}: cross-tenant request must be denied with 403/404, "
            f"found HTTP {response.status_code}"
        )


async def verify_account(
    client: httpx.AsyncClient,
    user: dict,
    expected_property_code: str,
    own_reservation_id: str,
    own_request_id: str,
    foreign_reservation_id: str,
    foreign_request_id: str,
    start: str,
    end: str,
) -> None:
    if user["property_code"] != expected_property_code:
        raise RuntimeError(
            f"trusted property mismatch: expected {expected_property_code}, "
            f"found {user['property_code']}"
        )

    grid = await get_json(
        client,
        "/api/v1/pms/grid",
        params={"start": start, "end": end},
        label=f"{expected_property_code} own grid",
    )
    if grid.get("property") != expected_property_code:
        raise RuntimeError(
            f"{expected_property_code} grid crossed property boundary: "
            f"{grid.get('property')}"
        )
    if not isinstance(grid.get("rooms"), list):
        raise RuntimeError(f"{expected_property_code} grid rooms is not a list")

    reception = await get_json(
        client,
        "/api/v1/admin/reception/reservations",
        params={"limit": 500},
        label=f"{expected_property_code} own reception",
    )
    own_ids = {str(item.get("id")) for item in reception.get("items", [])}
    if own_reservation_id not in own_ids:
        raise RuntimeError(
            f"{expected_property_code} cannot see its own seeded reservation {own_reservation_id}"
        )
    if foreign_reservation_id in own_ids:
        raise RuntimeError(
            f"{expected_property_code} reception returned foreign reservation {foreign_reservation_id}"
        )

    requests = await get_json(
        client,
        "/api/v1/admin/booking/requests",
        params={"limit": 250},
        label=f"{expected_property_code} own booking requests",
    )
    request_ids = {str(item.get("id")) for item in requests.get("items", [])}
    if own_request_id not in request_ids:
        raise RuntimeError(
            f"{expected_property_code} cannot see its own seeded request {own_request_id}"
        )
    if foreign_request_id in request_ids:
        raise RuntimeError(
            f"{expected_property_code} booking requests returned foreign request {foreign_request_id}"
        )

    own_detail = await get_json(
        client,
        f"/api/v1/admin/reception/reservations/{own_reservation_id}",
        label=f"{expected_property_code} own reservation detail",
    )
    if own_detail.get("reservation", {}).get("id") != own_reservation_id:
        raise RuntimeError(f"{expected_property_code} own reservation detail mismatch")

    await expect_denied(
        client,
        f"/api/v1/admin/reception/reservations/{foreign_reservation_id}",
        label=f"{expected_property_code} foreign reservation detail",
    )
    await expect_denied(
        client,
        f"/api/v1/admin/pms/reservations/{foreign_reservation_id}/schedule",
        label=f"{expected_property_code} foreign reservation schedule",
    )
    await expect_denied(
        client,
        f"/api/v1/admin/booking/requests/{foreign_request_id}/quote",
        method="POST",
        json_body={"room_type_code": "__CROSS_TENANT_ISOLATION_PROBE__"},
        label=f"{expected_property_code} foreign quote probe",
    )


async def main() -> int:
    base_url = validate_base_url(required("MARINA_STAGING_BASE_URL"))
    # Property-pinned runtimes use separate origins; shared-origin gates retain the default.
    base_url_b = validate_base_url(os.environ.get("MARINA_STAGING_TENANT_B_BASE_URL", "").strip() or base_url)
    if required("MARINA_STAGING_ISOLATION_CONFIRM") != CONFIRMATION:
        raise RuntimeError(
            f"MARINA_STAGING_ISOLATION_CONFIRM must equal {CONFIRMATION}"
        )

    a_reservation = validate_uuid(
        "MARINA_STAGING_TENANT_A_RESERVATION_ID",
        required("MARINA_STAGING_TENANT_A_RESERVATION_ID"),
    )
    b_reservation = validate_uuid(
        "MARINA_STAGING_TENANT_B_RESERVATION_ID",
        required("MARINA_STAGING_TENANT_B_RESERVATION_ID"),
    )
    a_request = validate_uuid(
        "MARINA_STAGING_TENANT_A_REQUEST_ID",
        required("MARINA_STAGING_TENANT_A_REQUEST_ID"),
    )
    b_request = validate_uuid(
        "MARINA_STAGING_TENANT_B_REQUEST_ID",
        required("MARINA_STAGING_TENANT_B_REQUEST_ID"),
    )

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=15.0,
        follow_redirects=False,
    ) as client_a, httpx.AsyncClient(
        base_url=base_url_b,
        timeout=15.0,
        follow_redirects=False,
    ) as client_b:
        a = await login(
            client_a,
            required("MARINA_STAGING_TENANT_A_USERNAME"),
            required("MARINA_STAGING_TENANT_A_PASSWORD"),
        )
        b = await login(
            client_b,
            required("MARINA_STAGING_TENANT_B_USERNAME"),
            required("MARINA_STAGING_TENANT_B_PASSWORD"),
        )

        if a["tenant_id"] == b["tenant_id"]:
            raise RuntimeError("Tenant A and Tenant B resolved to the same tenant_id")
        if a["property_id"] == b["property_id"]:
            raise RuntimeError("Tenant A and Tenant B resolved to the same property_id")
        if a["property_code"] == b["property_code"]:
            raise RuntimeError("Tenant A and Tenant B resolved to the same property_code")

        expected_a = required("MARINA_STAGING_TENANT_A_PROPERTY_CODE")
        expected_b = required("MARINA_STAGING_TENANT_B_PROPERTY_CODE")
        if a["property_code"] != expected_a or b["property_code"] != expected_b:
            raise RuntimeError(
                "trusted property codes do not match expected staging fixture: "
                f"A={a['property_code']}/{expected_a}, B={b['property_code']}/{expected_b}"
            )

        start = date.today().isoformat()
        end = (date.today() + timedelta(days=1)).isoformat()
        await verify_account(
            client_a,
            a,
            expected_a,
            a_reservation,
            a_request,
            b_reservation,
            b_request,
            start,
            end,
        )
        await verify_account(
            client_b,
            b,
            expected_b,
            b_reservation,
            b_request,
            a_reservation,
            a_request,
            start,
            end,
        )

        spoofed = await client_a.get(
            "/api/v1/pms/grid",
            params={"start": start, "end": end},
            headers={
                "X-Tenant-Id": b["tenant_id"],
                "X-Property-Id": b["property_id"],
            },
        )
        if spoofed.status_code != 200 or spoofed.json().get("property") != expected_a:
            raise RuntimeError("client-supplied tenant/property headers changed trusted context")

    print(
        "MARINA_STAGING_ISOLATION_PASS "
        f"tenant_a={a['tenant_id']} property_a={a['property_id']} "
        f"tenant_b={b['tenant_id']} property_b={b['property_id']}"
    )
    print(
        "BOUNDARY: authenticated two-tenant read isolation and denied cross-tenant "
        "probes passed; production remains STOP"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except (OSError, RuntimeError, httpx.HTTPError) as exc:
        print(f"MARINA_STAGING_ISOLATION_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
