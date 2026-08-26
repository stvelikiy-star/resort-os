import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/stays", tags=["stays"])
manager_access = require_roles("OWNER", "MANAGER")


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
                SELECT id,status::text AS status,"bookingNumber","checkIn","checkOut"
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
                    'actual_local_date',$8::text
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
            )
    return {
        "reservation_id": str(reservation_id),
        "status": "CHECKED_IN",
        "room_code": room["code"],
        "room_state": room["room_state"],
        "planned_check_in": reservation["checkIn"],
        "actual_local_date": local_today,
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
                SELECT id,status::text AS status,"bookingNumber","checkIn","checkOut","totalKgs"
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
            else:
                housekeeping_task_id = uuid.uuid4()
                await conn.execute(
                    '''
                    INSERT INTO operational_tasks (
                      id,"propertyId","roomId",type,status,priority,title,
                      description,"createdByType","createdById",source,"createdAt","updatedAt"
                    ) VALUES ($1,$2,$3,'HOUSEKEEPING','OPEN','HIGH',$4,$5,'SYSTEM',$6,'CHECK_OUT',now(),now())
                    ''',
                    housekeeping_task_id,
                    pid,
                    room["id"],
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
                    'housekeeping_task_id',$10::text
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
            )
    return {
        "reservation_id": str(reservation_id),
        "status": "CHECKED_OUT",
        "room_code": room["code"],
        "room_state": "DIRTY",
        "housekeeping_task_id": str(housekeeping_task_id) if housekeeping_task_id else None,
        "actual_check_out": local_today,
        "planned_check_out_before": original_check_out,
        "early_checkout_released_inventory": early_checkout_released_inventory,
        "stored_total_kgs_changed": False,
    }
