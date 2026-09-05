import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/dining", tags=["dining-floor-layout"])
read_access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")
layout_access = require_roles("OWNER", "MANAGER")


class TableLayoutPatch(BaseModel):
    floor_x: float = Field(ge=0, le=100)
    floor_y: float = Field(ge=0, le=100)
    zone_label: str = Field(min_length=1, max_length=80)
    floor_shape: Literal["ROUND", "SQUARE", "RECTANGLE"] = "ROUND"


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def table_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row["code"],
        "name": row["name"],
        "seats": row["seats"],
        "status": row["status"],
        "zone_label": row["zoneLabel"],
        "floor_x": float(row["floorX"]) if row["floorX"] is not None else None,
        "floor_y": float(row["floorY"]) if row["floorY"] is not None else None,
        "floor_shape": row["floorShape"],
        "notes": row["notes"],
        "active_orders": int(row["active_orders"] or 0),
        "ready_orders": int(row["ready_orders"] or 0),
    }


def session_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "table_id": str(row["tableId"]),
        "stay_id": str(row["stayId"]),
        "reservation_id": str(row["reservationId"]),
        "status": row["status"],
        "meal_type": row["mealType"],
        "party_size": row["partySize"],
        "adults": row["adults"],
        "children": row["children"],
        "guest_name": row["guest_name"] or "Гость",
        "room_code": row["room_code"],
        "booking_number": row["bookingNumber"],
        "waiter_id": str(row["waiterId"]) if row["waiterId"] else None,
        "waiter_name": row["waiter_name"],
        "seated_at": row["seatedAt"],
        "created_at": row["createdAt"],
    }


@router.get("/floor-layout")
async def floor_layout(request: Request, user: dict[str, Any] = Depends(read_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        local_date = await conn.fetchval(
            '''SELECT (now() AT TIME ZONE COALESCE(timezone,'Asia/Bishkek'))::date FROM properties WHERE id=$1''', pid,
        )
        tables = await conn.fetch(
            '''SELECT t.id,t.code,t.name,t.seats,t.status,t."zoneLabel",t."floorX",t."floorY",t."floorShape",t.notes,
                      count(o.id) FILTER (WHERE o.status IN ('NEW','ACCEPTED','COOKING','READY'))::int AS active_orders,
                      count(o.id) FILTER (WHERE o.status='READY')::int AS ready_orders
               FROM kitchen_tables t
               LEFT JOIN kitchen_orders o ON o."tableId"=t.id AND o."propertyId"=t."propertyId"
               WHERE t."propertyId"=$1 AND t."isActive"=true
               GROUP BY t.id
               ORDER BY t."zoneLabel",t.code''',
            pid,
        )
        sessions = await conn.fetch(
            '''SELECT ds.id,ds."tableId",ds."stayId",ds."reservationId",ds.status,ds."mealType",ds."partySize",
                      ds.adults,ds.children,ds."waiterId",ds."seatedAt",ds."createdAt",
                      r."bookingNumber",trim(concat_ws(' ',g."firstName",g."lastName")) AS guest_name,
                      room.code AS room_code,u."displayName" AS waiter_name
               FROM dining_table_sessions ds
               JOIN stays s ON s.id=ds."stayId" AND s."propertyId"=ds."propertyId"
               JOIN reservations r ON r.id=ds."reservationId"
               JOIN guests g ON g.id=s."guestId"
               LEFT JOIN staff_users u ON u.id=ds."waiterId"
               LEFT JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               LEFT JOIN rooms room ON room.id=ra."roomId"
               WHERE ds."propertyId"=$1 AND ds."serviceDate"=$2 AND ds.status IN ('WAITING','SEATED')
               ORDER BY CASE ds.status WHEN 'SEATED' THEN 0 ELSE 1 END,ds."createdAt"''',
            pid, local_date,
        )
    return {
        "service_date": local_date,
        "editable": user["role"] in {"OWNER", "MANAGER"},
        "current_user_id": user["id"],
        "tables": [table_item(row) for row in tables],
        "sessions": [session_item(row) for row in sessions],
        "truth": "Floor positions are visual metadata only; seating truth remains in dining_table_sessions.",
    }


@router.patch("/floor-layout/tables/{table_id}")
async def patch_floor_table(
    table_id: uuid.UUID,
    payload: TableLayoutPatch,
    request: Request,
    user: dict[str, Any] = Depends(layout_access),
):
    zone_label = payload.zone_label.strip()
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            before = await conn.fetchrow(
                '''SELECT id,code,"zoneLabel","floorX","floorY","floorShape" FROM kitchen_tables
                   WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true FOR UPDATE''', table_id, pid,
            )
            if not before:
                raise HTTPException(status_code=404, detail="Dining table not found")
            row = await conn.fetchrow(
                '''UPDATE kitchen_tables SET "zoneLabel"=$3,"floorX"=$4,"floorY"=$5,"floorShape"=$6,"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,code,name,seats,status,"zoneLabel","floorX","floorY","floorShape",notes''',
                table_id, pid, zone_label, payload.floor_x, payload.floor_y, payload.floor_shape,
            )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"beforeJson","afterJson","createdAt"
                   ) VALUES ($1,$2,'STAFF',$3,'UPDATE_FLOOR_LAYOUT','KitchenTable',$4,'DINING_FLOOR','SUCCESS',$5::jsonb,$6::jsonb,now())''',
                uuid.uuid4(), pid, user["id"], str(table_id),
                json.dumps({
                    "zone_label": before["zoneLabel"],
                    "floor_x": float(before["floorX"]) if before["floorX"] is not None else None,
                    "floor_y": float(before["floorY"]) if before["floorY"] is not None else None,
                    "floor_shape": before["floorShape"],
                }, ensure_ascii=False),
                json.dumps({
                    "zone_label": zone_label,
                    "floor_x": payload.floor_x,
                    "floor_y": payload.floor_y,
                    "floor_shape": payload.floor_shape,
                    "financial_effect": "NONE",
                }, ensure_ascii=False),
            )
    result = table_item({**dict(row), "active_orders": 0, "ready_orders": 0})
    return result
