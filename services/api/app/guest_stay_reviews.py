"""Private stay feedback in existing QR/PIN guest session and PMS guest history.

No automatic messaging, no rating-gated public review links, no KOL integration.
"""
import uuid
from typing import Any
from fastapi import APIRouter, Cookie, HTTPException, Request
from pydantic import BaseModel, Field

from .guest_os import GUEST_COOKIE
from .guest_requests import authorized_context
from .hotel_rules import load_rules
from .guest_os import PROPERTY_CODE

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


@router.get("/rooms/{token}/review-links")
async def guest_review_links(
    token: str, request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    """Only an authenticated in-stay guest can view this hotel's approved links.
    No review gating: the same links are returned for every rating.
    """
    from urllib.parse import urlsplit

    async with request.app.state.db.acquire() as conn:
        await authorized_context(conn, token, tc_guest_session)
        data = await load_rules(conn, PROPERTY_CODE)
    approved_hosts = {
        "google.com", "www.google.com", "maps.google.com", "maps.app.goo.gl",
        "2gis.kg", "2gis.ru", "go.2gis.com", "2gis.com", "www.2gis.kg",
        "yandex.ru", "yandex.com", "yandex.kz", "maps.yandex.ru",
        "maps.yandex.com", "yandex.kg",
    }
    def approved_link(raw: str) -> str | None:
        try:
            parsed = urlsplit(raw)
            host = (parsed.hostname or "").lower()
            return raw if parsed.scheme == "https" and host in approved_hosts and not parsed.username and not parsed.password else None
        except ValueError:
            return None
    rules = data["rules"]
    return {
        "google": approved_link(rules.get("review_google_url", "")),
        "gis": approved_link(rules.get("review_2gis_url", "")),
        "yandex": approved_link(rules.get("review_yandex_url", "")),
        "available_to_all_ratings": True,
    }


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
