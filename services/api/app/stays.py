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


async def first_room_for_reservation(conn, reservation_id: uuid.UUID):
    return await conn.fetchrow(
        '''
        SELECT room.id,room.code,room."operationalState"::text AS room_state,
               ib."startDate",ib."endDate"
        FROM inventory_blocks ib
        JOIN rooms room ON room.id=ib."roomId"
        WHERE ib."reservationId"=$1
          AND ib."blockType"='RESERVATION'
          AND ib.active=true
        ORDER BY ib."startDate" ASC,ib."endDate" ASC
        LIMIT 1
        FOR UPDATE OF room,ib
        ''',
        reservation_id,
    )


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

            # Check-in always starts in the first active schedule segment. We do not
            # enforce arrival-date policy here because early/late arrival rules are
            # not approved; we only enforce physical room readiness.
            room = await first_room_for_reservation(conn, reservation_id)
            if not room:
                raise HTTPException(status_code=409, detail="Reservation has no room assignment for check-in")
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
            if reservation["status"] != "CHECKED_IN":
                raise HTTPException(status_code=409, detail="Only checked-in reservation can check out")

            # Multi-room stays are represented as contiguous InventoryBlock segments.
            # Select the segment occupied today; on the planned checkout date choose
            # the segment ending today. This avoids cleaning an earlier room after relocation.
            room = await room_for_local_date(conn, reservation_id, local_today)

            # Historical NFC code remains unchanged/deferred. It is not an active V1 dependency.
            nfc_wallet = await conn.fetchrow(
                '''SELECT id,"balanceKgs",status::text AS status FROM nfc_wallets
                   WHERE "reservationId"=$1 AND "propertyId"=$2 FOR UPDATE''',
                reservation_id, pid,
            )
            nfc_frozen = False
            nfc_balance_kgs = None
            if nfc_wallet:
                nfc_balance_kgs = nfc_wallet["balanceKgs"]
                if nfc_wallet["status"] == "ACTIVE":
                    await conn.execute(
                        '''UPDATE nfc_wallets SET status='BLOCKED',"updatedAt"=now() WHERE id=$1''',
                        nfc_wallet["id"],
                    )
                    await conn.execute(
                        '''UPDATE nfc_bracelets SET status='BLOCKED',"updatedAt"=now()
                           WHERE "walletId"=$1 AND status='ACTIVE'::"NfcBraceletStatus"''',
                        nfc_wallet["id"],
                    )
                    nfc_frozen = True
                    await conn.execute(
                        '''
                        INSERT INTO audit_logs (
                          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                        ) VALUES ($1,$2,'STAFF',$3,'FREEZE_NFC_ON_CHECK_OUT','NfcWallet',$4,'PMS','SUCCESS',
                          jsonb_build_object('status','BLOCKED','balance_kgs',$5::int,'reason','CHECK_OUT'),now())
                        ''',
                        uuid.uuid4(), pid, user["id"], str(nfc_wallet["id"]), nfc_balance_kgs,
                    )

            await conn.execute(
                '''UPDATE reservations SET status='CHECKED_OUT', "updatedAt"=now() WHERE id=$1''',
                reservation_id,
            )

            housekeeping_task_id = None
            if room:
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
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'CHECK_OUT','Reservation',$4,'PMS','SUCCESS',
                  jsonb_build_object(
                    'room_code',$5::text,
                    'local_date',$6::text,
                    'housekeeping_task_id',$7::text,
                    'nfc_frozen',$8::boolean,
                    'nfc_balance_kgs',$9::int
                  ),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(reservation_id),
                room["code"] if room else None,
                str(local_today),
                str(housekeeping_task_id) if housekeeping_task_id else None,
                nfc_frozen,
                nfc_balance_kgs,
            )
    return {
        "reservation_id": str(reservation_id),
        "status": "CHECKED_OUT",
        "room_code": room["code"] if room else None,
        "room_state": "DIRTY" if room else None,
        "housekeeping_task_id": str(housekeeping_task_id) if housekeeping_task_id else None,
        "nfc_frozen": nfc_frozen,
        "nfc_balance_kgs": nfc_balance_kgs,
    }
