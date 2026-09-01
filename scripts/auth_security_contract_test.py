#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import asyncpg
import httpx

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://resort:resort@localhost:5432/resort_os").split("?")[0]
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Only-Strong-Password-2026")
PAIR_LIMIT = int(os.environ.get("AUTH_LOGIN_PAIR_MAX_FAILURES", "3"))
IP_LIMIT = int(os.environ.get("AUTH_LOGIN_IP_MAX_FAILURES", "8"))
WINDOW_SECONDS = int(os.environ.get("AUTH_LOGIN_WINDOW_SECONDS", "60"))
BAD_PASSWORD = "Wrong-Password-2026"
GENERIC_DETAIL = "Invalid username or password"


def key(kind: str, *parts: str) -> str:
    return f"{kind}:" + hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def pair_key(username: str, ip: str) -> str:
    return key("PAIR", PROPERTY_CODE, username.strip().lower(), ip)


def ip_key(ip: str) -> str:
    return key("IP", PROPERTY_CODE, ip)


def login(username: str, password: str, ip: str) -> httpx.Response:
    return httpx.post(
        f"{BASE}/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"X-Forwarded-For": ip},
        timeout=20.0,
    )


def assert_generic_failure(response: httpx.Response) -> None:
    assert response.status_code == 401, (response.status_code, response.text)
    assert response.json() == {"detail": GENERIC_DETAIL}, response.text


async def audit_count(resource_id: str, action: str = "LOGIN_FAILED") -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return int(
            await conn.fetchval(
                '''SELECT count(*) FROM audit_logs
                   WHERE resource='AuthThrottle' AND action=$1 AND "resourceId"=$2''',
                action,
                resource_id,
            )
        )
    finally:
        await conn.close()


async def expire_failure_window() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            '''UPDATE audit_logs
               SET "createdAt"="createdAt"-$1::interval
               WHERE resource='AuthThrottle' AND action='LOGIN_FAILED' ''',
            timedelta(seconds=WINDOW_SECONDS + 5),
        )
    finally:
        await conn.close()


async def throttle_evidence() -> list[dict]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            '''SELECT action,resource,"resourceId",source,result,"actorId","beforeJson","afterJson"
               FROM audit_logs WHERE resource='AuthThrottle' ORDER BY "createdAt",id'''
        )
        return [dict(row) for row in rows]
    finally:
        await conn.close()


def main() -> None:
    assert PAIR_LIMIT >= 2
    assert IP_LIMIT > PAIR_LIMIT
    assert os.environ.get("AUTH_TRUST_PROXY_HEADERS", "").lower() in {"1", "true", "yes"}, (
        "security contract must run behind explicit trusted-proxy-header mode"
    )

    pair_ip = "198.51.100.10"
    for _ in range(PAIR_LIMIT):
        assert_generic_failure(login(USERNAME, BAD_PASSWORD, pair_ip))
    assert_generic_failure(login(USERNAME, PASSWORD, pair_ip))
    assert asyncio.run(audit_count(pair_key(USERNAME, pair_ip))) == PAIR_LIMIT
    assert asyncio.run(audit_count(ip_key(pair_ip))) == PAIR_LIMIT

    # Pair-based throttling must not create a trivial global account lockout: a legitimate
    # login for the same account from a different trusted client IP still succeeds.
    fresh_ip = "198.51.100.11"
    legitimate = login(USERNAME, PASSWORD, fresh_ip)
    assert legitimate.status_code == 200, legitimate.text
    assert legitimate.json()["username"] == USERNAME

    # A successful login resets only that account+IP pair. Two new failures remain below
    # the pair threshold and a legitimate login is accepted again.
    for _ in range(PAIR_LIMIT - 1):
        assert_generic_failure(login(USERNAME, BAD_PASSWORD, fresh_ip))
    reset_success = login(USERNAME, PASSWORD, fresh_ip)
    assert reset_success.status_code == 200, reset_success.text
    assert asyncio.run(audit_count(pair_key(USERNAME, fresh_ip), "LOGIN_THROTTLE_RESET")) >= 2

    # IP spray protection is independent of username existence. Once the high IP limit is
    # reached, even a valid credential from that source receives the same generic response.
    spray_ip = "198.51.100.12"
    for index in range(IP_LIMIT):
        assert_generic_failure(login(f"spray-user-{index}", BAD_PASSWORD, spray_ip))
    assert_generic_failure(login(USERNAME, PASSWORD, spray_ip))
    assert asyncio.run(audit_count(ip_key(spray_ip))) == IP_LIMIT

    # A different IP is unaffected by the source-IP throttle.
    assert login(USERNAME, PASSWORD, "198.51.100.13").status_code == 200

    # Concurrent attempts with the same pair/IP are serialized by PostgreSQL advisory locks.
    # Only the bounded number of failures is persisted; later requests are rejected before
    # password verification and do not race past the threshold.
    concurrent_ip = "198.51.100.14"
    with ThreadPoolExecutor(max_workers=PAIR_LIMIT * 2) as executor:
        futures = [executor.submit(login, USERNAME, BAD_PASSWORD, concurrent_ip) for _ in range(PAIR_LIMIT * 2)]
        responses = [future.result(timeout=30) for future in futures]
    for response in responses:
        assert_generic_failure(response)
    assert asyncio.run(audit_count(pair_key(USERNAME, concurrent_ip))) == PAIR_LIMIT
    assert asyncio.run(audit_count(ip_key(concurrent_ip))) == PAIR_LIMIT

    # Window expiry restores legitimate access without deleting immutable audit evidence.
    asyncio.run(expire_failure_window())
    recovered = login(USERNAME, PASSWORD, pair_ip)
    assert recovered.status_code == 200, recovered.text

    evidence = asyncio.run(throttle_evidence())
    assert evidence, "throttle audit evidence missing"
    serialized = json.dumps(evidence, ensure_ascii=False, default=str)
    for forbidden in [USERNAME, BAD_PASSWORD, pair_ip, fresh_ip, spray_ip, concurrent_ip]:
        assert forbidden not in serialized, f"raw sensitive throttle input leaked into audit evidence: {forbidden}"
    assert all(item["actorId"] is None for item in evidence)
    assert all(item["source"] == "AUTH_THROTTLE" for item in evidence)
    assert all(item["resourceId"].startswith(("PAIR:", "IP:")) for item in evidence)

    print(
        "AUTH_SECURITY_CONTRACT_OK generic_401=true pair_limit=true ip_limit=true "
        "account_dos_resistant=true concurrent_serialization=true expiry_recovery=true "
        "success_reset=true trusted_proxy_ip=true raw_credentials_not_logged=true"
    )


if __name__ == "__main__":
    main()
