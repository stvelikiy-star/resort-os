from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/growth", tags=["admin-growth-control"])
manager_access = require_roles("OWNER", "MANAGER")

KINDS = {"POST_STAY_FEEDBACK", "RETURN_GUEST", "MANAGER_FOLLOWUP"}
STATUSES = {"OPEN", "IN_PROGRESS", "DONE", "CANCELLED"}
TRANSITIONS = {
    "OPEN": {"IN_PROGRESS", "DONE", "CANCELLED"},
    "IN_PROGRESS": {"OPEN", "DONE", "CANCELLED"},
    "DONE": {"IN_PROGRESS"},
    "CANCELLED": {"OPEN"},
}


class EngagementCreate(BaseModel):
    guest_id: uuid.UUID
    reservation_id: uuid.UUID | None = None
    kind: str
    due_date: date | None = None
    channel_hint: str | None = Field(default=None, max_length=80)
    title: str = Field(min_length=2, max_length=240)
    notes: str | None = Field(default=None, max_length=12000)


class EngagementStatusPatch(BaseModel):
    status: str


class FeedbackRecord(BaseModel):
    score: int = Field(ge=0, le=10)
    feedback_text: str | None = Field(default=None, max_length=12000)


async def property_context(conn, property_code: str):
    row = await conn.fetchrow('SELECT id,code,name,timezone FROM properties WHERE code=$1', property_code)
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


def guest_name(row) -> str:
    return " ".join(part for part in [row.get("firstName"), row.get("lastName")] if part) or "Гость"


def nps_class(score: int | None) -> str | None:
    if score is None:
        return None
    if score >= 9:
        return "PROMOTER"
    if score >= 7:
        return "PASSIVE"
    return "DETRACTOR"


def serialize_engagement(row) -> dict[str, Any]:
    score = int(row["score"]) if row["score"] is not None else None
    return {
        "id": str(row["id"]),
        "kind": row["kind"],
        "status": row["status"],
        "guest": {
            "id": str(row["guestId"]),
            "name": guest_name(row),
            "phone": row["phone"],
            "email": row["email"],
        },
        "reservation": None if not row["reservationId"] else {
            "id": str(row["reservationId"]),
            "booking_number": row["bookingNumber"],
            "status": row["reservation_status"],
            "check_in": row["checkIn"],
            "check_out": row["checkOut"],
        },
        "due_date": row["dueDate"],
        "channel_hint": row["channelHint"],
        "title": row["title"],
        "notes": row["notes"],
        "score": score,
        "nps_class": nps_class(score),
        "feedback_text": row["feedbackText"],
        "completed_at": row["completedAt"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "outbound_authority": "NONE_AUTOMATIC",
    }


async def fetch_engagement(conn, engagement_id: uuid.UUID, property_id):
    return await conn.fetchrow(
        '''
        SELECT e.id,e."propertyId",e."guestId",e."reservationId",e.kind,e.status,e."dueDate",e."channelHint",
               e.title,e.notes,e.score,e."feedbackText",e."completedAt",e."createdAt",e."updatedAt",
               g."firstName",g."lastName",g.phone,g.email,
               r."bookingNumber",r.status::text AS reservation_status,r."checkIn",r."checkOut"
        FROM guest_engagements e
        JOIN guests g ON g.id=e."guestId"
        LEFT JOIN reservations r ON r.id=e."reservationId"
        WHERE e.id=$1 AND e."propertyId"=$2
        ''',
        engagement_id,
        property_id,
    )


@router.get("/engagements")
async def list_engagements(
    request: Request,
    kind: str | None = Query(default=None),
    engagement_status: str | None = Query(default=None, alias="status"),
    guest_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=150, ge=1, le=300),
    user: dict[str, Any] = Depends(manager_access),
):
    if kind and kind not in KINDS:
        raise HTTPException(status_code=422, detail="Unknown engagement kind")
    if engagement_status and engagement_status not in STATUSES:
        raise HTTPException(status_code=422, detail="Unknown engagement status")

    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT e.id,e."propertyId",e."guestId",e."reservationId",e.kind,e.status,e."dueDate",e."channelHint",
                   e.title,e.notes,e.score,e."feedbackText",e."completedAt",e."createdAt",e."updatedAt",
                   g."firstName",g."lastName",g.phone,g.email,
                   r."bookingNumber",r.status::text AS reservation_status,r."checkIn",r."checkOut"
            FROM guest_engagements e
            JOIN guests g ON g.id=e."guestId"
            LEFT JOIN reservations r ON r.id=e."reservationId"
            WHERE e."propertyId"=$1
              AND ($2::text IS NULL OR e.kind=$2)
              AND ($3::text IS NULL OR e.status=$3)
              AND ($4::uuid IS NULL OR e."guestId"=$4)
            ORDER BY
              CASE e.status WHEN 'OPEN' THEN 0 WHEN 'IN_PROGRESS' THEN 1 ELSE 2 END,
              e."dueDate" NULLS LAST,e."updatedAt" DESC
            LIMIT $5
            ''',
            prop["id"], kind, engagement_status, guest_id, limit,
        )
    return {"items": [serialize_engagement(row) for row in rows], "outbound_authority": "NONE_AUTOMATIC"}


@router.post("/engagements", status_code=status.HTTP_201_CREATED)
async def create_engagement(
    payload: EngagementCreate,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    kind = payload.kind.strip().upper()
    if kind not in KINDS:
        raise HTTPException(status_code=422, detail="Unknown engagement kind")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            pid = prop["id"]
            today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
            guest = await conn.fetchrow(
                'SELECT id,"firstName","lastName",phone,email FROM guests WHERE id=$1 AND "propertyId"=$2 FOR UPDATE',
                payload.guest_id, pid,
            )
            if not guest:
                raise HTTPException(status_code=404, detail="Guest not found")

            reservation = None
            if payload.reservation_id:
                reservation = await conn.fetchrow(
                    '''SELECT id,"primaryGuestId",status::text AS status,"bookingNumber","checkIn","checkOut"
                       FROM reservations WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                    payload.reservation_id, pid,
                )
                if not reservation:
                    raise HTTPException(status_code=404, detail="Reservation not found")
                if reservation["primaryGuestId"] != payload.guest_id:
                    raise HTTPException(status_code=409, detail={"code": "ENGAGEMENT_GUEST_RESERVATION_MISMATCH", "message": "Reservation belongs to another primary Guest."})

            if kind == "POST_STAY_FEEDBACK":
                if not reservation:
                    raise HTTPException(status_code=422, detail="POST_STAY_FEEDBACK requires reservation_id")
                if reservation["status"] != "CHECKED_OUT" or reservation["checkOut"] > today:
                    raise HTTPException(status_code=409, detail={"code": "POST_STAY_NOT_ELIGIBLE", "message": "Feedback engagement requires a completed CHECKED_OUT stay."})
                duplicate = await conn.fetchval(
                    '''SELECT id FROM guest_engagements WHERE "propertyId"=$1 AND "reservationId"=$2 AND kind='POST_STAY_FEEDBACK' ''',
                    pid, payload.reservation_id,
                )
                if duplicate:
                    raise HTTPException(status_code=409, detail={"code": "POST_STAY_FEEDBACK_EXISTS", "engagement_id": str(duplicate)})

            if kind == "RETURN_GUEST":
                completed = await conn.fetchval(
                    '''SELECT count(*) FROM reservations WHERE "propertyId"=$1 AND "primaryGuestId"=$2 AND status='CHECKED_OUT' AND "checkOut"<=$3::date''',
                    pid, payload.guest_id, today,
                )
                if not completed:
                    raise HTTPException(status_code=409, detail={"code": "RETURN_GUEST_NO_COMPLETED_STAY"})
                future = await conn.fetchval(
                    '''SELECT count(*) FROM reservations WHERE "propertyId"=$1 AND "primaryGuestId"=$2
                       AND status IN ('GUARANTEED','CHECKED_IN') AND "checkOut">=$3::date''',
                    pid, payload.guest_id, today,
                )
                if future:
                    raise HTTPException(status_code=409, detail={"code": "RETURN_GUEST_HAS_ACTIVE_RESERVATION"})
                existing = await conn.fetchval(
                    '''SELECT id FROM guest_engagements WHERE "propertyId"=$1 AND "guestId"=$2 AND kind='RETURN_GUEST' AND status IN ('OPEN','IN_PROGRESS') LIMIT 1''',
                    pid, payload.guest_id,
                )
                if existing:
                    raise HTTPException(status_code=409, detail={"code": "RETURN_GUEST_ACTIVE_EXISTS", "engagement_id": str(existing)})

            engagement_id = uuid.uuid4()
            try:
                await conn.execute(
                    '''
                    INSERT INTO guest_engagements
                      (id,"propertyId","guestId","reservationId",kind,status,"dueDate","channelHint",title,notes,"createdAt","updatedAt")
                    VALUES ($1,$2,$3,$4,$5,'OPEN',$6,$7,$8,$9,now(),now())
                    ''',
                    engagement_id,pid,payload.guest_id,payload.reservation_id,kind,payload.due_date,
                    payload.channel_hint.strip() if payload.channel_hint else None,payload.title.strip(),payload.notes,
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "23505" and kind == "POST_STAY_FEEDBACK":
                    raise HTTPException(status_code=409, detail={"code": "POST_STAY_FEEDBACK_EXISTS"}) from exc
                raise

            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                VALUES ($1,$2,'STAFF',$3,'CREATE_GUEST_ENGAGEMENT','GuestEngagement',$4,'PMS_GROWTH','SUCCESS',
                  jsonb_build_object('kind',$5::text,'guest_id',$6::text,'reservation_id',$7::text,'outbound_authority','NONE_AUTOMATIC'),now())
                ''',
                uuid.uuid4(),pid,user["id"],str(engagement_id),kind,str(payload.guest_id),str(payload.reservation_id) if payload.reservation_id else None,
            )
            row = await fetch_engagement(conn, engagement_id, pid)
    return serialize_engagement(row)


@router.patch("/engagements/{engagement_id}/status")
async def change_engagement_status(
    engagement_id: uuid.UUID,
    payload: EngagementStatusPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    target = payload.status.strip().upper()
    if target not in STATUSES:
        raise HTTPException(status_code=422, detail="Unknown engagement status")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            row = await fetch_engagement(conn, engagement_id, prop["id"])
            if not row:
                raise HTTPException(status_code=404, detail="Engagement not found")
            current = row["status"]
            if target == current:
                return serialize_engagement(row)
            if target not in TRANSITIONS[current]:
                raise HTTPException(status_code=409, detail={"code": "ENGAGEMENT_INVALID_TRANSITION", "from": current, "to": target})
            await conn.execute(
                '''UPDATE guest_engagements SET status=$1,"completedAt"=CASE WHEN $1='DONE' THEN now() ELSE NULL END,"updatedAt"=now()
                   WHERE id=$2 AND "propertyId"=$3''',
                target, engagement_id, prop["id"],
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'GUEST_ENGAGEMENT_STATUS','GuestEngagement',$4,'PMS_GROWTH','SUCCESS',
                     jsonb_build_object('status',$5::text),jsonb_build_object('status',$6::text),now())''',
                uuid.uuid4(),prop["id"],user["id"],str(engagement_id),current,target,
            )
            updated = await fetch_engagement(conn, engagement_id, prop["id"])
    return serialize_engagement(updated)


@router.post("/engagements/{engagement_id}/feedback")
async def record_feedback(
    engagement_id: uuid.UUID,
    payload: FeedbackRecord,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    classification = nps_class(payload.score)
    next_status = "IN_PROGRESS" if classification == "DETRACTOR" else "DONE"
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            row = await fetch_engagement(conn, engagement_id, prop["id"])
            if not row:
                raise HTTPException(status_code=404, detail="Engagement not found")
            if row["kind"] != "POST_STAY_FEEDBACK":
                raise HTTPException(status_code=409, detail={"code": "FEEDBACK_WRONG_ENGAGEMENT_KIND"})
            if row["status"] == "CANCELLED":
                raise HTTPException(status_code=409, detail={"code": "FEEDBACK_ENGAGEMENT_CANCELLED"})
            await conn.execute(
                '''
                UPDATE guest_engagements
                SET score=$1,"feedbackText"=$2,status=$3,
                    "completedAt"=CASE WHEN $3='DONE' THEN now() ELSE NULL END,"updatedAt"=now()
                WHERE id=$4 AND "propertyId"=$5
                ''',
                payload.score,payload.feedback_text,next_status,engagement_id,prop["id"],
            )
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'RECORD_GUEST_FEEDBACK','GuestEngagement',$4,'PMS_GROWTH','SUCCESS',
                     jsonb_build_object('score',$5::int,'nps_class',$6::text,'status',$7::text,'outbound_authority','NONE_AUTOMATIC'),now())''',
                uuid.uuid4(),prop["id"],user["id"],str(engagement_id),payload.score,classification,next_status,
            )
            updated = await fetch_engagement(conn, engagement_id, prop["id"])
    return serialize_engagement(updated) | {"recovery_required": classification == "DETRACTOR"}


@router.get("/candidates/post-stay")
async def post_stay_candidates(
    request: Request,
    lookback_days: int = Query(default=14, ge=1, le=180),
    limit: int = Query(default=100, ge=1, le=300),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
        rows = await conn.fetch(
            '''
            SELECT r.id,r."bookingNumber",r."checkIn",r."checkOut",r."primaryGuestId",
                   g."firstName",g."lastName",g.phone,g.email
            FROM reservations r
            JOIN guests g ON g.id=r."primaryGuestId"
            WHERE r."propertyId"=$1 AND r.status='CHECKED_OUT'
              AND r."checkOut"<=$2::date AND r."checkOut">=$3::date
              AND (g.phone IS NOT NULL OR g.email IS NOT NULL)
              AND NOT EXISTS (
                SELECT 1 FROM guest_engagements e
                WHERE e."propertyId"=$1 AND e."reservationId"=r.id AND e.kind='POST_STAY_FEEDBACK'
              )
            ORDER BY r."checkOut" DESC,r."createdAt" DESC
            LIMIT $4
            ''',
            prop["id"],today,today-timedelta(days=lookback_days),limit,
        )
    return {
        "items": [{
            "reservation_id": str(row["id"]),
            "booking_number": row["bookingNumber"],
            "guest_id": str(row["primaryGuestId"]),
            "guest_name": guest_name(row),
            "phone": row["phone"],
            "email": row["email"],
            "check_in": row["checkIn"],
            "check_out": row["checkOut"],
            "days_since_checkout": (today-row["checkOut"]).days,
            "recommended_kind": "POST_STAY_FEEDBACK",
            "outbound_policy": "MANAGER_REVIEW_REQUIRED",
        } for row in rows],
        "truth": "Candidates are derived from completed stays and contact availability only. Listing a Guest does not establish marketing consent or send authority.",
    }


@router.get("/candidates/reactivation")
async def reactivation_candidates(
    request: Request,
    min_days_since_checkout: int = Query(default=30, ge=1, le=3650),
    limit: int = Query(default=100, ge=1, le=300),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
        rows = await conn.fetch(
            '''
            WITH history AS (
              SELECT g.id,g."firstName",g."lastName",g.phone,g.email,
                     count(r.id) FILTER (WHERE r.status='CHECKED_OUT')::int AS completed_stays,
                     max(r."checkOut") FILTER (WHERE r.status='CHECKED_OUT') AS last_checkout,
                     COALESCE(sum(r."totalKgs") FILTER (WHERE r.status='CHECKED_OUT'),0)::bigint AS completed_booked_value_kgs
              FROM guests g
              LEFT JOIN reservations r ON r."primaryGuestId"=g.id AND r."propertyId"=$1
              WHERE g."propertyId"=$1
              GROUP BY g.id
            )
            SELECT h.*
            FROM history h
            WHERE h.completed_stays>0 AND h.last_checkout<=$2::date
              AND (h.phone IS NOT NULL OR h.email IS NOT NULL)
              AND NOT EXISTS (
                SELECT 1 FROM reservations future
                WHERE future."propertyId"=$1 AND future."primaryGuestId"=h.id
                  AND future.status IN ('GUARANTEED','CHECKED_IN') AND future."checkOut">=$3::date
              )
              AND NOT EXISTS (
                SELECT 1 FROM guest_engagements e
                WHERE e."propertyId"=$1 AND e."guestId"=h.id AND e.kind='RETURN_GUEST' AND e.status IN ('OPEN','IN_PROGRESS')
              )
            ORDER BY h.completed_stays DESC,h.last_checkout DESC
            LIMIT $4
            ''',
            prop["id"],today-timedelta(days=min_days_since_checkout),today,limit,
        )
    return {
        "items": [{
            "guest_id": str(row["id"]),
            "guest_name": guest_name(row),
            "phone": row["phone"],
            "email": row["email"],
            "completed_stays": int(row["completed_stays"]),
            "last_checkout": row["last_checkout"],
            "days_since_checkout": (today-row["last_checkout"]).days,
            "completed_booked_value_kgs": int(row["completed_booked_value_kgs"] or 0),
            "recommended_kind": "RETURN_GUEST",
            "outbound_policy": "MANAGER_REVIEW_REQUIRED",
        } for row in rows],
        "parameters": {"min_days_since_checkout": min_days_since_checkout},
        "truth": "Candidates are factual past Guests with no active future stay and no active RETURN_GUEST engagement. This is not consent, propensity scoring or automatic send authority.",
    }


@router.get("/summary")
async def growth_summary(
    request: Request,
    min_days_since_checkout: int = Query(default=30, ge=1, le=3650),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        pid = prop["id"]
        today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
        queue = await conn.fetchrow(
            '''
            SELECT count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS'))::int AS active,
                   count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS') AND "dueDate"<$2::date)::int AS overdue,
                   count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND status IN ('OPEN','IN_PROGRESS'))::int AS feedback_open,
                   count(*) FILTER (WHERE kind='RETURN_GUEST' AND status IN ('OPEN','IN_PROGRESS'))::int AS return_open
            FROM guest_engagements WHERE "propertyId"=$1
            ''',
            pid,today,
        )
        feedback = await conn.fetchrow(
            '''
            SELECT count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK')::int AS total_engagements,
                   count(score) FILTER (WHERE kind='POST_STAY_FEEDBACK')::int AS scored,
                   round(avg(score) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND score IS NOT NULL),2) AS average_score,
                   count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND score BETWEEN 9 AND 10)::int AS promoters,
                   count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND score BETWEEN 7 AND 8)::int AS passives,
                   count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND score BETWEEN 0 AND 6)::int AS detractors,
                   count(*) FILTER (WHERE kind='POST_STAY_FEEDBACK' AND score BETWEEN 0 AND 6 AND status='IN_PROGRESS')::int AS recovery_open
            FROM guest_engagements WHERE "propertyId"=$1
            ''',
            pid,
        )
        post_stay_candidates = int(await conn.fetchval(
            '''SELECT count(*) FROM reservations r JOIN guests g ON g.id=r."primaryGuestId"
               WHERE r."propertyId"=$1 AND r.status='CHECKED_OUT' AND r."checkOut"<=$2::date AND r."checkOut">=$3::date
                 AND (g.phone IS NOT NULL OR g.email IS NOT NULL)
                 AND NOT EXISTS (SELECT 1 FROM guest_engagements e WHERE e."propertyId"=$1 AND e."reservationId"=r.id AND e.kind='POST_STAY_FEEDBACK')''',
            pid,today,today-timedelta(days=14),
        ) or 0)
        reactivation_candidates = int(await conn.fetchval(
            '''
            WITH history AS (
              SELECT g.id,max(r."checkOut") FILTER (WHERE r.status='CHECKED_OUT') AS last_checkout,
                     count(r.id) FILTER (WHERE r.status='CHECKED_OUT') AS completed
              FROM guests g LEFT JOIN reservations r ON r."primaryGuestId"=g.id AND r."propertyId"=$1
              WHERE g."propertyId"=$1 AND (g.phone IS NOT NULL OR g.email IS NOT NULL) GROUP BY g.id
            )
            SELECT count(*) FROM history h WHERE h.completed>0 AND h.last_checkout<=$2::date
              AND NOT EXISTS (SELECT 1 FROM reservations future WHERE future."propertyId"=$1 AND future."primaryGuestId"=h.id AND future.status IN ('GUARANTEED','CHECKED_IN') AND future."checkOut">=$3::date)
              AND NOT EXISTS (SELECT 1 FROM guest_engagements e WHERE e."propertyId"=$1 AND e."guestId"=h.id AND e.kind='RETURN_GUEST' AND e.status IN ('OPEN','IN_PROGRESS'))
            ''',
            pid,today-timedelta(days=min_days_since_checkout),today,
        ) or 0)

    scored = int(feedback["scored"] or 0)
    promoters = int(feedback["promoters"] or 0)
    detractors = int(feedback["detractors"] or 0)
    nps = round((promoters-detractors)*100/scored) if scored else None
    return {
        "local_date": today,
        "queue": {
            "active": int(queue["active"] or 0),
            "overdue": int(queue["overdue"] or 0),
            "feedback_open": int(queue["feedback_open"] or 0),
            "return_open": int(queue["return_open"] or 0),
        },
        "feedback": {
            "engagements": int(feedback["total_engagements"] or 0),
            "scored": scored,
            "average_score": float(feedback["average_score"]) if feedback["average_score"] is not None else None,
            "promoters": promoters,
            "passives": int(feedback["passives"] or 0),
            "detractors": detractors,
            "recovery_open": int(feedback["recovery_open"] or 0),
            "nps": nps,
            "nps_sample_size": scored,
        },
        "candidates": {
            "post_stay_14d": post_stay_candidates,
            "reactivation": reactivation_candidates,
            "reactivation_min_days": min_days_since_checkout,
        },
        "truth": {
            "nps": "NPS uses standard 0-6 detractor, 7-8 passive, 9-10 promoter classification over stored feedback scores; sample size is always exposed.",
            "outbound": "This module creates internal manager work only. It contains no outbound-send endpoint and grants no automatic marketing authority.",
            "reactivation": "Candidate status is factual stay/contact history only; it is not marketing consent or a propensity score.",
        },
    }
