from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles
from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")

admin_router = APIRouter(prefix="/api/v1/admin/intelligence", tags=["owner-intelligence"])
automation_router = APIRouter(prefix="/api/v1/automation/intelligence", tags=["automation-owner-intelligence"])
manager_access = require_roles("OWNER", "MANAGER")


async def property_context(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id,code,name,timezone,currency FROM properties WHERE code=$1',
        property_code,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value or {})


def _validate_horizon(horizon_days: int, maximum: int = 367) -> int:
    if horizon_days < 1 or horizon_days > maximum:
        raise HTTPException(status_code=422, detail=f"horizon_days must be between 1 and {maximum}")
    return horizon_days


async def build_forward_snapshot(conn, prop, as_of: date, horizon_days: int) -> dict[str, Any]:
    horizon_days = _validate_horizon(horizon_days)
    end_exclusive = as_of + timedelta(days=horizon_days)
    pid = prop["id"]

    room_count = int(await conn.fetchval('SELECT count(*) FROM rooms WHERE "propertyId"=$1', pid) or 0)

    rows = await conn.fetch(
        '''
        WITH days AS (
          SELECT generate_series($2::date,$3::date - 1,interval '1 day')::date AS d
        ), capacity AS (
          SELECT day.d,
                 count(room.id) FILTER (
                   WHERE room."operationalState" <> 'TECH_BLOCK'
                     AND NOT EXISTS (
                       SELECT 1 FROM inventory_blocks ib
                       WHERE ib."roomId"=room.id AND ib.active=true
                         AND ib."blockType" IN ('MAINTENANCE','MANUAL')
                         AND ib."startDate"<=day.d AND ib."endDate">day.d
                     )
                 )::int AS available_rooms
          FROM days day
          CROSS JOIN rooms room
          WHERE room."propertyId"=$1
          GROUP BY day.d
        ), booked AS (
          SELECT day.d,count(DISTINCT ib."roomId")::int AS booked_rooms
          FROM days day
          LEFT JOIN inventory_blocks ib
            ON ib.active=true AND ib."blockType"='RESERVATION'
           AND ib."startDate"<=day.d AND ib."endDate">day.d
          LEFT JOIN rooms room ON room.id=ib."roomId" AND room."propertyId"=$1
          LEFT JOIN reservations r ON r.id=ib."reservationId" AND r.status IN ('GUARANTEED','CHECKED_IN')
          WHERE room.id IS NOT NULL AND r.id IS NOT NULL
          GROUP BY day.d
        ), value_by_day AS (
          SELECT day.d,
                 count(DISTINCT r.id)::int AS reservations,
                 COALESCE(SUM(
                   CASE WHEN (r."checkOut"-r."checkIn")>0
                        THEN r."totalKgs"::numeric/(r."checkOut"-r."checkIn")
                        ELSE 0 END
                 ),0)::numeric AS allocated_value_kgs
          FROM days day
          LEFT JOIN reservations r
            ON r."propertyId"=$1
           AND r.status IN ('GUARANTEED','CHECKED_IN')
           AND r."checkIn"<=day.d AND r."checkOut">day.d
          GROUP BY day.d
        ), movement AS (
          SELECT day.d,
                 count(DISTINCT r.id) FILTER (WHERE r."checkIn"=day.d)::int AS arrivals,
                 count(DISTINCT r.id) FILTER (WHERE r."checkOut"=day.d)::int AS departures
          FROM days day
          LEFT JOIN reservations r
            ON r."propertyId"=$1
           AND r.status IN ('GUARANTEED','CHECKED_IN')
           AND (r."checkIn"=day.d OR r."checkOut"=day.d)
          GROUP BY day.d
        )
        SELECT day.d,
               COALESCE(capacity.available_rooms,0)::int AS available_rooms,
               COALESCE(booked.booked_rooms,0)::int AS booked_rooms,
               COALESCE(value_by_day.reservations,0)::int AS reservations,
               COALESCE(value_by_day.allocated_value_kgs,0)::numeric AS allocated_value_kgs,
               COALESCE(movement.arrivals,0)::int AS arrivals,
               COALESCE(movement.departures,0)::int AS departures
        FROM days day
        LEFT JOIN capacity ON capacity.d=day.d
        LEFT JOIN booked ON booked.d=day.d
        LEFT JOIN value_by_day ON value_by_day.d=day.d
        LEFT JOIN movement ON movement.d=day.d
        ORDER BY day.d
        ''',
        pid,
        as_of,
        end_exclusive,
    )

    active = await conn.fetchrow(
        '''
        WITH paid AS (
          SELECT "reservationId",COALESCE(SUM("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS paid_kgs
          FROM payments WHERE "reservationId" IS NOT NULL GROUP BY "reservationId"
        )
        SELECT count(*)::int AS active_reservations,
               COALESCE(SUM(r."totalKgs"),0)::bigint AS active_total_kgs,
               COALESCE(SUM(COALESCE(p.paid_kgs,0)),0)::bigint AS active_paid_kgs,
               COALESCE(SUM(GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)),0)::bigint AS active_outstanding_kgs
        FROM reservations r
        LEFT JOIN paid p ON p."reservationId"=r.id
        WHERE r."propertyId"=$1 AND r.status IN ('GUARANTEED','CHECKED_IN')
          AND r."checkOut">=$2::date
        ''',
        pid,
        as_of,
    )

    days: list[dict[str, Any]] = []
    for row in rows:
        available = int(row["available_rooms"] or 0)
        booked = int(row["booked_rooms"] or 0)
        allocated = round(float(row["allocated_value_kgs"] or 0))
        days.append(
            {
                "date": row["d"].isoformat(),
                "available_rooms": available,
                "booked_rooms": booked,
                "occupancy_on_books_percent": round(booked * 100 / available, 1) if available else 0.0,
                "reservations": int(row["reservations"] or 0),
                "allocated_booked_value_kgs": allocated,
                "arrivals": int(row["arrivals"] or 0),
                "departures": int(row["departures"] or 0),
            }
        )

    available_nights = sum(item["available_rooms"] for item in days)
    booked_nights = sum(item["booked_rooms"] for item in days)
    allocated_value = sum(item["allocated_booked_value_kgs"] for item in days)

    return {
        "version": 1,
        "property": {"code": prop["code"], "name": prop["name"], "currency": prop["currency"]},
        "as_of": as_of.isoformat(),
        "horizon_days": horizon_days,
        "end_exclusive": end_exclusive.isoformat(),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "room_count": room_count,
            "available_room_nights": available_nights,
            "booked_room_nights": booked_nights,
            "occupancy_on_books_percent": round(booked_nights * 100 / available_nights, 1) if available_nights else 0.0,
            "allocated_booked_value_kgs": allocated_value,
            "active_reservations": int(active["active_reservations"] or 0),
            "active_total_kgs": int(active["active_total_kgs"] or 0),
            "active_paid_kgs": int(active["active_paid_kgs"] or 0),
            "active_outstanding_kgs": int(active["active_outstanding_kgs"] or 0),
        },
        "days": days,
        "truth": {
            "source": "RESORT_CORE_POSTGRESQL",
            "meaning": "Forward on-books management snapshot from current reservations/inventory; not a statistical demand forecast.",
            "value": "Allocated booked value distributes Reservation.totalKgs evenly across stay nights for management comparison only.",
            "capacity": "Future available rooms subtract current TECH_BLOCK rooms plus active MAINTENANCE/MANUAL date blocks; future repair resolution is not predicted.",
        },
    }


async def capture_snapshot(conn, prop, as_of: date, horizon_days: int, actor_type: str, actor_id: str | None, source: str):
    payload = await build_forward_snapshot(conn, prop, as_of, horizon_days)
    snapshot_id = uuid.uuid4()
    row = await conn.fetchrow(
        '''
        INSERT INTO owner_analytics_snapshots
          (id,"propertyId","snapshotDate","horizonDays","payloadJson","createdAt","updatedAt")
        VALUES ($1,$2,$3,$4,$5::jsonb,now(),now())
        ON CONFLICT ("propertyId","snapshotDate") DO UPDATE
          SET "horizonDays"=EXCLUDED."horizonDays","payloadJson"=EXCLUDED."payloadJson","updatedAt"=now()
        RETURNING id,"createdAt","updatedAt"
        ''',
        snapshot_id,
        prop["id"],
        as_of,
        horizon_days,
        json.dumps(payload, ensure_ascii=False),
    )
    await conn.execute(
        '''
        INSERT INTO audit_logs
          (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt")
        VALUES ($1,$2,$3,$4,'CAPTURE_OWNER_ANALYTICS_SNAPSHOT','OwnerAnalyticsSnapshot',$5,$6,'SUCCESS',
          jsonb_build_object('snapshot_date',$7::text,'horizon_days',$8::int,'booked_room_nights',$9::int),now())
        ''',
        uuid.uuid4(),
        prop["id"],
        actor_type,
        actor_id,
        str(row["id"]),
        source,
        as_of.isoformat(),
        horizon_days,
        payload["summary"]["booked_room_nights"],
    )
    return {
        "id": str(row["id"]),
        "snapshot_date": as_of,
        "horizon_days": horizon_days,
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "payload": payload,
    }


@admin_router.post("/snapshots/capture")
async def admin_capture_snapshot(
    request: Request,
    horizon_days: int = Query(default=180, ge=1, le=367),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
            return await capture_snapshot(conn, prop, today, horizon_days, "STAFF", user["id"], "PMS")


@automation_router.post("/snapshots/capture")
async def automation_capture_snapshot(
    request: Request,
    horizon_days: int = Query(default=180, ge=1, le=367),
    actor: dict[str, Any] = Depends(require_automation_service),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, PROPERTY_CODE)
            today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
            return await capture_snapshot(conn, prop, today, horizon_days, actor["actor_type"], actor["actor_id"], "AUTOMATION")


@admin_router.get("/snapshots")
async def list_snapshots(
    request: Request,
    limit: int = Query(default=30, ge=1, le=180),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        rows = await conn.fetch(
            '''
            SELECT id,"snapshotDate","horizonDays","payloadJson","createdAt","updatedAt"
            FROM owner_analytics_snapshots
            WHERE "propertyId"=$1
            ORDER BY "snapshotDate" DESC
            LIMIT $2
            ''',
            prop["id"],
            limit,
        )
    return {
        "items": [
            {
                "id": str(row["id"]),
                "snapshot_date": row["snapshotDate"],
                "horizon_days": row["horizonDays"],
                "summary": _payload(row["payloadJson"]).get("summary", {}),
                "created_at": row["createdAt"],
                "updated_at": row["updatedAt"],
            }
            for row in rows
        ],
        "truth": "One management snapshot per hotel-local date; same-day re-capture updates that date rather than fabricating intraday pickup history.",
    }


@admin_router.get("/pickup")
async def booking_pickup(
    request: Request,
    from_date: date = Query(),
    to_date: date = Query(),
    baseline_date: date | None = Query(default=None),
    user: dict[str, Any] = Depends(manager_access),
):
    if to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    if (to_date - from_date).days + 1 > 180:
        raise HTTPException(status_code=422, detail="pickup range cannot exceed 180 days")

    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
        if from_date < today:
            raise HTTPException(status_code=422, detail="pickup range must start on or after the current hotel-local date")
        live_horizon = (to_date - today).days + 1
        current = await build_forward_snapshot(conn, prop, today, live_horizon)

        if baseline_date:
            baseline_row = await conn.fetchrow(
                '''
                SELECT id,"snapshotDate","horizonDays","payloadJson"
                FROM owner_analytics_snapshots
                WHERE "propertyId"=$1 AND "snapshotDate"=$2 AND "snapshotDate"<$3
                ''',
                prop["id"],
                baseline_date,
                today,
            )
        else:
            baseline_row = await conn.fetchrow(
                '''
                SELECT id,"snapshotDate","horizonDays","payloadJson"
                FROM owner_analytics_snapshots
                WHERE "propertyId"=$1 AND "snapshotDate"<$2
                  AND ("snapshotDate" + "horizonDays")>$3::date
                ORDER BY "snapshotDate" DESC
                LIMIT 1
                ''',
                prop["id"],
                today,
                to_date,
            )

        snapshot_count = int(await conn.fetchval(
            'SELECT count(*) FROM owner_analytics_snapshots WHERE "propertyId"=$1', prop["id"]
        ) or 0)

    if not baseline_row:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "local_date": today,
            "snapshot_count": snapshot_count,
            "required": "At least one prior hotel-local-date snapshot covering the requested future dates.",
            "current": current["summary"],
            "days": [],
            "truth": "No pickup is invented before a historical snapshot exists.",
        }

    baseline = _payload(baseline_row["payloadJson"])
    current_by_day = {item["date"]: item for item in current["days"]}
    baseline_by_day = {item["date"]: item for item in baseline.get("days", [])}
    requested_dates = [from_date + timedelta(days=index) for index in range((to_date - from_date).days + 1)]

    days: list[dict[str, Any]] = []
    for day in requested_dates:
        key = day.isoformat()
        current_day = current_by_day.get(key)
        baseline_day = baseline_by_day.get(key)
        if not current_day or not baseline_day:
            continue
        days.append(
            {
                "date": key,
                "current_booked_rooms": current_day["booked_rooms"],
                "baseline_booked_rooms": baseline_day["booked_rooms"],
                "room_pickup": current_day["booked_rooms"] - baseline_day["booked_rooms"],
                "current_occupancy_percent": current_day["occupancy_on_books_percent"],
                "baseline_occupancy_percent": baseline_day["occupancy_on_books_percent"],
                "occupancy_pickup_points": round(current_day["occupancy_on_books_percent"] - baseline_day["occupancy_on_books_percent"], 1),
                "current_allocated_value_kgs": current_day["allocated_booked_value_kgs"],
                "baseline_allocated_value_kgs": baseline_day["allocated_booked_value_kgs"],
                "booked_value_pickup_kgs": current_day["allocated_booked_value_kgs"] - baseline_day["allocated_booked_value_kgs"],
            }
        )

    if not days:
        return {
            "status": "INSUFFICIENT_COVERAGE",
            "local_date": today,
            "baseline_date": baseline_row["snapshotDate"],
            "snapshot_count": snapshot_count,
            "days": [],
            "truth": "The selected baseline does not cover the requested future range; no extrapolation is performed.",
        }

    current_room_nights = sum(item["current_booked_rooms"] for item in days)
    baseline_room_nights = sum(item["baseline_booked_rooms"] for item in days)
    current_value = sum(item["current_allocated_value_kgs"] for item in days)
    baseline_value = sum(item["baseline_allocated_value_kgs"] for item in days)

    return {
        "status": "READY",
        "local_date": today,
        "range": {"from": from_date, "to": to_date, "coverage_days": len(days)},
        "baseline": {
            "snapshot_id": str(baseline_row["id"]),
            "snapshot_date": baseline_row["snapshotDate"],
            "age_days": (today - baseline_row["snapshotDate"]).days,
        },
        "snapshot_count": snapshot_count,
        "summary": {
            "current_booked_room_nights": current_room_nights,
            "baseline_booked_room_nights": baseline_room_nights,
            "room_night_pickup": current_room_nights - baseline_room_nights,
            "current_allocated_booked_value_kgs": current_value,
            "baseline_allocated_booked_value_kgs": baseline_value,
            "booked_value_pickup_kgs": current_value - baseline_value,
        },
        "days": days,
        "truth": "Pickup is the net change in on-books reservations/value since a stored snapshot. It includes additions and cancellations and is not a demand or revenue forecast.",
    }


@admin_router.get("/owner-brief")
async def owner_brief(
    request: Request,
    horizon_days: int = Query(default=30, ge=7, le=90),
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        prop = await property_context(conn, user["property_code"])
        pid = prop["id"]
        today = await conn.fetchval('SELECT (now() AT TIME ZONE $1)::date', prop["timezone"])
        forward = await build_forward_snapshot(conn, prop, today, horizon_days)
        near_end = today + timedelta(days=3)

        arrival_rows = await conn.fetch(
            '''
            WITH paid AS (
              SELECT "reservationId",COALESCE(SUM("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS paid_kgs
              FROM payments WHERE "reservationId" IS NOT NULL GROUP BY "reservationId"
            )
            SELECT r.id,r."bookingNumber",r."checkIn",r."checkOut",r."totalKgs",
                   COALESCE(p.paid_kgs,0)::bigint AS paid_kgs,
                   g."firstName",g."lastName",g.phone,
                   room.id AS room_id,room.code AS room_code,room."operationalState"::text AS room_state
            FROM reservations r
            LEFT JOIN paid p ON p."reservationId"=r.id
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            LEFT JOIN LATERAL (
              SELECT rm.id,rm.code,rm."operationalState"
              FROM inventory_blocks ib
              JOIN rooms rm ON rm.id=ib."roomId"
              WHERE ib."reservationId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
                AND ib."startDate"<=r."checkIn" AND ib."endDate">r."checkIn"
              ORDER BY ib."startDate",rm.code LIMIT 1
            ) room ON true
            WHERE r."propertyId"=$1 AND r.status='GUARANTEED'
              AND r."checkIn">=$2::date AND r."checkIn"<$3::date
            ORDER BY r."checkIn",room.code NULLS LAST,r."createdAt"
            ''',
            pid,
            today,
            near_end,
        )

        urgent_tasks = int(await conn.fetchval(
            '''SELECT count(*) FROM operational_tasks WHERE "propertyId"=$1
               AND priority='URGENT' AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')''',
            pid,
        ) or 0)
        needs_reply = int(await conn.fetchval(
            '''SELECT count(*) FROM conversations WHERE "propertyId"=$1
               AND "lastInboundAt" IS NOT NULL
               AND ("lastOutboundAt" IS NULL OR "lastInboundAt">"lastOutboundAt")
               AND status NOT IN ('RESOLVED','ARCHIVED')''',
            pid,
        ) or 0)
        duplicate_groups = int(await conn.fetchval(
            '''
            WITH identities AS (
              SELECT NULLIF(regexp_replace(COALESCE(phone,''),'\\D','','g'),'') AS phone_key,
                     NULLIF(lower(trim(COALESCE(email,''))),'') AS email_key
              FROM guests WHERE "propertyId"=$1
            ), groups AS (
              SELECT 'PHONE:'||phone_key AS k FROM identities WHERE phone_key IS NOT NULL GROUP BY phone_key HAVING count(*)>1
              UNION ALL
              SELECT 'EMAIL:'||email_key AS k FROM identities WHERE email_key IS NOT NULL GROUP BY email_key HAVING count(*)>1
            ) SELECT count(*) FROM groups
            ''',
            pid,
        ) or 0)
        segments = await conn.fetchrow(
            '''
            WITH guest_stats AS (
              SELECT g.id,
                     count(r.id) FILTER (WHERE r.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT'))::int AS reservations,
                     count(r.id) FILTER (WHERE r.status='CHECKED_OUT')::int AS completed,
                     bool_or(r.status='GUARANTEED' AND r."checkIn">=$2::date) AS has_future
              FROM guests g
              LEFT JOIN reservations r ON r."primaryGuestId"=g.id AND r."propertyId"=$1
              WHERE g."propertyId"=$1
              GROUP BY g.id
            )
            SELECT count(*) FILTER (WHERE reservations>=2)::int AS repeat_profiles,
                   count(*) FILTER (WHERE completed>0 AND NOT COALESCE(has_future,false))::int AS completed_without_future,
                   count(*) FILTER (WHERE reservations=0)::int AS no_reservations
            FROM guest_stats
            ''',
            pid,
            today,
        )
        upcoming_repeat = int(await conn.fetchval(
            '''
            SELECT count(*)
            FROM reservations r
            WHERE r."propertyId"=$1 AND r.status='GUARANTEED'
              AND r."checkIn">=$2::date AND r."checkIn"<$3::date
              AND EXISTS (
                SELECT 1 FROM reservations prior
                WHERE prior."propertyId"=r."propertyId" AND prior."primaryGuestId"=r."primaryGuestId"
                  AND prior.id<>r.id AND prior.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
              )
            ''',
            pid,
            today,
            today + timedelta(days=30),
        ) or 0)

        prior_snapshot = await conn.fetchrow(
            '''SELECT "snapshotDate" FROM owner_analytics_snapshots
               WHERE "propertyId"=$1 AND "snapshotDate"<$2 ORDER BY "snapshotDate" DESC LIMIT 1''',
            pid,
            today,
        )

    def guest_name(row) -> str:
        return " ".join(part for part in [row["firstName"], row["lastName"]] if part) or "Гость"

    unassigned = []
    debt = []
    not_ready_today = []
    for row in arrival_rows:
        item = {
            "reservation_id": str(row["id"]),
            "booking_number": row["bookingNumber"],
            "guest_name": guest_name(row),
            "phone": row["phone"],
            "check_in": row["checkIn"],
            "room_code": row["room_code"],
            "room_state": row["room_state"],
            "outstanding_kgs": max(int(row["totalKgs"])-int(row["paid_kgs"] or 0), 0),
        }
        if not row["room_id"]:
            unassigned.append(item)
        if item["outstanding_kgs"] > 0:
            debt.append(item)
        if row["checkIn"] == today and row["room_id"] and row["room_state"] != "CLEAN":
            not_ready_today.append(item)

    first7 = forward["days"][:7]
    first30 = forward["days"][: min(30, len(forward["days"]))]

    def period_summary(items):
        available = sum(item["available_rooms"] for item in items)
        booked = sum(item["booked_rooms"] for item in items)
        return {
            "days": len(items),
            "booked_room_nights": booked,
            "available_room_nights": available,
            "occupancy_on_books_percent": round(booked * 100 / available, 1) if available else 0.0,
            "allocated_booked_value_kgs": sum(item["allocated_booked_value_kgs"] for item in items),
            "arrivals": sum(item["arrivals"] for item in items),
            "departures": sum(item["departures"] for item in items),
        }

    actions = [
        {"code": "ARRIVAL_NOT_READY_TODAY", "severity": "CRITICAL", "count": len(not_ready_today), "label": "Заезды сегодня в неготовые номера"},
        {"code": "UNASSIGNED_72H", "severity": "HIGH", "count": len(unassigned), "label": "Заезды до 72 часов без назначенного номера"},
        {"code": "DEBT_72H", "severity": "HIGH", "count": len(debt), "label": "Заезды до 72 часов с остатком оплаты"},
        {"code": "URGENT_TASKS", "severity": "HIGH", "count": urgent_tasks, "label": "Срочные операционные задачи"},
        {"code": "MESSAGES_NEED_REPLY", "severity": "NORMAL", "count": needs_reply, "label": "Диалоги, где последнее сообщение от гостя"},
        {"code": "GUEST_DUPLICATES", "severity": "NORMAL", "count": duplicate_groups, "label": "Группы возможных дублей гостей"},
    ]

    return {
        "property": {"code": prop["code"], "name": prop["name"], "local_date": today, "timezone": prop["timezone"]},
        "forward": {"next_7_days": period_summary(first7), "next_30_days": period_summary(first30), "daily": forward["days"]},
        "actions": actions,
        "details": {
            "not_ready_arrivals_today": not_ready_today[:25],
            "unassigned_arrivals_72h": unassigned[:25],
            "debt_arrivals_72h": debt[:25],
        },
        "guest_segments": {
            "repeat_profiles": int(segments["repeat_profiles"] or 0),
            "upcoming_repeat_arrivals_30d": upcoming_repeat,
            "completed_without_future": int(segments["completed_without_future"] or 0),
            "profiles_without_reservations": int(segments["no_reservations"] or 0),
        },
        "pickup_readiness": {
            "prior_snapshot_available": bool(prior_snapshot),
            "latest_prior_snapshot_date": prior_snapshot["snapshotDate"] if prior_snapshot else None,
            "status": "READY" if prior_snapshot else "INSUFFICIENT_HISTORY",
        },
        "truth": {
            "forward": "Confirmed/on-books operational view only; no statistical demand forecast is implied.",
            "debt": "Outstanding is Reservation.totalKgs minus stored RECEIVED payments; manager payment terms remain human-controlled.",
            "segments": "Segments are factual reservation-history counts; no hidden VIP or propensity score is assigned.",
        },
    }
