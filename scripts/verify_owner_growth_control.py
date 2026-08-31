import asyncio
import os
import uuid
from datetime import date, timedelta

import asyncpg
import httpx

BASE_URL = os.environ.get("RESORT_CORE_TEST_URL", "http://127.0.0.1:8000")
OWNER_USERNAME = os.environ.get("BOOTSTRAP_OWNER_USERNAME", "ci-owner")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "CI-Owner-Strong-Password-2026")
DATABASE_URL = os.environ["DATABASE_URL"].split("?")[0]


def choose_option(client: httpx.Client, start: date, end: date):
    response = client.get(
        "/api/v1/booking/check-availability",
        params={"check_in": start.isoformat(), "check_out": end.isoformat(), "adults": 2, "children": 0},
    )
    response.raise_for_status()
    return next(item for item in response.json()["results"] if item["available_count"] > 0 and item["pricing"]["sellable"])


def create_reservation(client: httpx.Client, guest_name: str, phone: str, email: str, start: date, key: str):
    end = start + timedelta(days=2)
    option = choose_option(client, start, end)
    request = client.post(
        "/api/v1/booking/requests",
        json={
            "guest_name": guest_name,
            "phone": phone,
            "email": email,
            "check_in": start.isoformat(),
            "check_out": end.isoformat(),
            "adults": 2,
            "children": 0,
            "room_type_code": option["room_type_code"],
            "source": "CI_OWNER_GROWTH",
        },
    )
    request.raise_for_status()
    request_id = request.json()["id"]
    quote = client.post(
        f"/api/v1/admin/booking/requests/{request_id}/quote",
        json={"room_type_code": option["room_type_code"]},
    )
    quote.raise_for_status()
    confirm = client.post(
        f"/api/v1/admin/booking/requests/{request_id}/confirm-payment",
        json={
            "amount_kgs": 1000,
            "method": "CI_MANAGER",
            "external_ref": f"growth-{key}",
            "idempotency_key": f"growth-payment-{key}",
        },
    )
    confirm.raise_for_status()
    return confirm.json()


async def mark_completed(reservation_id: str, check_in: date, check_out: date):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            rid = uuid.UUID(reservation_id)
            await conn.execute(
                'UPDATE reservations SET status=\'CHECKED_OUT\',"checkIn"=$2,"checkOut"=$3,"updatedAt"=now() WHERE id=$1',
                rid,
                check_in,
                check_out,
            )
            await conn.execute(
                'UPDATE inventory_blocks SET "startDate"=$2,"endDate"=$3,"updatedAt"=now() WHERE "reservationId"=$1',
                rid,
                check_in,
                check_out,
            )
    finally:
        await conn.close()


async def reservation_guest_id(reservation_id: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        value = await conn.fetchval('SELECT "primaryGuestId" FROM reservations WHERE id=$1', uuid.UUID(reservation_id))
        assert value is not None
        return str(value)
    finally:
        await conn.close()


async def create_foreign_guest() -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        property_id = uuid.uuid4()
        guest_id = uuid.uuid4()
        await conn.execute(
            '''INSERT INTO properties (id,code,name,timezone,currency,"beachCommissionBps","createdAt","updatedAt")
               VALUES ($1,$2,'Foreign Growth Property','Asia/Bishkek','KGS',500,now(),now())''',
            property_id,
            f"FOREIGN_GROWTH_{str(property_id)[:8]}",
        )
        await conn.execute(
            '''INSERT INTO guests (id,"propertyId","firstName",phone,"createdAt","updatedAt")
               VALUES ($1,$2,'Foreign Guest','+996700000999',now(),now())''',
            guest_id,
            property_id,
        )
        return str(guest_id)
    finally:
        await conn.close()


async def prove_database_state(feedback_id: str, return_id: str, return_guest_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        pid = await conn.fetchval("SELECT id FROM properties WHERE code='THREE_CROWNS'")
        migrations = await conn.fetch("SELECT migration_name FROM _prisma_migrations WHERE finished_at IS NOT NULL ORDER BY started_at")
        names = [row["migration_name"] for row in migrations]
        assert names == ["0_init", "1_site_content", "2_guest_service_tasks", "3_owner_analytics_snapshots", "4_guest_engagements", "5_guest_os_core"]

        table = await conn.fetchval("SELECT to_regclass('public.guest_engagements')::text")
        assert table == "guest_engagements"
        feedback = await conn.fetchrow('SELECT kind,status,score FROM guest_engagements WHERE id=$1 AND "propertyId"=$2', uuid.UUID(feedback_id), pid)
        assert feedback["kind"] == "POST_STAY_FEEDBACK"
        assert feedback["status"] == "DONE"
        assert feedback["score"] == 5
        return_row = await conn.fetchrow('SELECT kind,status,"guestId" FROM guest_engagements WHERE id=$1 AND "propertyId"=$2', uuid.UUID(return_id), pid)
        assert return_row["kind"] == "RETURN_GUEST"
        assert str(return_row["guestId"]) == return_guest_id

        invalid_id = uuid.uuid4()
        violated = False
        try:
            await conn.execute(
                '''INSERT INTO guest_engagements
                   (id,"propertyId","guestId",kind,status,title,score,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,'RETURN_GUEST','OPEN','Invalid score fixture',10,now(),now())''',
                invalid_id,
                pid,
                uuid.UUID(return_guest_id),
            )
        except asyncpg.CheckViolationError:
            violated = True
        assert violated, "score-kind database constraint did not reject RETURN_GUEST score"

        audits = await conn.fetch(
            '''SELECT action,count(*)::int AS c FROM audit_logs
               WHERE "propertyId"=$1 AND action IN ('CREATE_GUEST_ENGAGEMENT','RECORD_GUEST_FEEDBACK','GUEST_ENGAGEMENT_STATUS')
               GROUP BY action''',
            pid,
        )
        counts = {row["action"]: row["c"] for row in audits}
        assert counts.get("CREATE_GUEST_ENGAGEMENT", 0) >= 2
        assert counts.get("RECORD_GUEST_FEEDBACK", 0) >= 1
        assert counts.get("GUEST_ENGAGEMENT_STATUS", 0) >= 1
    finally:
        await conn.close()


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    unauth = client.get("/api/v1/admin/growth/summary")
    assert unauth.status_code == 401

    login = client.post("/api/v1/auth/login", json={"username": OWNER_USERNAME, "password": OWNER_PASSWORD})
    login.raise_for_status()

    initial = client.get("/api/v1/admin/growth/summary?min_days_since_checkout=30")
    initial.raise_for_status()
    initial_body = initial.json()
    today = date.fromisoformat(initial_body["local_date"])
    assert initial_body["feedback"]["nps"] is None
    assert initial_body["feedback"]["nps_sample_size"] == 0
    assert initial_body["queue"]["active"] == 0

    feedback_reservation = create_reservation(
        client,
        "Growth Feedback CI",
        "+996555881101",
        "growth.feedback.ci@example.com",
        today + timedelta(days=10),
        "feedback",
    )
    return_reservation = create_reservation(
        client,
        "Growth Return CI",
        "+996555881102",
        "growth.return.ci@example.com",
        today + timedelta(days=20),
        "return",
    )
    blocked_reservation = create_reservation(
        client,
        "Growth Future CI",
        "+996555881103",
        "growth.future.ci@example.com",
        today + timedelta(days=30),
        "future-completed",
    )

    asyncio.run(mark_completed(feedback_reservation["reservation_id"], today - timedelta(days=4), today - timedelta(days=2)))
    asyncio.run(mark_completed(return_reservation["reservation_id"], today - timedelta(days=62), today - timedelta(days=60)))
    asyncio.run(mark_completed(blocked_reservation["reservation_id"], today - timedelta(days=92), today - timedelta(days=90)))

    feedback_guest_id = asyncio.run(reservation_guest_id(feedback_reservation["reservation_id"]))
    return_guest_id = asyncio.run(reservation_guest_id(return_reservation["reservation_id"]))
    blocked_guest_id = asyncio.run(reservation_guest_id(blocked_reservation["reservation_id"]))

    future_same_guest = create_reservation(
        client,
        "Growth Future CI",
        "+996 555 881 103",
        "GROWTH.FUTURE.CI@EXAMPLE.COM",
        today + timedelta(days=40),
        "future-active",
    )
    assert asyncio.run(reservation_guest_id(future_same_guest["reservation_id"])) == blocked_guest_id

    post = client.get("/api/v1/admin/growth/candidates/post-stay", params={"lookback_days": 14, "limit": 100})
    post.raise_for_status()
    post_ids = {item["reservation_id"] for item in post.json()["items"]}
    assert feedback_reservation["reservation_id"] in post_ids
    assert return_reservation["reservation_id"] not in post_ids
    assert post.json()["truth"].startswith("Candidates are derived")

    react = client.get("/api/v1/admin/growth/candidates/reactivation", params={"min_days_since_checkout": 30, "limit": 100})
    react.raise_for_status()
    react_ids = {item["guest_id"] for item in react.json()["items"]}
    assert return_guest_id in react_ids
    assert feedback_guest_id not in react_ids
    assert blocked_guest_id not in react_ids

    feedback_create = client.post(
        "/api/v1/admin/growth/engagements",
        json={
            "guest_id": feedback_guest_id,
            "reservation_id": feedback_reservation["reservation_id"],
            "kind": "POST_STAY_FEEDBACK",
            "due_date": (today + timedelta(days=1)).isoformat(),
            "channel_hint": "PHONE_OR_MESSENGER",
            "title": "CI post-stay feedback",
            "notes": "No automatic outbound.",
        },
    )
    feedback_create.raise_for_status()
    feedback_engagement = feedback_create.json()
    assert feedback_engagement["outbound_authority"] == "NONE_AUTOMATIC"
    feedback_id = feedback_engagement["id"]

    duplicate_feedback = client.post(
        "/api/v1/admin/growth/engagements",
        json={
            "guest_id": feedback_guest_id,
            "reservation_id": feedback_reservation["reservation_id"],
            "kind": "POST_STAY_FEEDBACK",
            "title": "Duplicate feedback",
        },
    )
    assert duplicate_feedback.status_code == 409
    assert duplicate_feedback.json()["detail"]["code"] == "POST_STAY_FEEDBACK_EXISTS"

    wrong_guest_feedback = client.post(
        "/api/v1/admin/growth/engagements",
        json={
            "guest_id": return_guest_id,
            "reservation_id": feedback_reservation["reservation_id"],
            "kind": "POST_STAY_FEEDBACK",
            "title": "Wrong guest fixture",
        },
    )
    assert wrong_guest_feedback.status_code == 409
    assert wrong_guest_feedback.json()["detail"]["code"] == "ENGAGEMENT_GUEST_RESERVATION_MISMATCH"

    score = client.post(
        f"/api/v1/admin/growth/engagements/{feedback_id}/feedback",
        json={"score": 5, "feedback_text": "CI factual detractor feedback"},
    )
    score.raise_for_status()
    scored = score.json()
    assert scored["score"] == 5
    assert scored["nps_class"] == "DETRACTOR"
    assert scored["status"] == "IN_PROGRESS"
    assert scored["recovery_required"] is True

    after_score = client.get("/api/v1/admin/growth/summary?min_days_since_checkout=30")
    after_score.raise_for_status()
    score_summary = after_score.json()
    assert score_summary["feedback"]["scored"] == 1
    assert score_summary["feedback"]["nps_sample_size"] == 1
    assert score_summary["feedback"]["nps"] == -100
    assert score_summary["feedback"]["detractors"] == 1
    assert score_summary["feedback"]["recovery_open"] == 1
    assert "no outbound-send endpoint" in score_summary["truth"]["outbound"]

    complete_recovery = client.patch(
        f"/api/v1/admin/growth/engagements/{feedback_id}/status",
        json={"status": "DONE"},
    )
    complete_recovery.raise_for_status()
    assert complete_recovery.json()["status"] == "DONE"

    return_create = client.post(
        "/api/v1/admin/growth/engagements",
        json={
            "guest_id": return_guest_id,
            "kind": "RETURN_GUEST",
            "due_date": (today + timedelta(days=3)).isoformat(),
            "channel_hint": "PHONE_OR_MESSENGER",
            "title": "CI return guest",
            "notes": "Manager review required before communication.",
        },
    )
    return_create.raise_for_status()
    return_engagement = return_create.json()
    return_id = return_engagement["id"]
    assert return_engagement["outbound_authority"] == "NONE_AUTOMATIC"

    duplicate_return = client.post(
        "/api/v1/admin/growth/engagements",
        json={"guest_id": return_guest_id, "kind": "RETURN_GUEST", "title": "Duplicate return"},
    )
    assert duplicate_return.status_code == 409
    assert duplicate_return.json()["detail"]["code"] == "RETURN_GUEST_ACTIVE_EXISTS"

    blocked_return = client.post(
        "/api/v1/admin/growth/engagements",
        json={"guest_id": blocked_guest_id, "kind": "RETURN_GUEST", "title": "Must be blocked by future stay"},
    )
    assert blocked_return.status_code == 409
    assert blocked_return.json()["detail"]["code"] == "RETURN_GUEST_HAS_ACTIVE_RESERVATION"

    react_after = client.get("/api/v1/admin/growth/candidates/reactivation", params={"min_days_since_checkout": 30, "limit": 100})
    react_after.raise_for_status()
    assert return_guest_id not in {item["guest_id"] for item in react_after.json()["items"]}

    foreign_guest_id = asyncio.run(create_foreign_guest())
    foreign = client.post(
        "/api/v1/admin/growth/engagements",
        json={"guest_id": foreign_guest_id, "kind": "MANAGER_FOLLOWUP", "title": "Foreign property fixture"},
    )
    assert foreign.status_code == 404

    openapi = client.get("/openapi.json")
    openapi.raise_for_status()
    growth_paths = [path for path in openapi.json()["paths"] if path.startswith("/api/v1/admin/growth")]
    assert growth_paths
    assert not any("send" in path.lower() or "outbound" in path.lower() for path in growth_paths)

    listed = client.get("/api/v1/admin/growth/engagements", params={"limit": 200})
    listed.raise_for_status()
    assert listed.json()["outbound_authority"] == "NONE_AUTOMATIC"
    ids = {item["id"] for item in listed.json()["items"]}
    assert {feedback_id, return_id}.issubset(ids)

    asyncio.run(prove_database_state(feedback_id, return_id, return_guest_id))
    client.close()
    print("OWNER_GROWTH_CONTROL_E2E_OK")


if __name__ == "__main__":
    main()