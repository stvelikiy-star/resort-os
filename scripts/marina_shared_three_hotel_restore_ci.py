#!/usr/bin/env python3
"""Full logical backup of three hotels after additive onboarding; verify restored API.

Only disposable localhost PostgreSQL. Never drops, truncates or overwrites a DB.
"""
from __future__ import annotations

import asyncio
from datetime import date,timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, unquote, parse_qsl

import asyncpg

from marina_shared_add_hotel import staged_configuration
from marina_shared_live_browser_db import RECEIPTS,PASSWORD
from marina_two_property_restore_e2e import snapshot,pg_arguments
from marina_shared_release_restore_ci import public_schema_metadata
from release_contract import EXPECTED_MIGRATIONS
from prisma_migration_ledger import verify_committed_ledger

ROOT=Path(__file__).resolve().parents[1]
DEST_NAME="marina_shared_third_restore_ci"
CONFIRM="ISOLATED_THREE_HOTEL_LOGICAL_RESTORE_ONLY"


def verify_restore_urls(source: str, target: str) -> tuple[str,str]:
    if os.environ.get("MARINA_SHARED_THREE_RESTORE_CONFIRM")!=CONFIRM:
        raise RuntimeError("Third-hotel restore is not confirmed")
    if (os.environ.get("APP_ENV")!="staging" or
        os.environ.get("MARINA_TENANT_CONTEXT_ENABLED")!="true" or
        os.environ.get("MARINA_SHARED_AUTH_PREVIEW_ENABLED")!="true" or
        os.environ.get("MARINA_SHARED_BROWSER_CI_CONFIRM")!="DISPOSABLE_TWO_HOTEL_BROWSER_CI" or
        os.environ.get("MARINA_SHARED_THIRD_HOTEL_CONFIRM")!="DISPOSABLE_THIRD_HOTEL_ADDITIVE_CI_ONLY" or
        os.environ.get("COOKIE_SECURE")!="true"):
        raise RuntimeError("Not isolated shared three-hotel restore runtime")
    for raw,expected in ((source,"marina_shared_browser_ci"),(target,DEST_NAME)):
        u=urlsplit(raw)
        if (u.scheme not in ("postgresql","postgres") or
            u.hostname not in ("127.0.0.1","localhost") or
            u.port!=5432 or
            unquote(u.path)!="/"+expected or
            u.username!="marina_ci" or
            u.password!="synthetic-ci-database-only" or
            u.fragment or parse_qsl(u.query,keep_blank_values=True) not in ([],[("schema","public")])):
            raise RuntimeError("Refusing unsafe shared restore database URL")
    return source.split("?",1)[0],target.split("?",1)[0]


async def assert_source_three(source: str) -> None:
    conn=await asyncpg.connect(source)
    try:
        rows=await conn.fetch('''
            SELECT t.code AS tenant,p.code AS hotel FROM properties p
            JOIN tenants t ON t.id=p."tenantId" ORDER BY t.code,p.code''')
        assert [(r["tenant"],r["hotel"]) for r in rows]==[
            ("tenant_a","HOTEL_A"),("tenant_b","HOTEL_B"),("tenant_c","HOTEL_C")], "Unexpected populated source"
        assert await conn.fetchval("SELECT count(*) FROM staff_users")==25
        assert await conn.fetchval("SELECT count(*) FROM reservations")==6
        assert await conn.fetchval("SELECT count(*) FROM payments")==2
        assert len(await verify_committed_ledger(conn,ROOT)) == len(EXPECTED_MIGRATIONS)
    finally:
        await conn.close()


async def assert_empty(target: str) -> None:
    conn=await asyncpg.connect(target)
    try:
        if await conn.fetchval("SELECT count(*) FROM pg_tables WHERE schemaname='public'"):
            raise RuntimeError("Refusing restore into an existing database with tables")
    finally:
        await conn.close()


def command(args,env=None) -> None:
    subprocess.run(args,env=env,check=True,stdout=subprocess.DEVNULL)


async def verify_ledger(target: str) -> None:
    conn=await asyncpg.connect(target)
    try:
        assert len(await verify_committed_ledger(conn,ROOT)) == len(EXPECTED_MIGRATIONS)
    finally:
        await conn.close()


def full_restore() -> None:
    source,_=staged_configuration()
    source,target=verify_restore_urls(source,os.environ.get("RESTORE_DATABASE_URL",""))
    receipts=json.loads(RECEIPTS.read_text())
    assert set(receipts)=={"HOTEL_A","HOTEL_B"}
    asyncio.run(assert_source_three(source))
    asyncio.run(assert_empty(target))
    pre=asyncio.run(snapshot(source))
    schema_before=asyncio.run(public_schema_metadata(source))
    with tempfile.TemporaryDirectory(prefix="marina-three-hotel-dump-") as folder:
        archive=Path(folder)/"three-hotels.dump"
        srcargs,srcenv=pg_arguments(source)
        command(["pg_dump",*srcargs,"--format=custom","--no-owner","--no-acl","--file",str(archive)],srcenv)
        assert archive.is_file() and archive.stat().st_size>1024
        command(["pg_restore","--list",str(archive)])
        digest=hashlib.sha256(archive.read_bytes()).hexdigest()
        dstargs,dstenv=pg_arguments(target)
        asyncio.run(assert_empty(target))
        command(["pg_restore",*dstargs,"--exit-on-error","--no-owner","--no-acl",str(archive)],dstenv)
        assert asyncio.run(snapshot(target))==pre,"Restored 3-hotel rows/constraints differ"
        assert asyncio.run(public_schema_metadata(target))==schema_before, "Restored indexes/columns drifted"
        asyncio.run(verify_ledger(target))
        assert asyncio.run(snapshot(source))==pre,"Original populated source was modified by dump/restore"
        print("MARINA_SHARED_THREE_HOTEL_RESTORE_DATA_PASS: "
              f"tables={len(pre['tables'])} indexes={len(schema_before['indexes'])} "
              "migrations=39 source_unchanged=true sha256="+digest[:16]+"...",flush=True)
    env=dict(os.environ)
    env["MARINA_SHARED_ORIGINAL_DATABASE_URL"]=source
    env["DATABASE_URL"]=target
    command([sys.executable,str(Path(__file__)),"verify-restored"],env)
    assert asyncio.run(snapshot(source))==pre, "Restored API changed original shared database"
    print("MARINA_SHARED_THREE_HOTEL_RESTORE_E2E_PASS: three tenants, full backup, fresh restored canonical API",flush=True)


def restored_api() -> None:
    source,target=verify_restore_urls(
        os.environ.get("MARINA_SHARED_ORIGINAL_DATABASE_URL",""),
        os.environ.get("DATABASE_URL",""))
    receipts=json.loads(RECEIPTS.read_text())
    assert set(receipts)=={"HOTEL_A","HOTEL_B"}
    asyncio.run(assert_source_three(target))
    from fastapi.testclient import TestClient
    sys.path.insert(0,str(ROOT/"services"/"api"))
    from app.app_entry import app
    with TestClient(app,base_url="https://localhost:18000") as client:
        for hotel,tenant,expected_code,received,count in (
            ("HOTEL_A","tenant_a","A101",1000,12),
            ("HOTEL_B","tenant_b","B202",1500,12),
            ("HOTEL_C","tenant_c",None,0,1),
        ):
            client.cookies.clear()
            login=client.post("/api/v1/auth/login",json={
                "tenant_code":tenant,"property_code":hotel,
                "username":"owner","password":PASSWORD})
            assert login.status_code==200,hotel+" restored login"
            me=client.get("/api/v1/auth/me")
            assert me.status_code==200 and me.json()["property_code"]==hotel
            grid=client.get("/api/v1/pms/grid",params={
                "start":(date.today()-timedelta(days=2)).isoformat(),
                "end":(date.today()+timedelta(days=7)).isoformat()})
            assert grid.status_code==200 and grid.json()["property"]==hotel
            assert {x["code"] for x in grid.json()["rooms"]}==(
                {expected_code} if expected_code else set())
            finance=client.get("/api/v1/admin/finance/summary",params={
                "from_date":(date.today()-timedelta(days=10)).isoformat(),
                "to_date":(date.today()+timedelta(days=10)).isoformat()})
            assert finance.status_code==200
            f=finance.json()
            assert f["scope"]["internal_only"] is True
            assert f["period_payments"]["received_kgs"]==received
            assert not any(row["reservation_id"] in
                           [r["reservation_id"] for h,r in receipts.items() if h!=hotel]
                           for row in f["reservation_ledger"])
            staff=client.get("/api/v1/admin/staff/overview")
            assert staff.status_code==200 and len(staff.json()["staff"])==count
            if hotel=="HOTEL_C":
                assert f["reservation_ledger"]==[]
                for other in receipts.values():
                    foreign=client.get("/api/v1/ops/tasks/"+other["maintenance_task_id"]+"/history")
                    assert foreign.status_code==404,"Restored new hotel accessed an old task"
            assert client.post("/api/v1/auth/logout").status_code==204
            assert client.get("/api/v1/auth/me").status_code==401
    print("MARINA_SHARED_THREE_HOTEL_RESTORE_API_PASS: three owners, scoped PMS/finance/staff, foreign 404",flush=True)


if __name__=="__main__":
    if sys.argv[1:]==["verify-restored"]:
        restored_api()
    elif len(sys.argv)==1:
        full_restore()
    else:
        raise SystemExit("Usage: marina_shared_three_hotel_restore_ci.py [verify-restored]")
