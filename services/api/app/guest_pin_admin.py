import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth import require_roles
from .stays import issue_guest_pin

router = APIRouter(prefix="/api/v1/admin/guest-access", tags=["guest-access-admin"])
manager_access = require_roles("OWNER", "MANAGER", "RECEPTION")


@router.post("/reservations/{reservation_id}/pin")
async def reissue_guest_pin(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict = Depends(manager_access),
):
    """Issue a new one-time Guest OS PIN for an active checked-in stay.

    Plaintext is returned once and is never persisted. Only the salted PBKDF2 hash
    is stored. Existing authenticated guest sessions stay active; this endpoint is
    for a lost/expired admission PIN, not session revocation.
    """
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await conn.fetchrow(
                'SELECT id FROM properties WHERE code=$1', user["property_code"]
            )
            if not prop:
                raise HTTPException(status_code=503, detail="Property not loaded")

            reservation = await conn.fetchrow(
                '''
                SELECT id,status::text AS status,"bookingNumber"
                FROM reservations
                WHERE id=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                reservation_id,
                prop["id"],
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation["status"] != "CHECKED_IN":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "GUEST_PIN_REQUIRES_CHECKED_IN",
                        "reservation_status": reservation["status"],
                    },
                )

            stay = await conn.fetchrow(
                '''
                SELECT id,status::text AS status
                FROM stays
                WHERE "reservationId"=$1 AND "propertyId"=$2
                FOR UPDATE
                ''',
                reservation_id,
                prop["id"],
            )
            if not stay or stay["status"] != "ACTIVE":
                raise HTTPException(
                    status_code=409,
                    detail={"code": "ACTIVE_STAY_REQUIRED"},
                )

            guest_pin, guest_pin_hash = issue_guest_pin()
            await conn.execute(
                '''
                UPDATE stays
                SET "guestAccessPinHash"=$1,
                    "guestAccessPinIssuedAt"=now(),
                    "guestAccessPinExpiresAt"=now() + interval '24 hours',
                    "updatedAt"=now()
                WHERE id=$2
                ''',
                guest_pin_hash,
                stay["id"],
            )

            await conn.execute(
                '''
                INSERT INTO audit_logs (
                  id,"propertyId","actorType","actorId",action,resource,"resourceId",
                  source,result,"afterJson","createdAt"
                ) VALUES ($1,$2,'STAFF',$3,'GUEST_PIN_REISSUE','Stay',$4,'PMS','SUCCESS',
                  jsonb_build_object(
                    'reservation_id',$5::text,
                    'booking_number',$6::text,
                    'guest_pin_issued',true,
                    'valid_hours',24
                  ),now())
                ''',
                uuid.uuid4(),
                prop["id"],
                user["id"],
                str(stay["id"]),
                str(reservation_id),
                reservation["bookingNumber"],
            )

    return {
        "reservation_id": str(reservation_id),
        "stay_id": str(stay["id"]),
        "status": "CHECKED_IN",
        "guest_access_pin": guest_pin,
        "guest_access_pin_valid_for_hours": 24,
        "guest_access_pin_display_once": True,
    }
