import json
import os
import uuid
from datetime import date, timedelta
from typing import Any

from asyncpg.exceptions import ExclusionViolationError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "DIRECT_2026_27")
router = APIRouter(prefix="/api/v1/admin/pms", tags=["admin-pms-chessboard"])
manager_access = require_roles("OWNER", "MANAGER")


class ScheduleSegment(BaseModel):
    room_id: uuid.UUID
    start: date
    end: date

    @model_validator(mode="after")
    def valid_dates(self):
        if self.end <= self.start:
            raise ValueError("segment end must be after start")
        return self


class SchedulePreviewPayload(BaseModel):
    segments: list[ScheduleSegment] = Field(min_length=1, max_length=32)


class ScheduleCommitPayload(SchedulePreviewPayload):
    expected_version: str = Field(min_length=10, max_length=80)


def _normalize_segments(items: list[ScheduleSegment]) -> list[ScheduleSegment]:
    ordered = sorted(items, key=lambda item: (item.start, item.end, str(item.room_id)))
    merged: list[ScheduleSegment] = []
    for item in ordered:
        if merged and merged[-1].room_id == item.room_id and merged[-1].end == item.start:
            merged[-1] = ScheduleSegment(room_id=item.room_id, start=merged[-1].start, end=item.end)
        else:
            merged.append(item)
    for index, item in enumerate(merged):
        if index and merged[index - 1].end != item.start:
            raise HTTPException(status_code=422, detail="Schedule segments must be contiguous without gaps or overlaps")
    return merged


def _schedule_json(items: list[ScheduleSegment], rooms: dict[uuid.UUID, Any]) -> list[dict[str, Any]]:
    return [
        {
            "room_id": str(item.room_id),
            "room_code": rooms[item.room_id]["code"],
            "room_type_code": rooms[item.room_id]["room_type_code"],
            "room_type_name": rooms[item.room_id]["room_type_name"],
            "start": item.start,
            "end": item.end,
        }
        for item in items
    ]


def _night_room(schedule: list[ScheduleSegment], night: date) -> uuid.UUID | None:
    for item in schedule:
        if item.start <= night < item.end:
            return item.room_id
    return None


def _nights(start: date, end: date) -> list[date]:
    return [start + timedelta(days=index) for index in range((end - start).days)]


async def _property(conn, property_code: str):
    row = await conn.fetchrow('SELECT id,timezone,currency FROM properties WHERE code=$1', property_code)
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


async def _reservation(conn, reservation_id: uuid.UUID, property_id: uuid.UUID, lock: bool = False):
    lock_sql = " FOR UPDATE" if lock else ""
    return await conn.fetchrow(
        f'''
        SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r."totalKgs",
               to_char(r."updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') AS version
        FROM reservations r
        WHERE r.id=$1 AND r."propertyId"=$2{lock_sql}
        ''',
        reservation_id,
        property_id,
    )


async def _current_blocks(conn, reservation_id: uuid.UUID, lock: bool = False):
    # Lock only inventory rows here. Room rows are locked separately in one
    # deterministic ORDER BY room.code,room.id to reduce cross-reservation deadlocks.
    suffix = " FOR UPDATE OF ib" if lock else ""
    return await conn.fetch(
        f'''
        SELECT ib.id,ib."roomId",ib."startDate",ib."endDate",room.code,
               rt.code AS room_type_code,rt.name AS room_type_name
        FROM inventory_blocks ib
        JOIN rooms room ON room.id=ib."roomId"
        JOIN room_types rt ON rt.id=room."roomTypeId"
        WHERE ib."reservationId"=$1 AND ib.active=true AND ib."blockType"='RESERVATION'
        ORDER BY ib."startDate",ib."endDate"{suffix}
        ''',
        reservation_id,
    )


async def _load_rooms(conn, property_id: uuid.UUID, room_ids: list[uuid.UUID], lock: bool = False):
    if not room_ids:
        return {}
    suffix = " FOR UPDATE OF room" if lock else ""
    rows = await conn.fetch(
        f'''
        SELECT room.id,room.code,room."operationalState"::text AS operational_state,room."roomTypeId",
               rt.code AS room_type_code,rt.name AS room_type_name
        FROM rooms room
        JOIN room_types rt ON rt.id=room."roomTypeId"
        WHERE room."propertyId"=$1 AND room.id=ANY($2::uuid[])
        ORDER BY room.code,room.id{suffix}
        ''',
        property_id,
        room_ids,
    )
    return {row["id"]: row for row in rows}


async def _segment_price(conn, room_type_id: uuid.UUID, start: date, end: date):
    nights = _nights(start, end)
    rows = await conn.fetch(
        '''
        SELECT rp."validFrom",rp."validTo",rp."priceKgs",rp."saleStatus"::text AS sale_status
        FROM rate_periods rp
        JOIN rate_plans plan ON plan.id=rp."ratePlanId"
        WHERE rp."roomTypeId"=$1 AND plan.code=$2
          AND rp."validFrom" <= $4 AND rp."validTo" >= $3
        ORDER BY rp."validFrom"
        ''',
        room_type_id,
        RATE_PLAN_CODE,
        start,
        end - timedelta(days=1),
    )
    total = 0
    for night in nights:
        matched = next((row for row in rows if row["validFrom"] <= night <= row["validTo"]), None)
        if not matched:
            return {"sellable": False, "reason": "RATE_MISSING", "total_kgs": None}
        if matched["sale_status"] != "OPEN" or matched["priceKgs"] <= 0:
            return {"sellable": False, "reason": "RATE_REQUIRES_CONFIRMATION", "total_kgs": None}
        total += matched["priceKgs"]
    return {"sellable": True, "reason": None, "total_kgs": total}


async def _pricing_preview(conn, schedule: list[ScheduleSegment], rooms: dict[uuid.UUID, Any]):
    total = 0
    for item in schedule:
        room = rooms[item.room_id]
        result = await _segment_price(conn, room["roomTypeId"], item.start, item.end)
        if not result["sellable"]:
            return {"sellable": False, "reason": result["reason"], "suggested_total_kgs": None}
        total += result["total_kgs"]
    return {"sellable": True, "reason": None, "suggested_total_kgs": total}


async def _conflicts(conn, reservation_id: uuid.UUID, schedule: list[ScheduleSegment]):
    found: list[dict[str, Any]] = []
    for item in schedule:
        rows = await conn.fetch(
            '''
            SELECT ib.id,ib."blockType"::text AS block_type,ib."startDate",ib."endDate",ib.reason,
                   res."bookingNumber",room.code AS room_code
            FROM inventory_blocks ib
            JOIN rooms room ON room.id=ib."roomId"
            LEFT JOIN reservations res ON res.id=ib."reservationId"
            WHERE ib."roomId"=$1 AND ib.active=true
              AND (ib."reservationId" IS NULL OR ib."reservationId"<>$2)
              AND daterange(ib."startDate",ib."endDate",'[)') && daterange($3::date,$4::date,'[)')
            ORDER BY ib."startDate"
            ''',
            item.room_id,
            reservation_id,
            item.start,
            item.end,
        )
        for row in rows:
            found.append(
                {
                    "inventory_block_id": str(row["id"]),
                    "room_code": row["room_code"],
                    "block_type": row["block_type"],
                    "start": row["startDate"].isoformat(),
                    "end": row["endDate"].isoformat(),
                    "booking_number": row["bookingNumber"],
                    "reason": row["reason"],
                }
            )
    return found


def _rows_to_schedule(rows) -> list[ScheduleSegment]:
    return [ScheduleSegment(room_id=row["roomId"], start=row["startDate"], end=row["endDate"]) for row in rows]


def _assert_current_schedule_consistent(reservation, current: list[ScheduleSegment]):
    if not current:
        raise HTTPException(status_code=409, detail="Reservation has no active room schedule")
    if current[0].start != reservation["checkIn"] or current[-1].end != reservation["checkOut"]:
        raise HTTPException(status_code=409, detail={"code": "CURRENT_SCHEDULE_RANGE_MISMATCH", "message": "Repair reservation schedule before moving it."})
    for index in range(1, len(current)):
        if current[index - 1].end != current[index].start:
            raise HTTPException(status_code=409, detail={"code": "CURRENT_SCHEDULE_NOT_CONTIGUOUS", "message": "Repair reservation schedule before moving it."})


def _validate_status_and_history(reservation, current: list[ScheduleSegment], proposed: list[ScheduleSegment], local_today: date):
    status = reservation["status"]
    if status not in {"GUARANTEED", "CHECKED_IN"}:
        raise HTTPException(status_code=409, detail=f"Reservation status {status} is read-only for chessboard mutation")

    if status == "CHECKED_IN":
        if proposed[0].start != reservation["checkIn"]:
            raise HTTPException(status_code=409, detail="CHECKED_IN reservation check-in history cannot be rewritten")
        if proposed[-1].end <= local_today:
            raise HTTPException(status_code=409, detail="CHECKED_IN reservation must retain a future checkout date")
        history_end = min(local_today, reservation["checkOut"])
        for night in _nights(reservation["checkIn"], history_end):
            if _night_room(current, night) != _night_room(proposed, night):
                raise HTTPException(status_code=409, detail={"code": "PAST_ROOM_HISTORY_IMMUTABLE", "date": night.isoformat()})


async def _build_preview(conn, reservation, current_rows, proposed: list[ScheduleSegment], rooms: dict[uuid.UUID, Any], local_today: date):
    current = _rows_to_schedule(current_rows)
    _assert_current_schedule_consistent(reservation, current)
    _validate_status_and_history(reservation, current, proposed, local_today)

    missing = [str(item.room_id) for item in proposed if item.room_id not in rooms]
    if missing:
        raise HTTPException(status_code=422, detail={"code": "ROOM_NOT_FOUND", "room_ids": missing})

    blocked = sorted({rooms[item.room_id]["code"] for item in proposed if rooms[item.room_id]["operational_state"] == "TECH_BLOCK"})
    if blocked:
        raise HTTPException(status_code=409, detail={"code": "TARGET_ROOM_TECH_BLOCK", "rooms": blocked})

    old_today_room = _night_room(current, local_today) if reservation["status"] == "CHECKED_IN" else None
    new_today_room = _night_room(proposed, local_today) if reservation["status"] == "CHECKED_IN" else None
    immediate_relocation = bool(old_today_room and new_today_room and old_today_room != new_today_room)
    if immediate_relocation and rooms[new_today_room]["operational_state"] != "CLEAN":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TARGET_ROOM_NOT_READY",
                "room_code": rooms[new_today_room]["code"],
                "room_state": rooms[new_today_room]["operational_state"],
            },
        )

    conflicts = await _conflicts(conn, reservation["id"], proposed)
    pricing = await _pricing_preview(conn, proposed, rooms)
    current_type_codes = sorted({row["room_type_code"] for row in current_rows})
    proposed_type_codes = sorted({rooms[item.room_id]["room_type_code"] for item in proposed})
    suggested = pricing["suggested_total_kgs"]

    return {
        "reservation": {
            "id": str(reservation["id"]),
            "booking_number": reservation["bookingNumber"],
            "status": reservation["status"],
            "stored_check_in": reservation["checkIn"],
            "stored_check_out": reservation["checkOut"],
            "stored_total_kgs": reservation["totalKgs"],
            "version": reservation["version"],
        },
        "current_schedule": [
            {
                "room_id": str(row["roomId"]),
                "room_code": row["code"],
                "room_type_code": row["room_type_code"],
                "room_type_name": row["room_type_name"],
                "start": row["startDate"],
                "end": row["endDate"],
            }
            for row in current_rows
        ],
        "proposed_schedule": _schedule_json(proposed, rooms),
        "proposed_check_in": proposed[0].start,
        "proposed_check_out": proposed[-1].end,
        "conflicts": conflicts,
        "can_commit": len(conflicts) == 0,
        "category_changed": current_type_codes != proposed_type_codes,
        "immediate_relocation": None if not immediate_relocation else {
            "effective_date": local_today,
            "from_room_id": str(old_today_room),
            "from_room_code": rooms[old_today_room]["code"],
            "to_room_id": str(new_today_room),
            "to_room_code": rooms[new_today_room]["code"],
            "vacated_room_will_become_dirty": True,
            "housekeeping_will_be_created": True,
        },
        "pricing": {
            **pricing,
            "stored_total_kgs": reservation["totalKgs"],
            "delta_kgs": suggested - reservation["totalKgs"] if suggested is not None else None,
            "stored_total_will_change_on_commit": False,
        },
        "history_rule": "Past room nights of CHECKED_IN reservations are immutable.",
    }


async def _mark_vacated_room_dirty(conn, property_id, room_id, room_code, booking_number, actor_id):
    await conn.execute('UPDATE rooms SET "operationalState"=\'DIRTY\',"updatedAt"=now() WHERE id=$1', room_id)
    existing = await conn.fetchval(
        '''
        SELECT id FROM operational_tasks
        WHERE "roomId"=$1 AND type='HOUSEKEEPING'
          AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
        ORDER BY "createdAt" DESC LIMIT 1
        ''',
        room_id,
    )
    if existing:
        return existing
    task_id = uuid.uuid4()
    await conn.execute(
        '''
        INSERT INTO operational_tasks (
          id,"propertyId","roomId",type,status,priority,title,description,
          "createdByType","createdById",source,"createdAt","updatedAt"
        ) VALUES ($1,$2,$3,'HOUSEKEEPING','OPEN','NORMAL',$4,$5,'SYSTEM',$6,'ROOM_RELOCATION',now(),now())
        ''',
        task_id,
        property_id,
        room_id,
        f"Уборка после переселения · {room_code}",
        f"Гость переселён из номера {room_code}; бронь {booking_number}",
        actor_id,
    )
    return task_id


async def _record_actual_relocation(
    conn,
    *,
    property_id: uuid.UUID,
    reservation_id: uuid.UUID,
    from_room_id: uuid.UUID,
    to_room_id: uuid.UUID,
    booking_number: str,
):
    """Advance factual stay placement only when a checked-in guest moves now."""
    stay = await conn.fetchrow(
        '''
        SELECT id,"guestId"
        FROM stays
        WHERE "propertyId"=$1 AND "reservationId"=$2 AND status='ACTIVE'
        FOR UPDATE
        ''',
        property_id,
        reservation_id,
    )
    if not stay:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACTIVE_STAY_REQUIRED_FOR_RELOCATION",
                "action": "REPAIR_OR_RECHECK_STAY_BEFORE_ROOM_MOVE",
            },
        )

    assignment = await conn.fetchrow(
        '''
        SELECT id,"roomId"
        FROM room_assignments
        WHERE "stayId"=$1 AND "endedAt" IS NULL
        FOR UPDATE
        ''',
        stay["id"],
    )
    if not assignment or assignment["roomId"] != from_room_id:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CURRENT_ROOM_ASSIGNMENT_MISMATCH",
                "expected_room_id": str(from_room_id),
                "actual_room_id": str(assignment["roomId"]) if assignment else None,
            },
        )

    target_assignment = await conn.fetchrow(
        '''
        SELECT id,"stayId"
        FROM room_assignments
        WHERE "roomId"=$1 AND "endedAt" IS NULL AND "stayId"<>$2
        FOR UPDATE
        ''',
        to_room_id,
        stay["id"],
    )
    if target_assignment:
        raise HTTPException(
            status_code=409,
            detail={"code": "TARGET_ROOM_HAS_ACTIVE_STAY_ASSIGNMENT"},
        )

    await conn.execute(
        'UPDATE room_assignments SET "endedAt"=now(),"updatedAt"=now() WHERE id=$1',
        assignment["id"],
    )
    new_assignment_id = uuid.uuid4()
    await conn.execute(
        '''
        INSERT INTO room_assignments (
          id,"propertyId","stayId","roomId","startedAt",source,"createdAt","updatedAt"
        ) VALUES ($1,$2,$3,$4,now(),'PMS_RELOCATION',now(),now())
        ''',
        new_assignment_id,
        property_id,
        stay["id"],
        to_room_id,
    )
    await conn.execute(
        '''
        INSERT INTO guest_history_events (
          id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
        ) VALUES ($1,$2,$3,$4,'ROOM_RELOCATION','PMS_CHESSBOARD',
          jsonb_build_object(
            'from_room_id',$5::text,
            'to_room_id',$6::text,
            'booking_number',$7::text
          ),now(),now())
        ''',
        uuid.uuid4(),
        property_id,
        stay["guestId"],
        stay["id"],
        str(from_room_id),
        str(to_room_id),
        booking_number,
    )
    return new_assignment_id


@router.post("/reservations/{reservation_id}/schedule/preview")
async def preview_schedule(reservation_id: uuid.UUID, payload: SchedulePreviewPayload, request: Request, user: dict[str, Any] = Depends(manager_access)):
    proposed = _normalize_segments(payload.segments)
    async with request.app.state.db.acquire() as conn:
        prop = await _property(conn, user["property_code"])
        reservation = await _reservation(conn, reservation_id, prop["id"])
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        current_rows = await _current_blocks(conn, reservation_id)
        current_room_ids = {row["roomId"] for row in current_rows}
        room_ids = sorted(current_room_ids | {item.room_id for item in proposed}, key=str)
        rooms = await _load_rooms(conn, prop["id"], room_ids)
        local_today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", prop["timezone"])
        return await _build_preview(conn, reservation, current_rows, proposed, rooms, local_today)


@router.post("/reservations/{reservation_id}/schedule/commit")
async def commit_schedule(reservation_id: uuid.UUID, payload: ScheduleCommitPayload, request: Request, user: dict[str, Any] = Depends(manager_access)):
    proposed = _normalize_segments(payload.segments)
    try:
        async with request.app.state.db.acquire() as conn:
            async with conn.transaction():
                prop = await _property(conn, user["property_code"])
                reservation = await _reservation(conn, reservation_id, prop["id"], lock=True)
                if not reservation:
                    raise HTTPException(status_code=404, detail="Reservation not found")
                if reservation["version"] != payload.expected_version:
                    raise HTTPException(status_code=409, detail={"code": "STALE_RESERVATION", "current_version": reservation["version"]})

                current_rows = await _current_blocks(conn, reservation_id, lock=True)
                all_room_ids = sorted({row["roomId"] for row in current_rows} | {item.room_id for item in proposed}, key=str)
                rooms = await _load_rooms(conn, prop["id"], all_room_ids, lock=True)
                if len(rooms) != len(all_room_ids):
                    raise HTTPException(status_code=422, detail="One or more rooms do not belong to this property")

                local_today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", prop["timezone"])
                preview = await _build_preview(conn, reservation, current_rows, proposed, rooms, local_today)
                if not preview["can_commit"]:
                    raise HTTPException(status_code=409, detail={"code": "ROOM_CONFLICT", "conflicts": preview["conflicts"]})

                before_schedule = preview["current_schedule"]
                await conn.execute(
                    '''UPDATE inventory_blocks SET active=false,"updatedAt"=now()
                       WHERE "reservationId"=$1 AND active=true AND "blockType"='RESERVATION' ''',
                    reservation_id,
                )
                for item in proposed:
                    await conn.execute(
                        '''
                        INSERT INTO inventory_blocks (
                          id,"roomId","reservationId","blockType","startDate","endDate",active,reason,"createdAt","updatedAt"
                        ) VALUES ($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())
                        ''',
                        uuid.uuid4(), item.room_id, reservation_id, item.start, item.end, reservation["bookingNumber"],
                    )

                await conn.execute(
                    'UPDATE reservations SET "checkIn"=$1,"checkOut"=$2,"updatedAt"=now() WHERE id=$3',
                    proposed[0].start,
                    proposed[-1].end,
                    reservation_id,
                )

                relocation_task_id = None
                relocation_assignment_id = None
                relocation = preview["immediate_relocation"]
                if relocation:
                    relocation_assignment_id = await _record_actual_relocation(
                        conn,
                        property_id=prop["id"],
                        reservation_id=reservation_id,
                        from_room_id=uuid.UUID(relocation["from_room_id"]),
                        to_room_id=uuid.UUID(relocation["to_room_id"]),
                        booking_number=reservation["bookingNumber"],
                    )
                    relocation_task_id = await _mark_vacated_room_dirty(
                        conn,
                        prop["id"],
                        uuid.UUID(relocation["from_room_id"]),
                        relocation["from_room_code"],
                        reservation["bookingNumber"],
                        user["id"],
                    )

                before_payload = {
                    "schedule": before_schedule,
                    "check_in": reservation["checkIn"].isoformat(),
                    "check_out": reservation["checkOut"].isoformat(),
                    "stored_total_kgs": reservation["totalKgs"],
                }
                after_payload = {
                    "schedule": preview["proposed_schedule"],
                    "check_in": proposed[0].start.isoformat(),
                    "check_out": proposed[-1].end.isoformat(),
                    "stored_total_kgs": reservation["totalKgs"],
                    "suggested_total_kgs": preview["pricing"]["suggested_total_kgs"],
                    "price_delta_kgs": preview["pricing"]["delta_kgs"],
                    "category_changed": preview["category_changed"],
                    "immediate_relocation": relocation,
                    "relocation_room_assignment_id": str(relocation_assignment_id) if relocation_assignment_id else None,
                    "relocation_housekeeping_task_id": str(relocation_task_id) if relocation_task_id else None,
                }
                await conn.execute(
                    '''
                    INSERT INTO audit_logs (
                      id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
                      "beforeJson","afterJson","createdAt"
                    ) VALUES ($1,$2,'STAFF',$3,'PMS_SCHEDULE_MUTATION','Reservation',$4,'PMS_CHESSBOARD','SUCCESS',
                      $5::jsonb,$6::jsonb,now())
                    ''',
                    uuid.uuid4(), prop["id"], user["id"], str(reservation_id),
                    json.dumps(before_payload, default=str), json.dumps(after_payload, default=str),
                )

                new_version = await conn.fetchval(
                    '''SELECT to_char("updatedAt", 'YYYY-MM-DD"T"HH24:MI:SS.US') FROM reservations WHERE id=$1''',
                    reservation_id,
                )
                return {
                    "ok": True,
                    "reservation_id": str(reservation_id),
                    "booking_number": reservation["bookingNumber"],
                    "version": new_version,
                    "schedule": preview["proposed_schedule"],
                    "check_in": proposed[0].start,
                    "check_out": proposed[-1].end,
                    "stored_total_kgs": reservation["totalKgs"],
                    "pricing_preview": preview["pricing"],
                    "immediate_relocation": relocation,
                    "relocation_room_assignment_id": str(relocation_assignment_id) if relocation_assignment_id else None,
                    "relocation_housekeeping_task_id": str(relocation_task_id) if relocation_task_id else None,
                    "message": "Schedule updated atomically; stored reservation total was not changed automatically.",
                }
    except ExclusionViolationError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ROOM_CONFLICT_RACE", "message": "Inventory changed before commit; original schedule was preserved."},
        ) from exc