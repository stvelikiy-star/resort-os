import asyncio
import hashlib
import json
import os
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from .auth import SESSION_COOKIE, resolve_session_user, trusted_property_id
from .section_permissions import role_or_section_allowed
from .websocket_security import require_websocket_same_origin, websocket_authority

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
POLL_SECONDS = float(os.environ.get("PMS_WS_POLL_SECONDS", "2"))
router = APIRouter(tags=["realtime"])


def parse_iso_date(raw: str | None, fallback: date) -> date:
    if not raw:
        return fallback
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("invalid ISO date") from exc


async def authenticate_websocket(websocket: WebSocket, conn) -> dict[str, Any] | None:
    try:
        user = await resolve_session_user(conn, websocket.cookies.get(SESSION_COOKIE), touch=False)
    except HTTPException:
        await websocket.close(code=4401, reason="Session expired or invalid")
        return None
    roles = ("OWNER", "MANAGER", "RECEPTION")
    if user["role"] not in roles or not role_or_section_allowed(user, "/api/v1/pms/grid", roles):
        await websocket.close(code=4403, reason="PMS realtime requires management role")
        return None
    return user


async def build_snapshot(conn, start: date, end: date, user: dict[str, Any]) -> dict[str, Any]:
    property_id = await trusted_property_id(conn, user)
    rooms = await conn.fetch(
        '''
        SELECT r.id,r.code,r.name,r."buildingOrZone",r."floorLabel",r."bedConfiguration",
               r."operationalState"::text AS operational_state,
               rt.code AS room_type_code,rt.name AS room_type_name
        FROM rooms r
        JOIN room_types rt ON rt.id=r."roomTypeId"
        WHERE r."propertyId"=$1
        ORDER BY rt.name,r.code
        ''',
        property_id,
    )
    blocks = await conn.fetch(
        '''
        SELECT ib.id,ib."roomId",ib."blockType"::text AS block_type,ib."startDate",ib."endDate",ib.reason,
               res.id AS reservation_id,res."bookingNumber",res.status::text AS reservation_status,
               rr.source AS channel_source,
               g."firstName",g."lastName",g.phone
        FROM inventory_blocks ib
        JOIN rooms r ON r.id=ib."roomId"
        LEFT JOIN reservations res ON res.id=ib."reservationId"
        LEFT JOIN reservation_requests rr ON rr.id=res."requestId"
        LEFT JOIN guests g ON g.id=res."primaryGuestId"
        WHERE r."propertyId"=$1 AND ib.active=true
          AND daterange(ib."startDate",ib."endDate",'[)') && daterange($2::date,$3::date,'[)')
        ORDER BY ib."startDate"
        ''',
        property_id, start, end,
    )
    blocks_by_room: dict[str, list[dict[str, Any]]] = {}
    for block in blocks:
        rid = str(block["roomId"])
        guest_name = " ".join(filter(None, [block["firstName"], block["lastName"]])) or None
        blocks_by_room.setdefault(rid, []).append({
            "id": str(block["id"]),
            "type": block["block_type"],
            "start": block["startDate"].isoformat(),
            "end": block["endDate"].isoformat(),
            "reason": block["reason"],
            "reservation_id": str(block["reservation_id"]) if block["reservation_id"] else None,
            "booking_number": block["bookingNumber"],
            "reservation_status": block["reservation_status"],
            "guest_name": guest_name,
            "guest_phone": block["phone"],
            "channel_source": block["channel_source"],
        })
    return {
        "property": user["property_code"],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "rooms": [{
            "id": str(room["id"]),
            "code": room["code"],
            "name": room["name"],
            "room_type_code": room["room_type_code"],
            "room_type_name": room["room_type_name"],
            "building_or_zone": room["buildingOrZone"],
            "floor": room["floorLabel"],
            "beds_raw": room["bedConfiguration"],
            "operational_state": room["operational_state"],
            "blocks": blocks_by_room.get(str(room["id"]), []),
        } for room in rooms],
    }


@router.websocket("/ws/pms/grid")
async def pms_grid_websocket(websocket: WebSocket):
    if not await require_websocket_same_origin(websocket):
        return

    today = date.today()
    try:
        start = parse_iso_date(websocket.query_params.get("start"), today)
        end = parse_iso_date(websocket.query_params.get("end"), start + timedelta(days=14))
    except ValueError:
        await websocket.close(code=4400, reason="Invalid date range")
        return
    if end <= start or (end - start).days > 62:
        await websocket.close(code=4400, reason="Grid range must be 1-62 days")
        return

    async with websocket.app.state.db.acquire() as conn:
        user = await authenticate_websocket(websocket, conn)
    if not user:
        return
    await websocket.accept()
    authority = websocket_authority(user)
    last_digest: str | None = None
    heartbeat = 0
    try:
        while True:
            async with websocket.app.state.db.acquire() as conn:
                user = await authenticate_websocket(websocket, conn)
                if not user:
                    return
                if websocket_authority(user) != authority:
                    await websocket.close(code=4403, reason="Session authority changed; reconnect required")
                    return
                snapshot = await build_snapshot(conn, start, end, user)
            encoded = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            if digest != last_digest:
                await websocket.send_json({
                    "type": "pms.grid.snapshot",
                    "version": digest[:16],
                    "data": snapshot,
                })
                last_digest = digest
            heartbeat += 1
            if heartbeat >= max(1, int(20 / max(POLL_SECONDS, 0.25))):
                await websocket.send_json({"type": "heartbeat"})
                heartbeat = 0
            await asyncio.sleep(max(POLL_SECONDS, 0.25))
    except WebSocketDisconnect:
        return
