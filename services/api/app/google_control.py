import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .service_auth import require_automation_service

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")

router = APIRouter(prefix="/api/v1/automation/read", tags=["automation-read"])
service_access = require_automation_service


def _normalize_since(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(status_code=422, detail="updated_after must include a timezone offset")
    return value.astimezone(timezone.utc)


async def _property_id(conn):
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', PROPERTY_CODE)
    if not value:
        raise HTTPException(status_code=503, detail="Property is not loaded")
    return value


@router.get("/google-control-feed")
async def google_control_feed(
    request: Request,
    updated_after: datetime | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=2000),
    _service: dict[str, Any] = Depends(service_access),
):
    """Read-only operational mirror feed for the Three Crowns Google Control Center.

    Google Sheets is deliberately downstream from Resort Core. This endpoint exposes
    rooms, operational tasks, guests and CMS documents by stable IDs; it provides no
    mutation path for reservations, payments, inventory or stay lifecycle truth.
    """

    since = _normalize_since(updated_after)
    generated_at = datetime.now(timezone.utc)

    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn)

        room_rows = await conn.fetch(
            '''
            SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",
                   r."areaLabel",r."operationalState"::text AS operational_state,r."updatedAt",
                   rt.code AS room_type_code,rt.name AS room_type_name,
                   current_stay."bookingNumber" AS current_booking_number,
                   next_stay."startDate" AS next_check_in,
                   next_stay."bookingNumber" AS next_booking_number,
                   active_task.id AS active_task_id,active_task.title AS active_task_title,
                   active_task.status::text AS active_task_status
            FROM rooms r
            JOIN room_types rt ON rt.id=r."roomTypeId"
            LEFT JOIN LATERAL (
              SELECT res."bookingNumber",ib."startDate",ib."endDate"
              FROM inventory_blocks ib
              JOIN reservations res ON res.id=ib."reservationId"
              WHERE ib."roomId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
                AND ib."startDate"<=CURRENT_DATE AND ib."endDate">CURRENT_DATE
                AND res.status IN ('GUARANTEED','CHECKED_IN')
              ORDER BY ib."startDate",ib."createdAt" LIMIT 1
            ) current_stay ON true
            LEFT JOIN LATERAL (
              SELECT res."bookingNumber",ib."startDate"
              FROM inventory_blocks ib
              JOIN reservations res ON res.id=ib."reservationId"
              WHERE ib."roomId"=r.id AND ib.active=true AND ib."blockType"='RESERVATION'
                AND ib."startDate">=CURRENT_DATE AND res.status='GUARANTEED'
              ORDER BY ib."startDate",ib."createdAt" LIMIT 1
            ) next_stay ON true
            LEFT JOIN LATERAL (
              SELECT t.id,t.title,t.status
              FROM operational_tasks t
              WHERE t."roomId"=r.id AND t.status IN ('OPEN','IN_PROGRESS','IN_INSPECTION')
              ORDER BY CASE t.priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END,
                       t."createdAt" DESC LIMIT 1
            ) active_task ON true
            WHERE r."propertyId"=$1
              AND ($2::timestamptz IS NULL OR r."updatedAt">$2)
            ORDER BY r.code
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

        task_rows = await conn.fetch(
            '''
            SELECT t.id,t."roomId",r.code AS room_code,t.type::text AS type,t.status::text AS status,
                   t.priority::text AS priority,t.title,t.description,t.source,
                   u."displayName" AS assigned_to,t."createdAt",t."completedAt",t."updatedAt"
            FROM operational_tasks t
            LEFT JOIN rooms r ON r.id=t."roomId"
            LEFT JOIN staff_users u ON u.id=t."assignedToId"
            WHERE t."propertyId"=$1
              AND ($2::timestamptz IS NULL OR t."updatedAt">$2)
            ORDER BY t."updatedAt" ASC,t.id ASC
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

        guest_rows = await conn.fetch(
            '''
            SELECT g.id,g."firstName",g."lastName",g.phone,g.email,g."createdAt",g."updatedAt",
                   MIN(r."checkIn") FILTER (WHERE r.status<>'CANCELLED') AS first_check_in,
                   MAX(r."checkIn") FILTER (WHERE r.status<>'CANCELLED') AS last_check_in,
                   COUNT(r.id) FILTER (WHERE r.status<>'CANCELLED')::int AS stay_count,
                   COALESCE(SUM(r."totalKgs") FILTER (WHERE r.status<>'CANCELLED'),0)::int AS ltv_kgs,
                   GREATEST(g."updatedAt",COALESCE(MAX(r."updatedAt"),g."updatedAt")) AS sync_updated_at
            FROM guests g
            LEFT JOIN reservations r ON r."primaryGuestId"=g.id
            WHERE g."propertyId"=$1
            GROUP BY g.id
            HAVING ($2::timestamptz IS NULL OR GREATEST(g."updatedAt",COALESCE(MAX(r."updatedAt"),g."updatedAt"))>$2)
            ORDER BY sync_updated_at ASC,g.id ASC
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

        content_rows = await conn.fetch(
            '''
            SELECT id,locale,scope,"draftJson","publishedJson",version,"publishedVersion",
                   "publishedAt","updatedAt"
            FROM site_content_documents
            WHERE "propertyId"=$1
              AND ($2::timestamptz IS NULL OR "updatedAt">$2)
            ORDER BY locale,scope
            LIMIT $3
            ''',
            property_id,
            since,
            limit + 1,
        )

    rooms_truncated = len(room_rows) > limit
    tasks_truncated = len(task_rows) > limit
    guests_truncated = len(guest_rows) > limit
    content_truncated = len(content_rows) > limit

    return {
        "contract_version": "1.0",
        "property_code": PROPERTY_CODE,
        "generated_at": generated_at,
        "updated_after": since,
        "source_of_truth": "RESORT_CORE",
        "mirror_policy": "Google Control Center is an operational mirror. It must not create or mutate reservation, payment, inventory or stay truth.",
        "rooms": {
            "items": [
                {
                    "room_id": str(row["id"]),
                    "code": row["code"],
                    "name": row["name"],
                    "building_or_zone": row["buildingOrZone"],
                    "floor": row["floorLabel"],
                    "bed_configuration": row["bedConfiguration"],
                    "area": row["areaLabel"],
                    "room_type_code": row["room_type_code"],
                    "room_type_name": row["room_type_name"],
                    "operational_state": row["operational_state"],
                    "current_booking_number": row["current_booking_number"],
                    "next_check_in": row["next_check_in"],
                    "next_booking_number": row["next_booking_number"],
                    "active_task_id": str(row["active_task_id"]) if row["active_task_id"] else None,
                    "active_task_title": row["active_task_title"],
                    "active_task_status": row["active_task_status"],
                    "updated_at": row["updatedAt"],
                }
                for row in room_rows[:limit]
            ],
            "truncated": rooms_truncated,
        },
        "tasks": {
            "items": [
                {
                    "task_id": str(row["id"]),
                    "room_id": str(row["roomId"]) if row["roomId"] else None,
                    "room_code": row["room_code"],
                    "type": row["type"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "title": row["title"],
                    "description": row["description"],
                    "source": row["source"],
                    "assigned_to": row["assigned_to"],
                    "created_at": row["createdAt"],
                    "completed_at": row["completedAt"],
                    "updated_at": row["updatedAt"],
                }
                for row in task_rows[:limit]
            ],
            "truncated": tasks_truncated,
        },
        "guests": {
            "items": [
                {
                    "guest_id": str(row["id"]),
                    "first_name": row["firstName"],
                    "last_name": row["lastName"],
                    "phone": row["phone"],
                    "email": row["email"],
                    "first_check_in": row["first_check_in"],
                    "last_check_in": row["last_check_in"],
                    "stay_count": row["stay_count"],
                    "ltv_kgs": row["ltv_kgs"],
                    "created_at": row["createdAt"],
                    "updated_at": row["sync_updated_at"],
                }
                for row in guest_rows[:limit]
            ],
            "truncated": guests_truncated,
        },
        "site_content": {
            "items": [
                {
                    "document_id": str(row["id"]),
                    "locale": row["locale"],
                    "scope": row["scope"],
                    "draft": row["draftJson"],
                    "published": row["publishedJson"],
                    "version": row["version"],
                    "published_version": row["publishedVersion"],
                    "published_at": row["publishedAt"],
                    "updated_at": row["updatedAt"],
                }
                for row in content_rows[:limit]
            ],
            "truncated": content_truncated,
        },
    }
