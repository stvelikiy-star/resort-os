"""Public AI security: trusted proxy verification + real PostgreSQL cross-worker quota.

This verifier never calls OpenAI. Run only against an isolated CI PostgreSQL.
"""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

import asyncpg
from fastapi import HTTPException
from starlette.requests import Request

from services.api.app import public_ai_admin as module

DB = os.environ["DATABASE_URL"].split("?schema=",1)[0]
PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")


def request(app, peer, forwarded=""):
    headers=[(b"x-forwarded-for",forwarded.encode())] if forwarded else []
    return Request({"type":"http","method":"POST","path":"/api/v1/public/ai-admin/chat",
                    "headers":headers,"client":(peer,9876),"app":app})


async def main():
    if os.environ.get("APP_ENV","test").lower() == "production":
        raise AssertionError("Security test cannot run against production")
    if not any(name in DB for name in ("localhost", "127.0.0.1")):
        raise AssertionError("Only local disposable CI databases are permitted")
    pool=await asyncpg.create_pool(DB,min_size=1,max_size=6)
    app=SimpleNamespace(state=SimpleNamespace(db=pool))
    try:
        async with pool.acquire() as conn:
            pid=await conn.fetchval('SELECT id FROM properties WHERE code=$1',PROPERTY_CODE)
            assert pid is not None
            # Isolated CI DB only. Never remove operational audit logs.
            await conn.execute(
                '''DELETE FROM audit_logs WHERE "propertyId"=$1
                   AND action='PUBLIC_AI_REQUEST' AND resource='PublicAiThrottle' ''',pid)
        with patch("services.api.app.auth.AUTH_TRUST_PROXY_HEADERS",False), \
             patch.object(module,"AI_ADMIN_RATE_LIMIT_PER_MINUTE",2), \
             patch.object(module,"AI_ADMIN_DAILY_REQUEST_LIMIT",3):
            caller=request(app,"198.51.100.20","203.0.113.1")
            assert module._client_key(caller)=="198.51.100.20", "Spoofed header trusted"
            # Competing requests across pooled PostgreSQL connections are globally serialized.
            async def attempt(n):
                try:
                    await module._enforce_rate_limit(request(app,"198.51.100.20",f"203.0.113.{n}"))
                    return 201
                except HTTPException as exc:
                    return exc.status_code
            status=await asyncio.gather(*[attempt(n) for n in range(6)])
            assert status.count(201)==2 and status.count(429)==4, status
            # A different IP can consume the last daily quota.
            await module._enforce_rate_limit(request(app,"198.51.100.21"))
            try:
                await module._enforce_rate_limit(request(app,"198.51.100.22"))
            except HTTPException as exc:
                assert exc.status_code==429
            else:
                raise AssertionError("Daily property budget bypassed")
        with patch("services.api.app.auth.AUTH_TRUST_PROXY_HEADERS",True):
            assert module._client_key(request(app,"198.51.100.30","203.0.113.77"))=="198.51.100.30"
            assert module._client_key(request(app,"127.0.0.1","203.0.113.77"))=="203.0.113.77"
            assert module._client_key(request(app,"127.0.0.1","invalid-header"))=="127.0.0.1"
        async with pool.acquire() as conn:
            rows=await conn.fetch(
                '''SELECT "resourceId",count(*)::int AS attempts
                   FROM audit_logs WHERE "propertyId"=$1
                   AND action='PUBLIC_AI_REQUEST' AND resource='PublicAiThrottle'
                   GROUP BY "resourceId" ''',pid)
            assert sum(row["attempts"] for row in rows)==3, rows
            assert all(len(row["resourceId"])==64 for row in rows), "Raw IP leaked to audit"
        print("PUBLIC AI RATE LIMIT REAL POSTGRES: PASS 3 recorded, spoof denied, concurrent 429, day budget, no OpenAI")
    finally:
        await pool.close()


if __name__=="__main__":
    asyncio.run(main())
