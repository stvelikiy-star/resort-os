import json
import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/dining", tags=["dining-seating"])
read_access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")
write_access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")


class SeatingCreate(BaseModel):
    stay_id: uuid.UUID
    table_id: uuid.UUID
    service_date: date
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "OTHER"] | None = None
    waiter_id: uuid.UUID | None = None
    status: Literal["WAITING", "SEATED"] = "WAITING"
    notes: str | None = Field(default=None, max_length=1000)


class SeatingStatusPatch(BaseModel):
    status: Literal["WAITING", "SEATED", "RELEASED", "CANCELLED"]


class SeatingMove(BaseModel):
    target_table_id: uuid.UUID
    waiter_mode: Literal["KEEP", "CLEAR", "ASSIGN"] = "KEEP"
    waiter_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, resource_id: str, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'DiningTableSession',$5,'DINING_FLOOR','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, resource_id,
        json.dumps({**payload, "financial_effect": "NONE"}, ensure_ascii=False, default=str),
    )


async def validate_waiter(conn, pid: uuid.UUID, user: dict[str, Any], waiter_id: uuid.UUID | None) -> uuid.UUID | None:
    current_id = uuid.UUID(user["id"])
    if user["role"] == "DINING_STAFF":
        if waiter_id is None:
            return current_id
        if waiter_id != current_id:
            raise HTTPException(status_code=403, detail="Dining staff may assign only themselves")
    if waiter_id is None:
        return None
    waiter = await conn.fetchrow(
        '''SELECT id,role::text AS role FROM staff_users
           WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true''', waiter_id, pid,
    )
    if not waiter or waiter["role"] != "DINING_STAFF":
        raise HTTPException(status_code=422, detail={"code": "DINING_WAITER_INVALID"})
    return waiter_id


def session_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "stay_id": str(row["stayId"]),
        "reservation_id": str(row["reservationId"]),
        "table_id": str(row["tableId"]),
        "table_code": row["table_code"],
        "table_name": row["table_name"],
        "zone_label": row["zoneLabel"],
        "waiter_id": str(row["waiterId"]) if row["waiterId"] else None,
        "waiter_name": row["waiter_name"],
        "service_date": row["serviceDate"],
        "meal_type": row["mealType"],
        "status": row["status"],
        "party_size": row["partySize"],
        "adults": row["adults"],
        "children": row["children"],
        "guest_name": row["guest_name"],
        "room_code": row["room_code"],
        "booking_number": row["bookingNumber"],
        "notes": row["notes"],
        "seated_at": row["seatedAt"],
        "released_at": row["releasedAt"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
    }


SESSION_SELECT = '''
SELECT ds.id,ds."stayId",ds."reservationId",ds."tableId",ds."waiterId",ds."serviceDate",ds."mealType",
       ds.status,ds."partySize",ds.adults,ds.children,ds.notes,ds."seatedAt",ds."releasedAt",ds."createdAt",ds."updatedAt",
       kt.code AS table_code,kt.name AS table_name,kt."zoneLabel",u."displayName" AS waiter_name,
       r."bookingNumber",trim(concat_ws(' ',g."firstName",g."lastName")) AS guest_name,room.code AS room_code
FROM dining_table_sessions ds
JOIN kitchen_tables kt ON kt.id=ds."tableId"
JOIN reservations r ON r.id=ds."reservationId"
JOIN stays s ON s.id=ds."stayId"
JOIN guests g ON g.id=s."guestId"
LEFT JOIN staff_users u ON u.id=ds."waiterId"
LEFT JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
LEFT JOIN rooms room ON room.id=ra."roomId"
'''


@router.get("/sessions")
async def list_sessions(
    request: Request,
    service_date: date | None = Query(default=None),
    status_filter: str = Query(default="ACTIVE", alias="status"),
    mine: bool = Query(default=False),
    user: dict[str, Any] = Depends(read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        day = service_date or await conn.fetchval(
            '''SELECT (now() AT TIME ZONE COALESCE(timezone,'Asia/Bishkek'))::date FROM properties WHERE id=$1''', pid,
        )
        where = ['ds."propertyId"=$1', 'ds."serviceDate"=$2']
        args: list[Any] = [pid, day]
        if status_filter == "ACTIVE":
            where.append("ds.status IN ('WAITING','SEATED')")
        elif status_filter != "ALL":
            if status_filter not in {"WAITING", "SEATED", "RELEASED", "CANCELLED"}:
                raise HTTPException(status_code=422, detail="Unknown seating status")
            args.append(status_filter)
            where.append(f"ds.status=${len(args)}")
        if mine:
            args.append(uuid.UUID(user["id"]))
            where.append(f'ds."waiterId"=${len(args)}')
        rows = await conn.fetch(
            SESSION_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY CASE ds.status WHEN 'SEATED' THEN 0 ELSE 1 END, kt.code",
            *args,
        )
    return {"service_date": day, "items": [session_item(row) for row in rows]}


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SeatingCreate,
    request: Request,
    user: dict[str, Any] = Depends(write_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'dining-seat:{payload.stay_id}:{payload.table_id}')
            stay = await conn.fetchrow(
                '''SELECT s.id,s."reservationId",s.status::text AS stay_status,r.adults,r.children,r."checkIn",r."checkOut"
                   FROM stays s JOIN reservations r ON r.id=s."reservationId"
                   WHERE s.id=$1 AND s."propertyId"=$2 FOR UPDATE''', payload.stay_id, pid,
            )
            if not stay or stay["stay_status"] not in {"PENDING", "ACTIVE"}:
                raise HTTPException(status_code=409, detail={"code": "DINING_STAY_NOT_ACTIVE"})
            if payload.service_date < stay["checkIn"] or payload.service_date > stay["checkOut"]:
                raise HTTPException(status_code=422, detail={"code": "DINING_SEATING_OUTSIDE_STAY"})
            table = await conn.fetchrow(
                '''SELECT id,code,name,seats,"isActive",status FROM kitchen_tables
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', payload.table_id, pid,
            )
            if not table or not table["isActive"] or table["status"] == "OUT_OF_SERVICE":
                raise HTTPException(status_code=404, detail="Active dining table not found")
            party_size = int(stay["adults"]) + int(stay["children"])
            if party_size > int(table["seats"]):
                raise HTTPException(status_code=409, detail={"code": "DINING_TABLE_TOO_SMALL", "seats": table["seats"], "party_size": party_size})
            waiter_id = await validate_waiter(conn, pid, user, payload.waiter_id)
            conflict = await conn.fetchrow(
                '''SELECT id,"stayId" FROM dining_table_sessions
                   WHERE "tableId"=$1 AND status='SEATED' LIMIT 1 FOR UPDATE''', payload.table_id,
            )
            if conflict and payload.status == "SEATED":
                raise HTTPException(status_code=409, detail={"code": "DINING_TABLE_OCCUPIED", "session_id": str(conflict["id"])})
            existing = await conn.fetchrow(
                '''SELECT id,"tableId",status FROM dining_table_sessions
                   WHERE "stayId"=$1 AND status IN ('WAITING','SEATED') LIMIT 1 FOR UPDATE''', payload.stay_id,
            )
            if existing:
                raise HTTPException(status_code=409, detail={"code": "DINING_GUEST_ALREADY_ASSIGNED", "session_id": str(existing["id"])})

            session_id = uuid.uuid4()
            seated_at_sql = 'now()' if payload.status == "SEATED" else 'NULL'
            await conn.execute(
                f'''INSERT INTO dining_table_sessions (
                     id,"propertyId","stayId","reservationId","tableId","waiterId","serviceDate","mealType",status,
                     "partySize",adults,children,notes,source,"seatedAt","createdById","createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,'DINING_FLOOR',{seated_at_sql},$14,now(),now())''',
                session_id, pid, payload.stay_id, stay["reservationId"], payload.table_id, waiter_id,
                payload.service_date, payload.meal_type, payload.status, party_size, stay["adults"], stay["children"],
                payload.notes, uuid.UUID(user["id"]),
            )
            await conn.execute(
                '''UPDATE kitchen_tables SET status=$3,"updatedAt"=now() WHERE id=$1 AND "propertyId"=$2''',
                payload.table_id, pid, "OCCUPIED" if payload.status == "SEATED" else "RESERVED",
            )
            await audit(conn, pid, user, "CREATE_DINING_TABLE_SESSION", str(session_id), {
                "stay_id": str(payload.stay_id), "table_id": str(payload.table_id), "status": payload.status,
                "waiter_id": str(waiter_id) if waiter_id else None, "meal_type": payload.meal_type,
            })
            row = await conn.fetchrow(SESSION_SELECT + ' WHERE ds.id=$1', session_id)
    return session_item(row)


@router.patch("/sessions/{session_id}/status")
async def patch_session_status(
    session_id: uuid.UUID,
    payload: SeatingStatusPatch,
    request: Request,
    user: dict[str, Any] = Depends(write_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''SELECT id,"tableId","waiterId",status FROM dining_table_sessions
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', session_id, pid,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Dining table session not found")
            if user["role"] == "DINING_STAFF" and row["waiterId"] not in {None, uuid.UUID(user["id"])}:
                raise HTTPException(status_code=403, detail="This table belongs to another waiter")
            if row["status"] in {"RELEASED", "CANCELLED"}:
                raise HTTPException(status_code=409, detail={"code": "DINING_SESSION_CLOSED", "status": row["status"]})
            if payload.status == "SEATED":
                conflict = await conn.fetchrow(
                    '''SELECT id FROM dining_table_sessions WHERE "tableId"=$1 AND status='SEATED' AND id<>$2 LIMIT 1 FOR UPDATE''',
                    row["tableId"], session_id,
                )
                if conflict:
                    raise HTTPException(status_code=409, detail={"code": "DINING_TABLE_OCCUPIED", "session_id": str(conflict["id"])})
            await conn.execute(
                '''UPDATE dining_table_sessions SET status=$2,
                     "seatedAt"=CASE WHEN $2='SEATED' AND "seatedAt" IS NULL THEN now() ELSE "seatedAt" END,
                     "releasedAt"=CASE WHEN $2 IN ('RELEASED','CANCELLED') THEN now() ELSE "releasedAt" END,
                     "updatedAt"=now() WHERE id=$1''', session_id, payload.status,
            )
            table_status = "OCCUPIED" if payload.status == "SEATED" else "RESERVED" if payload.status == "WAITING" else "CLEANING"
            await conn.execute('UPDATE kitchen_tables SET status=$2,"updatedAt"=now() WHERE id=$1', row["tableId"], table_status)
            await audit(conn, pid, user, "PATCH_DINING_TABLE_SESSION", str(session_id), {"from_status": row["status"], "status": payload.status})
            result = await conn.fetchrow(SESSION_SELECT + ' WHERE ds.id=$1', session_id)
    return session_item(result)


@router.post("/sessions/{session_id}/move")
async def move_session(
    session_id: uuid.UUID,
    payload: SeatingMove,
    request: Request,
    user: dict[str, Any] = Depends(write_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            session = await conn.fetchrow(
                '''SELECT id,"tableId","stayId","waiterId",status,"partySize" FROM dining_table_sessions
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', session_id, pid,
            )
            if not session:
                raise HTTPException(status_code=404, detail="Dining table session not found")
            if session["status"] not in {"WAITING", "SEATED"}:
                raise HTTPException(status_code=409, detail={"code": "DINING_SESSION_NOT_MOVABLE", "status": session["status"]})
            if user["role"] == "DINING_STAFF" and session["waiterId"] not in {None, uuid.UUID(user["id"])}:
                raise HTTPException(status_code=403, detail="This table belongs to another waiter")
            target = await conn.fetchrow(
                '''SELECT id,seats,status,"isActive" FROM kitchen_tables WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                payload.target_table_id, pid,
            )
            if not target or not target["isActive"] or target["status"] == "OUT_OF_SERVICE":
                raise HTTPException(status_code=404, detail="Target table not available")
            if int(session["partySize"]) > int(target["seats"]):
                raise HTTPException(status_code=409, detail={"code": "DINING_TABLE_TOO_SMALL", "seats": target["seats"], "party_size": session["partySize"]})
            if session["status"] == "SEATED":
                conflict = await conn.fetchrow(
                    '''SELECT id FROM dining_table_sessions WHERE "tableId"=$1 AND status='SEATED' AND id<>$2 LIMIT 1 FOR UPDATE''',
                    payload.target_table_id, session_id,
                )
                if conflict:
                    raise HTTPException(status_code=409, detail={"code": "DINING_TABLE_OCCUPIED", "session_id": str(conflict["id"])})

            if payload.waiter_mode == "KEEP":
                waiter_id = session["waiterId"]
            elif payload.waiter_mode == "CLEAR":
                if user["role"] == "DINING_STAFF":
                    raise HTTPException(status_code=403, detail="Dining staff cannot clear assignment")
                waiter_id = None
            else:
                waiter_id = await validate_waiter(conn, pid, user, payload.waiter_id)
                if waiter_id is None:
                    raise HTTPException(status_code=422, detail="waiter_id is required for ASSIGN")

            old_table_id = session["tableId"]
            await conn.execute(
                '''UPDATE dining_table_sessions SET "tableId"=$2,"waiterId"=$3,notes=COALESCE($4,notes),"updatedAt"=now() WHERE id=$1''',
                session_id, payload.target_table_id, waiter_id, payload.notes,
            )
            await conn.execute('UPDATE kitchen_tables SET status=\'CLEANING\',"updatedAt"=now() WHERE id=$1', old_table_id)
            await conn.execute(
                'UPDATE kitchen_tables SET status=$2,"updatedAt"=now() WHERE id=$1',
                payload.target_table_id, "OCCUPIED" if session["status"] == "SEATED" else "RESERVED",
            )
            await audit(conn, pid, user, "MOVE_DINING_TABLE_SESSION", str(session_id), {
                "from_table_id": str(old_table_id), "to_table_id": str(payload.target_table_id),
                "waiter_mode": payload.waiter_mode, "waiter_id": str(waiter_id) if waiter_id else None,
            })
            result = await conn.fetchrow(SESSION_SELECT + ' WHERE ds.id=$1', session_id)
    return session_item(result)
