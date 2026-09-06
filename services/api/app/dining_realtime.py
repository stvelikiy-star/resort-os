from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .auth import SESSION_COOKIE, hash_session_token

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
POLL_SECONDS = max(0.25, float(os.environ.get("DINING_WS_POLL_SECONDS", "1")))
router = APIRouter(tags=["dining-realtime"])
ALLOWED_ROLES = {"OWNER", "MANAGER", "DINING_STAFF"}


async def authenticate(websocket: WebSocket, conn) -> dict[str, Any] | None:
    raw_token = websocket.cookies.get(SESSION_COOKIE)
    if not raw_token:
        await websocket.close(code=4401, reason="Authentication required")
        return None
    row = await conn.fetchrow(
        '''SELECT s."expiresAt",s."revokedAt",u.id AS user_id,u.username,u."displayName",
                  u.role::text AS role,u."isActive",p.id AS property_id,p.code AS property_code
           FROM auth_sessions s
           JOIN staff_users u ON u.id=s."userId"
           JOIN properties p ON p.id=u."propertyId"
           WHERE s."tokenHash"=$1''',
        hash_session_token(raw_token),
    )
    if (
        not row
        or row["revokedAt"] is not None
        or row["expiresAt"] <= datetime.utcnow()
        or not row["isActive"]
        or row["property_code"] != PROPERTY_CODE
    ):
        await websocket.close(code=4401, reason="Session expired or invalid")
        return None
    if row["role"] not in ALLOWED_ROLES:
        await websocket.close(code=4403, reason="Dining realtime requires dining or management role")
        return None
    return {
        "id": str(row["user_id"]),
        "user_id": row["user_id"],
        "display_name": row["displayName"],
        "role": row["role"],
        "property_id": row["property_id"],
        "property_code": row["property_code"],
    }


async def ready_orders(conn, user: dict[str, Any]) -> list[dict[str, Any]]:
    # DINING_STAFF receives only orders explicitly assigned to that waiter.
    # OWNER/MANAGER may observe all READY orders for operational supervision.
    rows = await conn.fetch(
        '''SELECT o.id,o."orderNumber",o."tableId",o."roomId",o."waiterId",o."guestCount",o."totalKgs",o."readyAt",
                  t.code AS table_code,t.name AS table_name,r.code AS room_code
           FROM kitchen_orders o
           LEFT JOIN kitchen_tables t ON t.id=o."tableId"
           LEFT JOIN rooms r ON r.id=o."roomId"
           WHERE o."propertyId"=$1 AND o.status='READY'
             AND ($2::boolean OR o."waiterId"=$3)
           ORDER BY o."readyAt",o."openedAt",o.id''',
        user["property_id"],
        user["role"] in {"OWNER", "MANAGER"},
        user["user_id"],
    )
    return [
        {
            "id": str(row["id"]),
            "order_number": row["orderNumber"],
            "table_id": str(row["tableId"]) if row["tableId"] else None,
            "table_code": row["table_code"],
            "table_name": row["table_name"],
            "room_code": row["room_code"],
            "waiter_id": str(row["waiterId"]) if row["waiterId"] else None,
            "guest_count": int(row["guestCount"]),
            "total_kgs": int(row["totalKgs"]),
            "ready_at": row["readyAt"].isoformat() if row["readyAt"] else None,
        }
        for row in rows
    ]


@router.websocket("/ws/dining/ready")
async def dining_ready_websocket(websocket: WebSocket):
    async with websocket.app.state.db.acquire() as conn:
        user = await authenticate(websocket, conn)
        if not user:
            return
        await websocket.accept()
        try:
            initial = await ready_orders(conn, user)
            seen = {item["id"] for item in initial}
            await websocket.send_json(
                {
                    "type": "dining.ready.snapshot",
                    "orders": initial,
                    "scope": "ALL" if user["role"] in {"OWNER", "MANAGER"} else "ASSIGNED_TO_ME",
                }
            )
            heartbeat = 0
            while True:
                items = await ready_orders(conn, user)
                for item in items:
                    if item["id"] not in seen:
                        await websocket.send_json({"type": "dining.order.ready", "order": item})
                        seen.add(item["id"])
                heartbeat += 1
                if heartbeat >= max(1, int(20 / POLL_SECONDS)):
                    await websocket.send_json({"type": "heartbeat"})
                    heartbeat = 0
                await asyncio.sleep(POLL_SECONDS)
        except WebSocketDisconnect:
            return
