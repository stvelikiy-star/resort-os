#!/usr/bin/env python3
"""Synthetic-only active/inactive/unlinked AGENT membership fixtures.

Never use against a customer database. Extends the already-seeded isolated
two-hotel browser CI without resetting, truncating, or changing RC3 source.
"""
import asyncio
import os
import uuid

import asyncpg
from marina_shared_live_browser_db import dsn


async def seed_agent_fixtures():
    if os.environ.get("MARINA_SHARED_AGENT_P0_SEED_CONFIRM") != "ISOLATED_AGENT_CI_ONLY":
        raise RuntimeError("Synthetic agent seed confirmation missing")
    if os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED") != "true":
        raise RuntimeError("Shared auth staging required")
    conn = await asyncpg.connect(dsn())
    try:
        async with conn.transaction():
            assert await conn.fetchval("SELECT count(*) FROM tenants") == 2
            assert await conn.fetchval("SELECT count(*) FROM properties") == 2
            assert await conn.fetchval("SELECT count(*) FROM booking_agents") == 0, (
                "Refusing to touch populated agents"
            )
            for suffix in ("A", "B"):
                pid = await conn.fetchval(
                    "SELECT id FROM properties WHERE code=$1", "HOTEL_" + suffix)
                assert pid is not None
                row = await conn.fetchrow(
                    'SELECT id,"passwordHash" FROM staff_users '
                    'WHERE "propertyId"=$1 AND username=\'agent\' AND '
                    'role=\'AGENT\' AND "isActive"=true', pid)
                assert row, "Expected original synthetic AGENT identity"
                active_id = uuid.UUID(
                    "11111111-2222-4333-8444-7777777777" + suffix.lower() + "1"
                )
                inactive_id = uuid.UUID(
                    "11111111-2222-4333-8444-8888888888" + suffix.lower() + "1"
                )
                await conn.execute(
                    'INSERT INTO booking_agents(id,"propertyId",name,status,'
                    '"createdAt","updatedAt") VALUES '
                    "($1,$2,$3,'ACTIVE',now(),now()),"
                    "($4,$2,$5,'INACTIVE',now(),now())",
                    active_id, pid, "CI active agency " + suffix,
                    inactive_id, "CI disabled agency " + suffix,
                )
                await conn.execute(
                    'UPDATE staff_users SET "bookingAgentId"=$2,"updatedAt"=now() '
                    'WHERE id=$1 AND "propertyId"=$3',
                    row["id"], active_id, pid,
                )
                for name, link in (("agent_inactive", inactive_id),
                                   ("agent_unlinked", None)):
                    await conn.execute(
                        '''INSERT INTO staff_users
                        (id,"propertyId",username,"displayName","passwordHash",
                         role,"bookingAgentId","isActive","updatedAt")
                         VALUES($1,$2,$3,$4,$5,'AGENT',$6,true,now())''',
                        uuid.uuid4(), pid, name,
                        "CI " + name + " " + suffix,
                        row["passwordHash"], link,
                    )
            assert await conn.fetchval(
                "SELECT count(*) FROM booking_agents") == 4
            assert await conn.fetchval(
                'SELECT count(*) FROM staff_users WHERE role=\'AGENT\'') == 6
    finally:
        await conn.close()
    print("PASS: active, disabled and unlinked agents for two independent synthetic hotels")


if __name__ == "__main__":
    asyncio.run(seed_agent_fixtures())
