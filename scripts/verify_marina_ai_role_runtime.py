#!/usr/bin/env python3
import asyncio
import os
import sys
from types import SimpleNamespace

import asyncpg
from fastapi import HTTPException

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "services", "api"))

from app.marina_assistant import _live_context  # noqa: E402


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"PASS: {message}")


def collect_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key).lower())
            keys.update(collect_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(collect_keys(nested))
    return keys


async def main() -> int:
    database_url = os.environ["DATABASE_URL"].split("?")[0]
    usernames = {
        "RECEPTION": os.environ["RECEPTION_USERNAME"],
        "MAID": os.environ["MAID_USERNAME"],
        "TECHNICIAN": os.environ["TECHNICIAN_USERNAME"],
        "AGENT": os.environ["AGENT_USERNAME"],
        "COOK": os.environ.get("COOK_USERNAME") or os.environ.get("KITCHEN_USERNAME") or os.environ["DINING_STAFF_USERNAME"],
    }

    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=pool)))

    forbidden_keys = {
        "phone", "email", "pin", "password", "passwordhash",
        "token", "access_token", "api_key", "telegramuserid",
        "telegramusername",
    }

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id,u.username,u.role::text AS role,u."bookingAgentId" AS booking_agent_id,
                       p.code AS property_code
                FROM staff_users u
                JOIN properties p ON p.id=u."propertyId"
                WHERE p.code=$1 AND u.username=ANY($2::text[]) AND u."isActive"=true
                """,
                os.environ["PROPERTY_CODE"],
                list(usernames.values()),
            )
            by_username = {row["username"]: row for row in rows}

        for expected_role, username in usernames.items():
            row = by_username.get(username)
            require(row is not None, f"{expected_role} fixture exists: {username}")
            require(row["role"] == expected_role, f"{username} server role is {expected_role}")

            user = {
                "id": str(row["id"]),
                "role": row["role"],
                "property_code": row["property_code"],
            }
            if expected_role != "RECEPTION":
                try:
                    await _live_context(request, user, expected_role)
                except HTTPException as exc:
                    require(exc.status_code == 403, f"{expected_role} assistant denied by server")
                else:
                    raise AssertionError(f"{expected_role} unexpectedly received AI access")
                continue

            snapshot = await _live_context(request, user, expected_role)
            require(snapshot.get("available") is True, f"{expected_role} live context available")
            require(snapshot.get("read_only") is True, f"{expected_role} context stays read-only")
            require(snapshot.get("role") == expected_role, f"{expected_role} role preserved")

            exposed = collect_keys(snapshot)
            leaked = sorted(forbidden_keys & exposed)
            require(not leaked, f"{expected_role} omits secrets/direct contacts: leaked={leaked}")

            if expected_role == "RECEPTION":
                require("hotel" in snapshot, "RECEPTION receives hotel operations context")
                require("finance" not in (snapshot.get("hotel") or {}), "RECEPTION does not receive OWNER/MANAGER finance")
                require("agent" not in snapshot and "dining" not in snapshot, "RECEPTION has no unrelated agent/dining scope")

        print("MARINA_AI_ROLE_RUNTIME_ACCEPTANCE: PASS")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
