import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/rooms", tags=["admin-room-detail"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/{room_id}")
async def room_detail(
    room_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        property_id = await conn.fetchval("SELECT id FROM properties WHERE code=$1", user["property_code"])
        if not property_id:
            raise HTTPException(status_code=503, detail="Property not loaded")

        room = await conn.fetchrow(
            '''
            SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",r."areaLabel",
                   r."operationalState"::text AS operational_state,r.notes,r."createdAt",r."updatedAt",
                   rt.code AS room_type_code,rt.name AS room_type_name,rt."capacityAdults",rt."capacityChildren"
            FROM rooms r
            JOIN room_types rt ON rt.id=r."roomTypeId"
            WHERE r.id=$1 AND r."propertyId"=$2
            ''',
            room_id, property_id,
        )
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        blocks = await conn.fetch(
            '''
            SELECT ib.id,ib."blockType"::text AS block_type,ib."startDate",ib."endDate",ib.active,ib.reason,
                   res.id AS reservation_id,res."bookingNumber",res.status::text AS reservation_status,
                   g."firstName",g."lastName"
            FROM inventory_blocks ib
            LEFT JOIN reservations res ON res.id=ib."reservationId"
            LEFT JOIN guests g ON g.id=res."primaryGuestId"
            WHERE ib."roomId"=$1
            ORDER BY ib."startDate" DESC,ib."createdAt" DESC
            LIMIT 100
            ''',
            room_id,
        )

        tasks = await conn.fetch(
            '''
            SELECT t.id,t.type::text AS type,t.status::text AS status,t.priority::text AS priority,
                   t.title,t.description,t.source,t."createdAt",t."updatedAt",t."completedAt",
                   u."displayName" AS assigned_to
            FROM operational_tasks t
            LEFT JOIN staff_users u ON u.id=t."assignedToId"
            WHERE t."propertyId"=$1 AND t."roomId"=$2
            ORDER BY t."createdAt" DESC
            LIMIT 100
            ''',
            property_id, room_id,
        )

        task_ids = [str(row["id"]) for row in tasks]
        audit_rows = []
        if task_ids:
            audit_rows = await conn.fetch(
                '''
                SELECT a.id,a."resourceId",a."actorType",a."actorId",a.action,a.source,a.result,a."afterJson",a."createdAt",
                       u."displayName" AS actor_name,u.role::text AS actor_role
                FROM audit_logs a
                LEFT JOIN staff_users u ON u."propertyId"=$1 AND u.id::text=a."actorId"
                WHERE a."propertyId"=$1
                  AND a.resource='OperationalTask'
                  AND a."resourceId" = ANY($2::text[])
                ORDER BY a."createdAt" DESC
                LIMIT 300
                ''',
                property_id, task_ids,
            )

    def guest_name(row):
        parts = [row["firstName"], row["lastName"]]
        value = " ".join(part for part in parts if part)
        return value or None

    return {
        "room": {
            "id": str(room["id"]),
            "code": room["code"],
            "name": room["name"],
            "room_type_code": room["room_type_code"],
            "room_type_name": room["room_type_name"],
            "capacity_adults": room["capacityAdults"],
            "capacity_children": room["capacityChildren"],
            "building_or_zone": room["buildingOrZone"],
            "floor": room["floorLabel"],
            "beds_raw": room["bedConfiguration"],
            "area": room["areaLabel"],
            "operational_state": room["operational_state"],
            "notes": room["notes"],
            "updated_at": room["updatedAt"],
        },
        "blocks": [
            {
                "id": str(row["id"]),
                "type": row["block_type"],
                "start": row["startDate"],
                "end": row["endDate"],
                "active": row["active"],
                "reason": row["reason"],
                "reservation": {
                    "id": str(row["reservation_id"]),
                    "booking_number": row["bookingNumber"],
                    "status": row["reservation_status"],
                    "guest_name": guest_name(row),
                } if row["reservation_id"] else None,
            }
            for row in blocks
        ],
        "tasks": [
            {
                "id": str(row["id"]),
                "type": row["type"],
                "status": row["status"],
                "priority": row["priority"],
                "title": row["title"],
                "description": row["description"],
                "assigned_to": row["assigned_to"],
                "source": row["source"],
                "created_at": row["createdAt"],
                "updated_at": row["updatedAt"],
                "completed_at": row["completedAt"],
            }
            for row in tasks
        ],
        "task_history": [
            {
                "id": str(row["id"]),
                "task_id": row["resourceId"],
                "actor_type": row["actorType"],
                "actor_id": row["actorId"],
                "actor_name": row["actor_name"],
                "actor_role": row["actor_role"],
                "action": row["action"],
                "source": row["source"],
                "result": row["result"],
                "after": row["afterJson"],
                "created_at": row["createdAt"],
            }
            for row in audit_rows
        ],
        "truth": "Only stored Resort Core room, inventory-block, task and audit facts are returned; missing building/floor/area fields remain null.",
    }
