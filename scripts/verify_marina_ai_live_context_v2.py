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


async def main() -> int:
    database_url = os.environ["DATABASE_URL"].split("?")[0]
    owner_username = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            owner = await conn.fetchrow(
                """
                SELECT u.id,u.role::text AS role,p.code AS property_code
                FROM staff_users u
                JOIN properties p ON p.id=u."propertyId"
                WHERE u.username=$1 AND u."isActive"=true
                """,
                owner_username,
            )
            require(owner is not None, "OWNER fixture exists")

        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(db=pool))
        )
        user = {
            "id": str(owner["id"]),
            "role": owner["role"],
            "property_code": owner["property_code"],
        }

        snapshot = await _live_context(request, user, "DASHBOARD")
        require(snapshot.get("available") is True, "live context is available")
        require(snapshot.get("read_only") is True, "live context stays read-only")
        require(snapshot.get("role") == "OWNER", "OWNER role is preserved")

        hotel = snapshot.get("hotel") or {}
        occupancy = hotel.get("occupancy") or {}
        finance = hotel.get("finance") or {}

        required_hotel_fields = {
            "room_counts",
            "occupancy",
            "rooms_requiring_attention",
            "arrivals_today",
            "departures_today",
            "active_reservations",
            "task_counts",
            "active_tasks",
            "active_inventory_holds",
            "reservation_request_counts",
            "finance",
        }
        missing = sorted(required_hotel_fields - set(hotel))
        require(not missing, f"hotel v2 fields present: missing={missing}")

        for field in (
            "total_rooms",
            "sellable_rooms",
            "occupied_rooms",
            "vacant_sellable_rooms",
            "occupancy_percent",
            "tech_block_rooms",
        ):
            require(field in occupancy, f"occupancy.{field} present")

        for field in (
            "active_reservation_count",
            "active_total_kgs",
            "active_paid_kgs",
            "active_remaining_kgs",
            "debtor_count",
            "confirmed_payments_today_kgs",
            "awaiting_prepayment",
        ):
            require(field in finance, f"finance.{field} present")

        require(
            occupancy["sellable_rooms"] <= occupancy["total_rooms"],
            "sellable rooms do not exceed total rooms",
        )
        require(
            occupancy["vacant_sellable_rooms"] <= occupancy["sellable_rooms"],
            "vacant sellable rooms do not exceed sellable rooms",
        )
        require(
            finance["active_remaining_kgs"] >= 0,
            "active reservation balance is non-negative",
        )

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

        forbidden_keys = {"phone", "email", "pin", "password", "token", "api_key", "access_token"}
        exposed_keys = collect_keys(snapshot)
        require(
            forbidden_keys.isdisjoint(exposed_keys),
            f"OWNER live context omits secrets and direct contact fields: exposed={sorted(forbidden_keys & exposed_keys)}",
        )

        print("MARINA_AI_LIVE_CONTEXT_V2_RUNTIME: PASS")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
