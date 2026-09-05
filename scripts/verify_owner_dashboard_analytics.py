#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import asyncpg
import httpx

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "owner-analytics-ci")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "Owner-Analytics-CI-2026")
RECEPTION_USERNAME = os.environ.get("OWNER_ANALYTICS_RECEPTION_USERNAME", "owner-analytics-reception")
RECEPTION_PASSWORD = os.environ.get("OWNER_ANALYTICS_RECEPTION_PASSWORD", "Owner-Analytics-Reception-2026")
MAID_USERNAME = os.environ.get("OWNER_ANALYTICS_MAID_USERNAME", "owner-analytics-maid")
TECH_USERNAME = os.environ.get("OWNER_ANALYTICS_TECH_USERNAME", "owner-analytics-tech")


def utc_naive(local_day: date, hour: int, minute: int, tz_name: str) -> datetime:
    local = datetime.combine(local_day, time(hour, minute), tzinfo=ZoneInfo(tz_name))
    return local.astimezone(timezone.utc).replace(tzinfo=None)


async def seed_known_facts() -> dict:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        prop = await conn.fetchrow("SELECT id,timezone FROM properties WHERE code='THREE_CROWNS'")
        assert prop
        pid = prop["id"]
        tz_name = prop["timezone"]
        today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", tz_name)
        room = await conn.fetchrow('SELECT id,code FROM rooms WHERE "propertyId"=$1 ORDER BY code LIMIT 1', pid)
        assert room
        maid_id = await conn.fetchval(
            'SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2', pid, MAID_USERNAME
        )
        tech_id = await conn.fetchval(
            'SELECT id FROM staff_users WHERE "propertyId"=$1 AND username=$2', pid, TECH_USERNAME
        )
        assert maid_id and tech_id

        async def task(
            task_type: str,
            status: str,
            title: str,
            created_hm: tuple[int, int],
            completed_hm: tuple[int, int] | None,
            assignee,
            service_code: str | None = None,
            service_date: date | None = None,
            room_id=None,
            priority: str = "NORMAL",
        ):
            created_at = utc_naive(today, *created_hm, tz_name)
            completed_at = utc_naive(today, *completed_hm, tz_name) if completed_hm else None
            updated_at = completed_at or created_at
            await conn.execute(
                '''
                INSERT INTO operational_tasks(
                  id,"propertyId","roomId","serviceCode","serviceDate",type,status,priority,title,
                  "assignedToId","createdByType",source,"completedAt","createdAt","updatedAt"
                ) VALUES(
                  $1,$2,$3,$4,$5,$6::"OperationalTaskType",$7::"OperationalTaskStatus",
                  $8::"OperationalTaskPriority",$9,$10,'SYSTEM','OWNER_DASHBOARD_ANALYTICS_CI',$11,$12,$13
                )
                ''',
                uuid.uuid4(), pid, room_id, service_code, service_date, task_type, status, priority,
                title, assignee, completed_at, created_at, updated_at,
            )

        # Guest Services: 2 DONE (30m + 90m = 60m avg), 1 active and overdue by stored serviceDate.
        await task("GUEST_REQUEST", "DONE", "Extra towels", (0, 40), (1, 10), None, "TOWELS", today)
        await task("GUEST_REQUEST", "DONE", "Reception help", (1, 20), (2, 50), None, "RECEPTION", today)
        await task("GUEST_REQUEST", "OPEN", "Wake-up reminder", (3, 0), None, None, "RECEPTION", today - timedelta(days=1), priority="URGENT")

        # Housekeeping: 2 DONE (20m + 40m = 30m avg), 1 active.
        await task("HOUSEKEEPING", "DONE", "Departure clean A", (3, 10), (3, 30), maid_id, room_id=room["id"])
        await task("HOUSEKEEPING", "DONE", "Departure clean B", (3, 40), (4, 20), maid_id, room_id=room["id"])
        await task("HOUSEKEEPING", "IN_PROGRESS", "Refresh clean", (4, 30), None, maid_id, room_id=room["id"])

        # Maintenance: 2 DONE (60m + 120m = 90m avg), 1 active; exact title recurs twice.
        await task("MAINTENANCE", "DONE", "Air conditioner leak", (4, 40), (5, 40), tech_id, room_id=room["id"])
        await task("MAINTENANCE", "DONE", "Air conditioner leak", (5, 45), (7, 45), tech_id, room_id=room["id"])
        await task("MAINTENANCE", "OPEN", "Bathroom tap", (7, 50), None, tech_id, room_id=room["id"], priority="HIGH")

        reservation_id = uuid.uuid4()
        booking_number = f"OWNER-AN-{uuid.uuid4().hex[:8]}"
        created_at = utc_naive(today, 0, 10, tz_name)
        paid_at = utc_naive(today, 0, 30, tz_name)
        await conn.execute(
            '''
            INSERT INTO reservations(
              id,"propertyId","bookingNumber",status,"checkIn","checkOut",adults,children,"totalKgs","createdAt","updatedAt"
            ) VALUES($1,$2,$3,'GUARANTEED',$4,$5,1,0,1000,$6,$6)
            ''',
            reservation_id, pid, booking_number, today + timedelta(days=10), today + timedelta(days=11), created_at,
        )
        payment_id = uuid.uuid4()
        await conn.execute(
            '''
            INSERT INTO payments(
              id,"reservationId","amountKgs",method,status,provider,"externalRef","idempotencyKey","paidAt","createdAt","updatedAt"
            ) VALUES($1,$2,777,'CI_OWNER_ANALYTICS','RECEIVED','CI_OWNER_ANALYTICS',$3,$4,$5,$6,$6)
            ''',
            payment_id, reservation_id, f"OWNER-AN-{uuid.uuid4().hex}", f"owner-an-{uuid.uuid4().hex}", paid_at, created_at,
        )
        return {"today": today, "timezone": tz_name, "room_code": room["code"], "payment_id": str(payment_id)}
    finally:
        await conn.close()


def login(username: str, password: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return client


def main() -> None:
    facts = asyncio.run(seed_known_facts())
    owner = login(OWNER_USERNAME, OWNER_PASSWORD)
    reception = login(RECEPTION_USERNAME, RECEPTION_PASSWORD)
    today = facts["today"]
    params = {"from_date": today.isoformat(), "to_date": today.isoformat()}

    response = owner.get("/api/v1/admin/intelligence/operations-performance", params=params)
    response.raise_for_status()
    body = response.json()

    guest = body["guest_services"]
    assert guest["created_in_period"] == 3, guest
    assert guest["completed_in_period"] == 2, guest
    assert guest["active_now"] == 1, guest
    assert guest["urgent_now"] == 1, guest
    assert guest["avg_completion_minutes"] == 60.0, guest
    assert guest["past_due_date_active"] == 1, guest

    sla = body["guest_service_sla"]
    assert sla["status"] == "NOT_CONFIGURED" and sla["configured"] is False, sla
    assert sla["target_minutes"] is None and sla["breach_count"] is None, sla
    assert sla["due_date_overdue_active"] == 1, sla

    housekeeping = body["housekeeping"]
    assert housekeeping["created_in_period"] == 3, housekeeping
    assert housekeeping["completed_in_period"] == 2, housekeeping
    assert housekeeping["active_now"] == 1, housekeeping
    assert housekeeping["avg_completion_minutes"] == 30.0, housekeeping

    maintenance = body["maintenance"]
    assert maintenance["created_in_period"] == 3, maintenance
    assert maintenance["completed_in_period"] == 2, maintenance
    assert maintenance["active_now"] == 1, maintenance
    assert maintenance["avg_completion_minutes"] == 90.0, maintenance

    problem = next((item for item in body["problem_rooms"] if item["room_code"] == facts["room_code"]), None)
    assert problem and problem["maintenance_created_in_period"] == 3, body["problem_rooms"]
    recurring = next((item for item in body["recurring_faults"] if item["room_code"] == facts["room_code"]), None)
    assert recurring and recurring["occurrences"] == 2, body["recurring_faults"]
    assert recurring["normalized_exact_title"] == "air conditioner leak", recurring

    maid = next((item for item in body["staff_performance"] if item["role"] == "MAID"), None)
    tech = next((item for item in body["staff_performance"] if item["role"] == "TECHNICIAN"), None)
    assert maid and maid["completed_in_period"] == 2 and maid["active_now"] == 1 and maid["avg_completion_minutes"] == 30.0, maid
    assert tech and tech["completed_in_period"] == 2 and tech["active_now"] == 1 and tech["avg_completion_minutes"] == 90.0, tech

    forbidden = reception.get("/api/v1/admin/intelligence/operations-performance", params=params)
    assert forbidden.status_code == 403, forbidden.text

    dashboard = owner.get("/api/v1/admin/dashboard")
    dashboard.raise_for_status()
    dashboard_body = dashboard.json()
    assert dashboard_body["property"]["local_date"] == today.isoformat(), dashboard_body["property"]
    assert dashboard_body["finance"]["confirmed_payments_today_kgs"] == 777, dashboard_body["finance"]

    finance = owner.get("/api/v1/admin/finance/summary", params=params)
    finance.raise_for_status()
    assert finance.json()["period_payments"]["received_kgs"] == 777, finance.json()["period_payments"]

    executive_source = Path("apps/admin/components/OwnerExecutivePack.tsx").read_text(encoding="utf-8")
    assert "/core/api/v1/admin/finance/summary" in executive_source
    assert "canonical Finance Core" in executive_source
    operations_source = Path("apps/admin/components/OwnerOperationsPerformance.tsx").read_text(encoding="utf-8")
    assert "/core/api/v1/admin/intelligence/operations-performance" in operations_source
    assert "порог в Core не задан" in operations_source

    owner.close()
    reception.close()
    print("PASS: owner dashboard analytics reconcile task performance, recurring faults, non-fabricated SLA and hotel-local finance facts")


if __name__ == "__main__":
    main()
