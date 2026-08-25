from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["health"])


@router.get("/live")
async def live():
    return {"status": "ok", "service": "three-crowns-core", "probe": "liveness"}


@router.get("/ready")
async def ready(request: Request):
    try:
        async with request.app.state.db.acquire() as conn:
            await conn.fetchval("SELECT 1")
            prop = await conn.fetchrow(
                '''
                SELECT p.code,p.name,p.timezone,
                       (SELECT count(*)::int FROM rooms r WHERE r."propertyId"=p.id) AS room_count,
                       (SELECT count(*)::int FROM room_types rt WHERE rt."propertyId"=p.id) AS room_type_count
                FROM properties p
                WHERE p.code=$1
                ''',
                "THREE_CROWNS",
            )
            if not prop:
                raise HTTPException(status_code=503, detail="Three Crowns property is not loaded")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc

    return {
        "status": "ready",
        "service": "three-crowns-core",
        "probe": "readiness",
        "property": prop["code"],
        "timezone": prop["timezone"],
        "room_count": prop["room_count"],
        "room_type_count": prop["room_type_count"],
    }
