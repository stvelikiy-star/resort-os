import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/guest-crm", tags=["guest-crm"])
manager_access = require_roles("OWNER", "MANAGER")

PREFERENCE_LABELS = {
    "ROOM_LOCATION": "Расположение номера",
    "FLOOR": "Этаж",
    "BED_LAYOUT": "Конфигурация кроватей",
    "LANGUAGE": "Язык общения",
    "COMMUNICATION_CHANNEL": "Канал связи",
    "HOUSEKEEPING_TIME": "Удобное время уборки",
}
SAFE_EVENT_PAYLOAD_KEYS = {
    "room_id",
    "from_room_id",
    "to_room_id",
    "booking_number",
    "request_code",
    "task_id",
}


class PreferenceUpsert(BaseModel):
    value: str = Field(min_length=1, max_length=240)


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def require_guest(conn, property_id_value: uuid.UUID, guest_id: uuid.UUID):
    row = await conn.fetchrow(
        '''SELECT id,"firstName","lastName",phone,email,"createdAt","updatedAt" FROM guests WHERE id=$1 AND "propertyId"=$2''',
        guest_id,
        property_id_value,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Guest not found")
    return row


def safe_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    clean = {key: value[key] for key in SAFE_EVENT_PAYLOAD_KEYS if key in value and value[key] is not None}
    return clean or None


@router.get("/{guest_id}")
async def guest_crm_detail(
    guest_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        guest = await require_guest(conn, pid, guest_id)
        stays = await conn.fetch(
            '''
            SELECT s.id,s.status::text AS status,s."reservationId",s."actualCheckInAt",s."actualCheckOutAt",
                   s."createdAt",s."updatedAt",r."bookingNumber",r."checkIn",r."checkOut",r."totalKgs"
            FROM stays s
            JOIN reservations r ON r.id=s."reservationId"
            WHERE s."propertyId"=$1 AND s."guestId"=$2
            ORDER BY COALESCE(s."actualCheckInAt",r."checkIn"::timestamp) DESC,s."createdAt" DESC
            ''',
            pid,
            guest_id,
        )
        stay_ids = [row["id"] for row in stays]
        assignments = []
        requests_rows = []
        if stay_ids:
            assignments = await conn.fetch(
                '''
                SELECT ra.id,ra."stayId",ra."roomId",ra."startedAt",ra."endedAt",ra.source,
                       room.code AS room_code,room.name AS room_name,rt.name AS room_type_name
                FROM room_assignments ra
                JOIN rooms room ON room.id=ra."roomId"
                JOIN room_types rt ON rt.id=room."roomTypeId"
                WHERE ra."propertyId"=$1 AND ra."stayId"=ANY($2::uuid[])
                ORDER BY ra."startedAt",ra."createdAt"
                ''',
                pid,
                stay_ids,
            )
            requests_rows = await conn.fetch(
                '''
                SELECT id,"stayId","serviceCode",source,status::text AS status,priority::text AS priority,
                       title,description,"createdAt","updatedAt","completedAt"
                FROM operational_tasks
                WHERE "propertyId"=$1 AND "stayId"=ANY($2::uuid[]) AND type='GUEST_REQUEST'
                ORDER BY "createdAt" DESC
                ''',
                pid,
                stay_ids,
            )
        events = await conn.fetch(
            '''
            SELECT id,"stayId","eventType",source,"payloadJson","occurredAt","createdAt"
            FROM guest_history_events
            WHERE "propertyId"=$1 AND "guestId"=$2
            ORDER BY "occurredAt" DESC,"createdAt" DESC
            LIMIT 500
            ''',
            pid,
            guest_id,
        )
        preferences = await conn.fetch(
            '''
            SELECT id,key,"valueText",source,"isActive","createdAt","updatedAt"
            FROM guest_preferences
            WHERE "propertyId"=$1 AND "guestId"=$2
            ORDER BY "isActive" DESC,key
            ''',
            pid,
            guest_id,
        )

    assignments_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in assignments:
        assignments_by[str(row["stayId"])].append(
            {
                "id": str(row["id"]),
                "room_id": str(row["roomId"]),
                "room_code": row["room_code"],
                "room_name": row["room_name"],
                "room_type_name": row["room_type_name"],
                "started_at": row["startedAt"],
                "ended_at": row["endedAt"],
                "source": row["source"],
            }
        )
    requests_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in requests_rows:
        requests_by[str(row["stayId"])].append(
            {
                "id": str(row["id"]),
                "request_code": row["serviceCode"],
                "source": row["source"],
                "status": row["status"],
                "priority": row["priority"],
                "title": row["title"],
                "description": row["description"],
                "created_at": row["createdAt"],
                "updated_at": row["updatedAt"],
                "completed_at": row["completedAt"],
            }
        )

    return {
        "guest": {
            "id": str(guest["id"]),
            "first_name": guest["firstName"],
            "last_name": guest["lastName"],
            "phone": guest["phone"],
            "email": guest["email"],
            "created_at": guest["createdAt"],
            "updated_at": guest["updatedAt"],
        },
        "stays": [
            {
                "id": str(row["id"]),
                "status": row["status"],
                "reservation_id": str(row["reservationId"]),
                "booking_number": row["bookingNumber"],
                "planned_check_in": row["checkIn"],
                "planned_check_out": row["checkOut"],
                "actual_check_in_at": row["actualCheckInAt"],
                "actual_check_out_at": row["actualCheckOutAt"],
                "total_kgs": row["totalKgs"],
                "assignments": assignments_by.get(str(row["id"]), []),
                "requests": requests_by.get(str(row["id"]), []),
            }
            for row in stays
        ],
        "preferences": [
            {
                "id": str(row["id"]),
                "key": row["key"],
                "label": PREFERENCE_LABELS.get(row["key"], row["key"]),
                "value": row["valueText"],
                "source": row["source"],
                "active": row["isActive"],
                "created_at": row["createdAt"],
                "updated_at": row["updatedAt"],
            }
            for row in preferences
        ],
        "events": [
            {
                "id": str(row["id"]),
                "stay_id": str(row["stayId"]) if row["stayId"] else None,
                "event_type": row["eventType"],
                "source": row["source"],
                "payload": safe_payload(row["payloadJson"]),
                "occurred_at": row["occurredAt"],
            }
            for row in events
        ],
        "preference_keys": [{"key": key, "label": label} for key, label in PREFERENCE_LABELS.items()],
        "truth": "Actual stay and room-assignment history comes from Stay/RoomAssignment. Preferences are explicit manager-approved non-sensitive service preferences; no automatic profiling or guest merging is performed.",
    }


@router.put("/{guest_id}/preferences/{key}")
async def upsert_guest_preference(
    guest_id: uuid.UUID,
    key: str,
    payload: PreferenceUpsert,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    normalized = key.strip().upper()
    if normalized not in PREFERENCE_LABELS:
        raise HTTPException(status_code=422, detail={"code": "PREFERENCE_KEY_NOT_ALLOWED", "allowed": sorted(PREFERENCE_LABELS)})
    value = payload.value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Preference value cannot be empty")

    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            await require_guest(conn, pid, guest_id)
            before = await conn.fetchrow(
                '''SELECT id,"valueText","isActive" FROM guest_preferences WHERE "guestId"=$1 AND key=$2 FOR UPDATE''',
                guest_id,
                normalized,
            )
            preference_id = before["id"] if before else uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO guest_preferences (id,"propertyId","guestId",key,"valueText",source,"isActive","createdAt","updatedAt")
                VALUES ($1,$2,$3,$4,$5,'MANAGER_CRM',true,now(),now())
                ON CONFLICT ("guestId",key) DO UPDATE SET
                  "valueText"=EXCLUDED."valueText",source='MANAGER_CRM',"isActive"=true,"updatedAt"=now()
                ''',
                preference_id,
                pid,
                guest_id,
                normalized,
                value,
            )
            await conn.execute(
                '''
                INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt")
                VALUES ($1,$2,'STAFF',$3,'UPSERT_GUEST_PREFERENCE','GuestPreference',$4,'GUEST_CRM','SUCCESS',
                  $5::jsonb,jsonb_build_object('guest_id',$6::text,'key',$7::text,'value',$8::text,'active',true),now())
                ''',
                uuid.uuid4(),
                pid,
                user["id"],
                str(preference_id),
                None if not before else {"value": before["valueText"], "active": before["isActive"]},
                str(guest_id),
                normalized,
                value,
            )
    return {"id": str(preference_id), "guest_id": str(guest_id), "key": normalized, "label": PREFERENCE_LABELS[normalized], "value": value, "active": True}


@router.delete("/{guest_id}/preferences/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_guest_preference(
    guest_id: uuid.UUID,
    key: str,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    normalized = key.strip().upper()
    if normalized not in PREFERENCE_LABELS:
        raise HTTPException(status_code=404, detail="Preference not found")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            await require_guest(conn, pid, guest_id)
            row = await conn.fetchrow(
                '''SELECT id,"valueText","isActive" FROM guest_preferences WHERE "propertyId"=$1 AND "guestId"=$2 AND key=$3 FOR UPDATE''',
                pid,
                guest_id,
                normalized,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Preference not found")
            await conn.execute('UPDATE guest_preferences SET "isActive"=false,"updatedAt"=now() WHERE id=$1', row["id"])
            await conn.execute(
                '''INSERT INTO audit_logs (id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt")
                   VALUES ($1,$2,'STAFF',$3,'DEACTIVATE_GUEST_PREFERENCE','GuestPreference',$4,'GUEST_CRM','SUCCESS',
                     jsonb_build_object('guest_id',$5::text,'key',$6::text,'value',$7::text,'active',$8::boolean),
                     jsonb_build_object('guest_id',$5::text,'key',$6::text,'active',false),now())''',
                uuid.uuid4(), pid, user["id"], str(row["id"]), str(guest_id), normalized, row["valueText"], row["isActive"],
            )
