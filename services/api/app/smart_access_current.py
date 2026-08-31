from fastapi import APIRouter, Cookie, HTTPException, Request

from .my_stay import _guest_context

router = APIRouter(tags=["smart-access"])


@router.get("/api/v1/guest/access/current-room")
async def guest_current_room_access(
    request: Request,
    resort_guest_session: str | None = Cookie(default=None),
):
    """Return the active access point for the room assigned to the current stay.

    This is discovery only. The QR/session is never itself a door key; unlock still
    passes through the normal grant/payment/controller checks in smart_access.py.
    """
    ctx = await _guest_context(request, resort_guest_session)
    if not ctx["room_id"]:
        raise HTTPException(status_code=404, detail="Current room is not resolved")

    async with request.app.state.db.acquire() as conn:
        point = await conn.fetchrow(
            '''
            SELECT code,name,kind,"priceKgs",active,"controllerRef"
            FROM smart_access_points
            WHERE "propertyId"=$1 AND "roomId"=$2 AND kind='ROOM' AND active=true
            ORDER BY "updatedAt" DESC,id
            LIMIT 1
            ''',
            ctx["property_id"],
            ctx["room_id"],
        )
    if not point:
        raise HTTPException(status_code=404, detail="Digital room access is not enabled")

    return {
        "code": point["code"],
        "name": point["name"],
        "kind": point["kind"],
        "price_kgs": int(point["priceKgs"]),
        "payment_required": int(point["priceKgs"]) > 0,
        "controller_bound": bool(point["controllerRef"]),
        "room_code": ctx["room_code"],
    }
