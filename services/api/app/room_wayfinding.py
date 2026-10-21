"""Optional guest-safe physical-room directions. No lock credentials or guest PII."""
import uuid
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles, trusted_property_id
from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context

router = APIRouter(prefix="/api/v1/admin/rooms", tags=["room-wayfinding"])
guest_router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-room-wayfinding"])
manager_access = require_roles("OWNER", "MANAGER")


class RoomWayfindingPatch(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    parking_label: str | None = Field(default=None, max_length=100)
    directions: str | None = Field(default=None, max_length=1200)
    walkthrough_video_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("GPS latitude and longitude must be set together")
        if self.walkthrough_video_url:
            u = urlsplit(self.walkthrough_video_url)
            if u.scheme != "https" or not u.hostname or u.username or u.password:
                raise ValueError("Only public HTTPS video links are allowed")
        return self


def serialize(row: Any) -> dict[str, Any]:
    if row is None:
        return {"latitude": None, "longitude": None, "parking_label": "",
                "directions": "", "walkthrough_video_url": "", "map_url": None}
    lat = row["latitude"]
    lon = row["longitude"]
    return {"latitude": lat, "longitude": lon,
            "parking_label": row["parkingLabel"] or "",
            "directions": row["directions"] or "",
            "walkthrough_video_url": row["walkthroughVideoUrl"] or "",
            "map_url": f"https://www.google.com/maps/search/?api=1&query={lat}%2C{lon}" if lat is not None and lon is not None else None}


async def fetch_room_route(conn, pid: uuid.UUID, rid: uuid.UUID):
    return await conn.fetchrow(
        '''SELECT latitude,longitude,"parkingLabel",directions,"walkthroughVideoUrl"
           FROM room_wayfinding WHERE "propertyId"=$1 AND "roomId"=$2''',
        pid, rid,
    )


@router.get("/{room_id}/wayfinding")
async def admin_room_route(room_id: uuid.UUID, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        exists = await conn.fetchval('SELECT 1 FROM rooms WHERE id=$1 AND "propertyId"=$2', room_id, pid)
        if not exists:
            raise HTTPException(status_code=404, detail="Room not found")
        row = await fetch_room_route(conn, pid, room_id)
    return {"wayfinding": serialize(row)}


@router.put("/{room_id}/wayfinding")
async def update_room_route(room_id: uuid.UUID, payload: RoomWayfindingPatch, request: Request,
                            user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await trusted_property_id(conn, user)
            exists = await conn.fetchval('SELECT 1 FROM rooms WHERE id=$1 AND "propertyId"=$2 FOR UPDATE', room_id, pid)
            if not exists:
                raise HTTPException(status_code=404, detail="Room not found")
            await conn.execute(
                '''INSERT INTO room_wayfinding
                    (id,"propertyId","roomId",latitude,longitude,"parkingLabel",directions,"walkthroughVideoUrl")
                   VALUES($1,$2,$3,$4,$5,$6,$7,$8)
                   ON CONFLICT ("roomId") DO UPDATE SET
                    latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude,
                    "parkingLabel"=EXCLUDED."parkingLabel",
                    directions=EXCLUDED.directions,
                    "walkthroughVideoUrl"=EXCLUDED."walkthroughVideoUrl",
                    "updatedAt"=now()
                   WHERE room_wayfinding."propertyId"=EXCLUDED."propertyId"''',
                uuid.uuid4(), pid, room_id, payload.latitude, payload.longitude,
                payload.parking_label or None, payload.directions or None,
                payload.walkthrough_video_url or None,
            )
            row = await fetch_room_route(conn, pid, room_id)
    return {"wayfinding": serialize(row)}


@guest_router.get("/rooms/{token}/wayfinding")
async def guest_room_route(token: str, request: Request,
                           tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        qr, _stay, _session = await authorized_context(conn, token, tc_guest_session)
        row = await fetch_room_route(conn, qr["propertyId"], qr["roomId"])
    return {"wayfinding": serialize(row), "guest_safe": True}
