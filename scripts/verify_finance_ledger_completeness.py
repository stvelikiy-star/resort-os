#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import date, timedelta
from http.cookiejar import CookieJar

import asyncpg

BASE = os.environ.get("CORE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DB = os.environ["DATABASE_URL"].replace("?schema=public", "")
OWNER_USERNAME = os.environ["BOOTSTRAP_OWNER_USERNAME"]
OWNER_PASSWORD = os.environ["BOOTSTRAP_OWNER_PASSWORD"]


def login_cookie() -> str:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    request = urllib.request.Request(
        BASE + "/api/v1/auth/login",
        data=json.dumps({"username": OWNER_USERNAME, "password": OWNER_PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=20) as response:
        assert response.status == 200
        response.read()
    cookie = "; ".join(f"{item.name}={item.value}" for item in jar)
    assert cookie
    return cookie


async def seed_large_ledger() -> tuple[str, date]:
    conn = await asyncpg.connect(DB)
    try:
        prop = await conn.fetchrow(
            "SELECT id,(now() AT TIME ZONE timezone)::date AS local_today FROM properties WHERE code='THREE_CROWNS'"
        )
        assert prop
        pid = prop["id"]
        today = prop["local_today"]
        marker = uuid.uuid4().hex[:10].upper()

        # This debtor is deliberately older than 505 later CANCELLED rows. With the old
        # SQL LIMIT 500 it disappears before debtor calculation, which this test catches.
        debtor_id = uuid.uuid4()
        await conn.execute(
            '''
            INSERT INTO reservations (
              id,"propertyId","bookingNumber",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt"
            ) VALUES ($1,$2,$3,'CHECKED_OUT',$4,$5,1,0,100,now(),now())
            ''',
            debtor_id,
            pid,
            f"FIN-COMPLETE-DEBT-{marker}",
            today - timedelta(days=12),
            today - timedelta(days=10),
        )

        padding = []
        for index in range(505):
            padding.append(
                (
                    uuid.uuid4(),
                    pid,
                    f"FIN-COMPLETE-PAD-{marker}-{index:03d}",
                    today + timedelta(days=50),
                    today + timedelta(days=51),
                )
            )
        await conn.executemany(
            '''
            INSERT INTO reservations (
              id,"propertyId","bookingNumber",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt"
            ) VALUES ($1,$2,$3,'CANCELLED',$4,$5,1,0,100,now(),now())
            ''',
            padding,
        )
        return str(debtor_id), today
    finally:
        await conn.close()


def main() -> None:
    debtor_id, today = asyncio.run(seed_large_ledger())
    cookie = login_cookie()
    query = urllib.parse.urlencode({"from_date": today.isoformat(), "to_date": today.isoformat()})
    request = urllib.request.Request(
        BASE + f"/api/v1/admin/finance/summary?{query}",
        headers={"Cookie": cookie, "User-Agent": "finance-ledger-completeness-ci"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        body = json.loads(response.read().decode("utf-8"))

    meta = body["reservation_ledger_meta"]
    assert meta["total_count"] > 500, meta
    assert meta["returned_count"] == 500, meta
    assert meta["truncated"] is True, meta
    assert meta["snapshot_calculation_complete"] is True, meta

    preview_ids = {item["reservation_id"] for item in body["reservation_ledger"]}
    assert debtor_id not in preview_ids, "fixture must be outside the 500-row payload preview"

    debtor = next((item for item in body["debtors"] if item["reservation_id"] == debtor_id), None)
    assert debtor, "checked-out debtor was lost behind the ledger preview boundary"
    assert debtor["status"] == "CHECKED_OUT"
    assert debtor["remaining_kgs"] == 100
    assert debtor["balance_stage"] == "CHECKED_OUT_BALANCE"
    assert body["receivables_snapshot"]["checked_out_kgs"] >= 100

    print("PASS: finance snapshots remain complete when reservation ledger exceeds 500 rows")


if __name__ == "__main__":
    main()
