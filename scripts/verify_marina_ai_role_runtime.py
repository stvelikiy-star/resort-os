#!/usr/bin/env python3
import asyncio
import os
import sys
from types import SimpleNamespace

import asyncpg

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
        "DINING_STAFF": os.environ["DINING_STAFF_USERNAME"],
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

            elif expected_role == "MAID":
                housekeeping = snapshot.get("housekeeping") or {}
                require(housekeeping, "MAID receives housekeeping context")
                require("task_counts" in housekeeping and "rooms" in housekeeping and "tasks" in housekeeping, "MAID receives actionable housekeeping fields")
                require("hotel" not in snapshot and "finance" not in snapshot and "agent" not in snapshot, "MAID has no hotel finance/agent scope")
                for task in housekeeping.get("tasks", []):
                    require(task.get("assigned_to_me") in {True, False}, "MAID task assignment flag present")

            elif expected_role == "TECHNICIAN":
                maintenance = snapshot.get("maintenance") or {}
                require(maintenance, "TECHNICIAN receives maintenance context")
                require("task_counts" in maintenance and "tech_block_rooms" in maintenance and "tasks" in maintenance, "TECHNICIAN receives actionable maintenance fields")
                require("hotel" not in snapshot and "finance" not in snapshot and "agent" not in snapshot, "TECHNICIAN has no hotel finance/agent scope")
                for task in maintenance.get("tasks", []):
                    require(task.get("assigned_to_me") in {True, False}, "TECHNICIAN task assignment flag present")

            elif expected_role == "AGENT":
                agent = snapshot.get("agent") or {}
                require(row["booking_agent_id"] is not None, "AGENT fixture is linked to bookingAgentId")
                require(agent.get("available") is True, "AGENT scoped context is active")
                require("availability_today" in agent, "AGENT receives aggregate availability")
                require("active_requests" in agent and "active_reservations" in agent, "AGENT receives own request/reservation collections")
                require("scope_rule" in agent and "bookingAgentId" in agent["scope_rule"], "AGENT strict isolation rule documented")
                require("hotel" not in snapshot and "finance" not in snapshot and "housekeeping" not in snapshot and "maintenance" not in snapshot, "AGENT has no cross-role operational scopes")

            elif expected_role == "DINING_STAFF":
                dining = snapshot.get("dining") or {}
                require(dining, "DINING_STAFF receives dining context")
                require("order_counts" in dining and "active_orders" in dining and "table_counts" in dining, "DINING_STAFF receives operational dining fields")
                require("hotel" not in snapshot and "finance" not in snapshot and "agent" not in snapshot, "DINING_STAFF has no hotel finance/agent scope")

        print("MARINA_AI_ROLE_RUNTIME_ACCEPTANCE: PASS")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
