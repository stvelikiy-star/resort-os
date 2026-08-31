import base64
import hashlib
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/stays", tags=["stays"])
manager_access = require_roles("OWNER", "MANAGER", "RECEPTION")

PIN_ITERATIONS = 200_000


def issue_guest_pin() -> tuple[str, str]:
    """Return the one-time visible PIN and a salted PBKDF2 representation for storage."""
    pin = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt,
        PIN_ITERATIONS,
    )
    stored = "$".join(
        [
            "pbkdf2_sha256",
            str(PIN_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ]
    )
    return pin, stored


async def property_context(conn, property_code: str):
    row = await conn.fetchrow(
        'SELECT id,timezone FROM properties WHERE code=$1', property_code
    )
    if not row:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return row


async def room_for_local_date(conn, reservation_id: uuid.UUID, local_date):
    return await conn.fetchrow(
        '''
        SELECT room.id,room.code,room."operationalState"::text AS room_state,
               ib."startDate",ib."endDate"
        FROM inventory_blocks ib
        JOIN rooms room ON room.id=ib."roomId"
        WHERE ib."reservationId"=$1
          AND ib."blockType"='RESERVATION'
          AND ib.active=true
        ORDER BY
          CASE
            WHEN ib."startDate" <= $2::date AND $2::date < ib."endDate" THEN 0
            WHEN ib."endDate" = $2::date THEN 1
            ELSE 2
          END,
          ib."endDate" DESC,
          ib."startDate" DESC
        LIMIT 1
        FOR UPDATE OF room,ib
        ''',
        reservation_id,
        local_date,
    )


async def activate_stay(
    conn,
    *,
    property_id: uuid.UUID,
    reservation,
    room_id: uuid.UUID,
):
    if not reservation["primaryGuestId"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHECK_IN_GUEST_REQUIRED",
                "action": "ATTACH_PRIMARY_GUEST_FIRST",
            },
        )

    guest_pin, guest_pin_hash = issue_guest_pin()
    stay = await conn.fetchrow(
        '''
        INSERT INTO stays (
          id,"propertyId","reservationId","guestId",status,"actualCheckInAt",
          "guestAccessPinHash","guestAccessPinIssuedAt","guestAccessPinExpiresAt",
          "createdAt","updatedAt"
        ) VALUES ($1,$2,$3,$4,'ACTIVE',now(),$5,now(),now() + interval '24 hours',now(),now())
        ON CONFLICT ("reservationId") DO UPDATE SET
          "guestId"=EXCLUDED."guestId",
          status='ACTIVE',
          "actualCheckInAt"=COALESCE(stays."actualCheckInAt",now()),
          "actualCheckOutAt"=NULL,
          "guestAccessPinHash"=EXCLUDED."guestAccessPinHash",
          "guestAccessPinIssuedAt"=now(),
          "guestAccessPinExpiresAt"=now() + interval '24 hours',
          "updatedAt"=now()
        RETURNING id
        ''',
        uuid.uuid4(),
        property_id,
        reservation["id"],
        reservation["primaryGuestId"],
        guest_pin_hash,
    )

    active_assignment = await conn.fetchrow(
        '''
        SELECT id,"roomId"
        FROM room_assignments
        WHERE "stayId"=$1 AND "endedAt" IS NULL
        FOR UPDATE
        ''',
        stay["id"],
    )
    if active_assignment and active_assignment["roomId"] != room_id:
        await conn.execute(
            'UPDATE room_assignments SET "endedAt"=now(),"updatedAt"=now() WHERE id=$1',
            active_assignment["id"],
        )
        active_assignment = None

    if active_assignment:
        assignment_id = active_assignment["id"]
    else:
        assignment_id = uuid.uuid4()
        await conn.execute(
            '''
            INSERT INTO room_assignments (
              id,"propertyId","stayId","roomId","startedAt",source,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,$4,now(),'CHECK_IN',now(),now())
            ''',
            assignment_id,
            property_id,
            stay["id"],
            room_id,
        )

    await conn.execute(
        '''
        INSERT INTO guest_history_events (
          id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
        ) VALUES ($1,$2,$3,$4,'CHECK_IN','PMS',
          jsonb_build_object('room_id',$5::text,'booking_number',$6::text),now(),now())
        ''',
        uuid.uuid4(),
        property_id,
        reservation["primaryGuestId"],
        stay["id"],
        str(room_id),
        reservation["bookingNumber"],
    )
    return stay["id"], assignment_id, guest_pin


async def close_stay(conn, *, property_id: uuid.UUID, reservation, room_id: uuid.UUID):
    stay = await conn.fetchrow(
        '''
        SELECT id,"guestId",status::text AS status
        FROM stays
        WHERE "reservationId"=$1 AND "propertyId"=$2
        FOR UPDATE
        ''',
        reservation["id"],
        property_id,
    )
    if not stay:
        return None, 0

    await conn.execute(
        '''
        UPDATE room_assignments
        SET "endedAt"=COALESCE("endedAt",now()),"updatedAt"=now()
        WHERE "stayId"=$1 AND "endedAt" IS NULL
        ''',
        stay["id"],
    )
    revoked_sessions = await conn.fetchval(
        '''
        WITH revoked AS (
          UPDATE guest_sessions
          SET status='REVOKED',"revokedAt"=COALESCE("revokedAt",now()),"updatedAt"=now()
          WHERE "stayId"=$1 AND status='ACTIVE'
          RETURNING id
        )
        SELECT count(*)::int FROM revoked
        ''',
        stay["id"],
    )
    await conn.execute(
        '''
        UPDATE stays
        SET status='CHECKED_OUT',"actualCheckOutAt"=now(),
            "guestAccessPinHash"=NULL,"guestAccessPinIssuedAt"=NULL,
            "guestAccessPinExpiresAt"=NULL,"updatedAt"=now()
        WHERE id=$1
        ''',
        stay["id"],
    )
    await conn.execute(
        '''
        INSERT INTO guest_history_events (
          id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
        ) VALUES ($1,$2,$3,$4,'CHECK_OUT','PMS',
          jsonb_build_object('room_id',$5::text,'booking_number',$6::text),now(),now())
        ''',
        uuid.uuid4(),
        property_id,
        stay["guestId"],
        stay["id"],
        str(room_id),
        reservation["bookingNumber"],
    )
    return stay["id"], revoked_sessions or 0


async def trim_schedule_for_early_checkout(
    conn,
    reservation,
    local_today,
):
    """Release nights after an early checkout without changing commercial total."""
    if local_today >= reservation["checkOut"]:
        return False
    if local_today <= reservation["checkIn"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHECK_OUT_WOULD_CREATE_ZERO_NIGHT_STAY",
                "planned_check_in": str(reservation["checkIn"]),
                "actual_local_date": str(local_today),
            },
        )

    rows = await conn.fetch(
        '''
        SELECT id,"roomId","startDate","endDate"
        FROM inventory_blocks
        WHERE "reservationId"=$1
          AND "blockType"='RESERVATION'
          AND active=true
        ORDER BY "startDate","endDate"
        FOR UPDATE
        ''',
        reservation["id"],
    )
    if not rows:
        raise HTTPException(status_code=409, detail="Reservation has no active room schedule")

    retained: list[tuple[Any, Any, Any]] = []
    for row in rows:
        if row["endDate"] <= local_today:
            retained.append((row["roomId"], row["startDate"], row["endDate"]))
            continue
        if row["startDate"] < local_today < row["endDate"]:
            retained.append((row["roomId"], row["startDate"], local_today))
        break

    if not retained or retained[-1][2] != local_today:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CHECK_OUT_DATE_NOT_IN_SCHEDULE",
                "actual_local_date": str(local_today),
            },
        )

    await conn.execute(
        '''
        UPDATE inventory_blocks
        SET active=false,"updatedAt"=now()
        WHERE "reservationId"=$1 AND "blockType"='RESERVATION' AND active=true
        ''',
        reservation["id"],
    )
    for room_id, start_date, end_date in retained:
        await conn.execute(
            '''
            INSERT INTO inventory_blocks (
              id,"roomId","reservationId","blockType","startDate","endDate",
              active,reason,"createdAt","updatedAt"
            ) VALUES ($1,$2,$3,'RESERVATION',$4,$5,true,$6,now(),now())
            ''',
            uuid.uuid4(),
            room_id,
            reservation["id"],
            start_date,
            end_date,
            reservation["bookingNumber"],
        )

    await conn.execute(
        'UPDATE reservations SET "checkOut"=$1,"updatedAt"=now() WHERE id=$2',
        local_today,
        reservation["id"],
    )
    return True


@router.post("/reservations/{reservation_id}/check-in")
async def check_in(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            pid = prop["id"]
            local_today = await conn.fetchval(
                "SELECT (now() AT TIME ZONE $1)::date", prop["timezone"]
            )
            reservation = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,"bookingNumber","checkIn","checkOut","primaryGuestId"
                FROM reservations
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                reservation_id,
                pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] != "GUARANTEED":
                raise HTTPException(status_code=409, detail="Only guaranteed reservation can check in")
            if not (reservation["checkIn"] <= local_today < reservation["checkOut"]):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "CHECK_IN_DATE_OUTSIDE_SCHEDULE",
                        "planned_check_in": str(reservation["checkIn"]),
                        "planned_check_out": str(reservation["checkOut"]),
                        "actual_local_date": str(local_today),
                        "action": "ADJUST_DATES_IN_CHESSBOARD_FIRST",
                    },
                )

            room = await room_for_local_date(conn, reservation_id, local_today)
            if not room or not (room["startDate"] <= local_today < room["endDate"]):
                raise HTTPException(status_code=409, detail="Reservation has no room assignment for actual check-in date")
            if room["room_state"] != "CLEAN":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "CHECK_IN_ROOM_NOT_READY",
                        "room_code": room["code"],
                        "room_state": room["room_state"],
                    },
                )

            stay_id, room_assignment_id, guest_access_pin = await activate_stay(
                conn,
                property_id=pid,
                reservation=reservation,
                room_id=room["id"],
            )
            await conn.execute(
                '''UPDATE reservations SET status='CHECKED_IN', "updatedAt"=now() WHERE id=$1''',
                reservation_id,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",
                  source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'CHECK_IN','Reservation',$4,'PMS','SUCCESS',
                  jsonb_build_object(
                    'room_code',$5::text,
                    'room_state',$6::text,
                    'planned_check_in',$7::text,
                    'actual_local_date',$8::text,
                    'stay_id',$9::text,
                    'room_assignment_id',$10::text,
                    'guest_pin_issued',true
                  ),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(reservation_id),
                room["code"],
                room["room_state"],
                str(reservation["checkIn"]),
                str(local_today),
                str(stay_id),
                str(room_assignment_id),
            )
    return {
        "reservation_id": str(reservation_id),
        "stay_id": str(stay_id),
        "status": "CHECKED_IN",
        "room_code": room["code"],
        "room_state": room["room_state"],
        "planned_check_in": reservation["checkIn"],
        "actual_local_date": local_today,
        "guest_access_pin": guest_access_pin,
        "guest_access_pin_valid_for_hours": 24,
        "guest_access_pin_display_once": True,
    }


@router.post("/reservations/{reservation_id}/check-out")
async def check_out(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await property_context(conn, user["property_code"])
            pid = prop["id"]
            local_today = await conn.fetchval(
                "SELECT (now() AT TIME ZONE $1)::date", prop["timezone"]
            )
            reservation = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,"bookingNumber","checkIn","checkOut","totalKgs","primaryGuestId"
                FROM reservations
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                reservation_id,
                pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] != "CHECKED_IN":
                raise HTTPException(status_code=409, detail="Only checked-in reservation can check out")
            if local_today > reservation["checkOut"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "CHECK_OUT_AFTER_SCHEDULE",
                        "planned_check_out": str(reservation["checkOut"]),
                        "actual_local_date": str(local_today),
                        "action": "EXTEND_DATES_IN_CHESSBOARD_FIRST",
                    },
                )

            room = await room_for_local_date(conn, reservation_id, local_today)
            if not room:
                raise HTTPException(status_code=409, detail="Reservation has no room assignment for checkout")

            original_check_out = reservation["checkOut"]
            early_checkout_released_inventory = await trim_schedule_for_early_checkout(
                conn,
                reservation,
                local_today,
            )

            stay_id, revoked_guest_sessions = await close_stay(
                conn,
                property_id=pid,
                reservation=reservation,
                room_id=room["id"],
            )

            await conn.execute(
                '''UPDATE reservations SET status='CHECKED_OUT', "updatedAt"=now() WHERE id=$1''',
                reservation_id,
            )

            await conn.execute(
                '''UPDATE rooms SET "operationalState"='DIRTY', "updatedAt"=now() WHERE id=$1''',
                room["id"],
            )
            existing_task = await conn.fetchval(
                '''
                SELECT id FROM operational_tasks
                WHERE "roomId"=$1 AND type='HOUSEKEEPING'
                  AND status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
                LIMIT 1
                ''',
                room["id"],
            )
            if existing_task:
                housekeeping_task_id = existing_task
                await conn.execute(
                    '''
                    UPDATE operational_tasks
                    SET "reservationId"=COALESCE("reservationId",$2),
                        "stayId"=COALESCE("stayId",$3),"updatedAt"=now()
                    WHERE id=$1
                    ''',
                    housekeeping_task_id,
                    reservation_id,
                    stay_id,
                )
            else:
                housekeeping_task_id = uuid.uuid4()
                await conn.execute(
                    '''
                    INSERT INTO operational_tasks (
                      id,"propertyId","roomId","reservationId","stayId",type,status,priority,title,
                      description,"createdByType","createdById",source,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,$4,$5,'HOUSEKEEPING','OPEN','HIGH',$6,$7,'SYSTEM',$8,'CHECK_OUT',now(),now())
                    ''',
                    housekeeping_task_id,
                    pid,
                    room["id"],
                    reservation_id,
                    stay_id,
                    f"Уборка после выезда · {room['code']}",
                    f"Автоматически создано после выезда {reservation['bookingNumber']}",
                    user["id"],
                )

            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'CHECK_OUT','Reservation',$4,'PMS','SUCCESS',
                  jsonb_build_object(
                    'status','CHECKED_IN',
                    'planned_check_out',$5::text,
                    'stored_total_kgs',$6::int
                  ),
                  jsonb_build_object(
                    'status','CHECKED_OUT',
                    'room_code',$7::text,
                    'actual_local_date',$8::text,
                    'early_checkout_released_inventory',$9::boolean,
                    'stored_total_kgs',$6::int,
                    'housekeeping_task_id',$10::text,
                    'stay_id',$11::text,
                    'revoked_guest_sessions',$12::int
                  ),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(reservation_id),
                str(original_check_out),
                reservation["totalKgs"],
                room["code"],
                str(local_today),
                early_checkout_released_inventory,
                str(housekeeping_task_id) if housekeeping_task_id else None,
                str(stay_id) if stay_id else None,
                revoked_guest_sessions,
            )
    return {
        "reservation_id": str(reservation_id),
        "stay_id": str(stay_id) if stay_id else None,
        "status": "CHECKED_OUT",
        "room_code": room["code"],
        "room_state": "DIRTY",
        "housekeeping_task_id": str(housekeeping_task_id) if housekeeping_task_id else None,
        "revoked_guest_sessions": revoked_guest_sessions,
        "actual_check_out": local_today,
        "planned_check_out_before": original_check_out,
        "early_checkout_released_inventory": early_checkout_released_inventory,
        "stored_total_kgs_changed": False,
    }