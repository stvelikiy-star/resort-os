"""Private stay feedback in existing QR/PIN guest session and PMS guest history.

No automatic messaging, no rating-gated public review links, no KOL integration.
"""
import uuid
from typing import Any
from fastapi import APIRouter, Cookie, HTTPException, Request
from pydantic import BaseModel, Field

from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context

router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-stay-review"])


class StayReviewInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)


async def read_review(conn, property_id, stay_id, guest_id) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        '''SELECT rating,comment,"createdAt","updatedAt"
           FROM guest_stay_reviews
           WHERE "propertyId"=$1 AND "stayId"=$2 AND "guestId"=$3''',
        property_id, stay_id, guest_id,
    )
    if not row:
        return None
    return {"rating": row["rating"], "comment": row["comment"],
            "created_at": row["createdAt"], "updated_at": row["updatedAt"]}


@router.get("/rooms/{token}/review")
async def get_my_stay_review(
    token: str, request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        qr, stay, _ = await authorized_context(conn, token, tc_guest_session)
        review = await read_review(conn, qr["propertyId"], stay["stayId"], stay["guestId"])
    return {"review": review, "outbound_authority": "NONE_AUTOMATIC",
            "public_reviews_available_regardless_of_rating": True}


@router.put("/rooms/{token}/review")
async def submit_my_stay_review(
    token: str, payload: StayReviewInput, request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, _ = await authorized_context(conn, token, tc_guest_session)
            if not (payload.comment or "").strip() and payload.rating <= 3:
                # A low star rating is itself actionable; do not compel text.
                pass
            await conn.execute(
                '''INSERT INTO guest_stay_reviews
                   (id,"propertyId","stayId","guestId",rating,comment,"createdAt","updatedAt")
                   VALUES ($1,$2,$3,$4,$5,$6,now(),now())
                   ON CONFLICT ("stayId") DO UPDATE SET
                       rating=EXCLUDED.rating, comment=EXCLUDED.comment, "updatedAt"=now()
                   WHERE guest_stay_reviews."propertyId"=EXCLUDED."propertyId"
                     AND guest_stay_reviews."guestId"=EXCLUDED."guestId"''',
                uuid.uuid4(), qr["propertyId"], stay["stayId"], stay["guestId"],
                payload.rating, payload.comment.strip(),
            )
            review = await read_review(conn, qr["propertyId"], stay["stayId"], stay["guestId"])
            if review is None:
                raise HTTPException(status_code=409, detail="Review could not be saved for this stay")
    return {"review": review, "manager_attention_required": payload.rating <= 3,
            "outbound_authority": "NONE_AUTOMATIC"}
