import json
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles
from .guest_os import GUEST_COOKIE
from .guest_requests import REQUEST_LABELS, authorized_context

admin_router = APIRouter(prefix="/api/v1/admin/guest-offers", tags=["admin-guest-offers"])
guest_router = APIRouter(prefix="/api/v1/guest-os", tags=["guest-offers"])
manager_access = require_roles("OWNER", "MANAGER")

ACTION_TYPES = {"GUEST_REQUEST", "EXTERNAL_URL", "AI_PROMPT"}
EVENT_TYPES = {"CLICK", "REQUEST", "EXTERNAL_OPEN", "AI_PROMPT"}


class CampaignWrite(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    title_ru: str = Field(min_length=2, max_length=180)
    title_kg: str = Field(min_length=2, max_length=180)
    title_en: str = Field(min_length=2, max_length=180)
    hook_ru: str = Field(min_length=2, max_length=800)
    hook_kg: str = Field(min_length=2, max_length=800)
    hook_en: str = Field(min_length=2, max_length=800)
    cta_ru: str = Field(default="Хочу", min_length=1, max_length=80)
    cta_kg: str = Field(default="Каалайм", min_length=1, max_length=80)
    cta_en: str = Field(default="Request", min_length=1, max_length=80)
    image_url: str | None = Field(default=None, max_length=1000)
    action_type: Literal["GUEST_REQUEST", "EXTERNAL_URL", "AI_PROMPT"]
    request_code: str | None = Field(default=None, max_length=40)
    external_url: str | None = Field(default=None, max_length=1500)
    ai_prompt: str | None = Field(default=None, max_length=1200)
    active_from: datetime | None = None
    active_to: datetime | None = None
    min_adults: int = Field(default=0, ge=0, le=30)
    min_children: int = Field(default=0, ge=0, le=30)
    min_stay_nights: int = Field(default=0, ge=0, le=120)
    max_stay_nights: int | None = Field(default=None, ge=0, le=120)
    priority: int = Field(default=100, ge=0, le=10000)
    sort_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = False

    @model_validator(mode="after")
    def validate_action(self):
        if self.active_from and self.active_to and self.active_to <= self.active_from:
            raise ValueError("active_to must be after active_from")
        if self.max_stay_nights is not None and self.max_stay_nights < self.min_stay_nights:
            raise ValueError("max_stay_nights must be >= min_stay_nights")
        if self.image_url and not (self.image_url.startswith("https://") or self.image_url.startswith("/")):
            raise ValueError("image_url must be HTTPS or a site-relative path")
        if self.action_type == "GUEST_REQUEST":
            code = (self.request_code or "").strip().upper()
            if code not in REQUEST_LABELS:
                raise ValueError("GUEST_REQUEST requires a supported request_code")
            self.request_code = code
            self.external_url = None
            self.ai_prompt = None
        elif self.action_type == "EXTERNAL_URL":
            if not self.external_url or not self.external_url.startswith("https://"):
                raise ValueError("EXTERNAL_URL requires an HTTPS external_url")
            self.request_code = None
            self.ai_prompt = None
        else:
            if not self.ai_prompt or not self.ai_prompt.strip():
                raise ValueError("AI_PROMPT requires ai_prompt")
            self.request_code = None
            self.external_url = None
        self.code = self.code.strip().upper()
        return self


class CampaignToggle(BaseModel):
    is_active: bool


class GuestOfferEvent(BaseModel):
    event_type: Literal["CLICK", "REQUEST", "EXTERNAL_OPEN", "AI_PROMPT"]


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


def serialize_campaign(row, *, include_analytics: bool = False) -> dict[str, Any]:
    item = {
        "id": str(row["id"]),
        "code": row["code"],
        "title_ru": row["titleRu"],
        "title_kg": row["titleKg"],
        "title_en": row["titleEn"],
        "hook_ru": row["hookRu"],
        "hook_kg": row["hookKg"],
        "hook_en": row["hookEn"],
        "cta_ru": row["ctaRu"],
        "cta_kg": row["ctaKg"],
        "cta_en": row["ctaEn"],
        "image_url": row["imageUrl"],
        "action_type": row["actionType"],
        "request_code": row["requestCode"],
        "external_url": row["externalUrl"],
        "ai_prompt": row["aiPrompt"],
        "active_from": row["activeFrom"],
        "active_to": row["activeTo"],
        "min_adults": row["minAdults"],
        "min_children": row["minChildren"],
        "min_stay_nights": row["minStayNights"],
        "max_stay_nights": row["maxStayNights"],
        "priority": row["priority"],
        "sort_order": row["sortOrder"],
        "is_active": row["isActive"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
        "commercial_truth": "REQUEST_OR_HANDOFF_ONLY",
    }
    if include_analytics:
        item["analytics"] = {
            "clicks": int(row.get("clicks") or 0),
            "requests": int(row.get("requests") or 0),
            "external_opens": int(row.get("external_opens") or 0),
            "ai_prompts": int(row.get("ai_prompts") or 0),
        }
    return item


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, campaign_id: uuid.UUID, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'GuestOfferCampaign',$5,'GUEST_OFFER_CONTROL','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, str(campaign_id), json.dumps(payload, ensure_ascii=False, default=str),
    )


@admin_router.get("")
async def list_campaigns(request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        rows = await conn.fetch(
            '''SELECT c.*,
                 count(e.id) FILTER (WHERE e."eventType"='CLICK')::int AS clicks,
                 count(e.id) FILTER (WHERE e."eventType"='REQUEST')::int AS requests,
                 count(e.id) FILTER (WHERE e."eventType"='EXTERNAL_OPEN')::int AS external_opens,
                 count(e.id) FILTER (WHERE e."eventType"='AI_PROMPT')::int AS ai_prompts
               FROM guest_offer_campaigns c
               LEFT JOIN guest_offer_events e ON e."campaignId"=c.id
               WHERE c."propertyId"=$1
               GROUP BY c.id
               ORDER BY c."isActive" DESC,c.priority,c."sortOrder",c."updatedAt" DESC''',
            pid,
        )
    return {"items": [serialize_campaign(row, include_analytics=True) for row in rows]}


@admin_router.post("", status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignWrite, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            campaign_id = uuid.uuid4()
            try:
                await conn.execute(
                    '''INSERT INTO guest_offer_campaigns (
                         id,"propertyId",code,"titleRu","titleKg","titleEn","hookRu","hookKg","hookEn","ctaRu","ctaKg","ctaEn",
                         "imageUrl","actionType","requestCode","externalUrl","aiPrompt","activeFrom","activeTo","minAdults","minChildren",
                         "minStayNights","maxStayNights",priority,"sortOrder","isActive","createdById","createdAt","updatedAt"
                       ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,now(),now())''',
                    campaign_id, pid, payload.code, payload.title_ru, payload.title_kg, payload.title_en,
                    payload.hook_ru, payload.hook_kg, payload.hook_en, payload.cta_ru, payload.cta_kg, payload.cta_en,
                    payload.image_url, payload.action_type, payload.request_code, payload.external_url, payload.ai_prompt,
                    payload.active_from, payload.active_to, payload.min_adults, payload.min_children,
                    payload.min_stay_nights, payload.max_stay_nights, payload.priority, payload.sort_order,
                    payload.is_active, uuid.UUID(user["id"]),
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "23505":
                    raise HTTPException(status_code=409, detail={"code": "GUEST_OFFER_CODE_EXISTS"}) from exc
                raise
            await audit(conn, pid, user, "CREATE_GUEST_OFFER", campaign_id, payload.model_dump())
            row = await conn.fetchrow('SELECT * FROM guest_offer_campaigns WHERE id=$1', campaign_id)
    return serialize_campaign(row)


@admin_router.put("/{campaign_id}")
async def replace_campaign(campaign_id: uuid.UUID, payload: CampaignWrite, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            try:
                row = await conn.fetchrow(
                    '''UPDATE guest_offer_campaigns SET
                         code=$3,"titleRu"=$4,"titleKg"=$5,"titleEn"=$6,"hookRu"=$7,"hookKg"=$8,"hookEn"=$9,
                         "ctaRu"=$10,"ctaKg"=$11,"ctaEn"=$12,"imageUrl"=$13,"actionType"=$14,"requestCode"=$15,
                         "externalUrl"=$16,"aiPrompt"=$17,"activeFrom"=$18,"activeTo"=$19,"minAdults"=$20,"minChildren"=$21,
                         "minStayNights"=$22,"maxStayNights"=$23,priority=$24,"sortOrder"=$25,"isActive"=$26,"updatedAt"=now()
                       WHERE id=$1 AND "propertyId"=$2 RETURNING *''',
                    campaign_id, pid, payload.code, payload.title_ru, payload.title_kg, payload.title_en,
                    payload.hook_ru, payload.hook_kg, payload.hook_en, payload.cta_ru, payload.cta_kg, payload.cta_en,
                    payload.image_url, payload.action_type, payload.request_code, payload.external_url, payload.ai_prompt,
                    payload.active_from, payload.active_to, payload.min_adults, payload.min_children,
                    payload.min_stay_nights, payload.max_stay_nights, payload.priority, payload.sort_order, payload.is_active,
                )
            except Exception as exc:
                if getattr(exc, "sqlstate", None) == "23505":
                    raise HTTPException(status_code=409, detail={"code": "GUEST_OFFER_CODE_EXISTS"}) from exc
                raise
            if not row:
                raise HTTPException(status_code=404, detail="Guest offer campaign not found")
            await audit(conn, pid, user, "UPDATE_GUEST_OFFER", campaign_id, payload.model_dump())
    return serialize_campaign(row)


@admin_router.patch("/{campaign_id}/active")
async def toggle_campaign(campaign_id: uuid.UUID, payload: CampaignToggle, request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''UPDATE guest_offer_campaigns SET "isActive"=$3,"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2 RETURNING *''',
                campaign_id, pid, payload.is_active,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Guest offer campaign not found")
            await audit(conn, pid, user, "TOGGLE_GUEST_OFFER", campaign_id, {"is_active": payload.is_active})
    return serialize_campaign(row)


async def eligible_campaign(conn, campaign_id: uuid.UUID, property_id: uuid.UUID, adults: int, children: int, nights: int):
    return await conn.fetchrow(
        '''SELECT * FROM guest_offer_campaigns
           WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true
             AND ("activeFrom" IS NULL OR "activeFrom"<=now())
             AND ("activeTo" IS NULL OR "activeTo">now())
             AND "minAdults"<=$3 AND "minChildren"<=$4 AND "minStayNights"<=$5
             AND ("maxStayNights" IS NULL OR "maxStayNights">=$5)''',
        campaign_id, property_id, adults, children, nights,
    )


@guest_router.get("/rooms/{token}/offers")
async def guest_offers(token: str, request: Request, tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE)):
    async with request.app.state.db.acquire() as conn:
        qr, stay, _ = await authorized_context(conn, token, tc_guest_session)
        reservation = await conn.fetchrow(
            'SELECT adults,children,("checkOut"-"checkIn")::int AS nights FROM reservations WHERE id=$1 AND "propertyId"=$2',
            stay["reservation_id"], qr["propertyId"],
        )
        adults = int(reservation["adults"] if reservation else 1)
        children = int(reservation["children"] if reservation else 0)
        nights = int(reservation["nights"] if reservation else max(1, (stay["checkOut"] - stay["checkIn"]).days))
        rows = await conn.fetch(
            '''SELECT * FROM guest_offer_campaigns
               WHERE "propertyId"=$1 AND "isActive"=true
                 AND ("activeFrom" IS NULL OR "activeFrom"<=now())
                 AND ("activeTo" IS NULL OR "activeTo">now())
                 AND "minAdults"<=$2 AND "minChildren"<=$3 AND "minStayNights"<=$4
                 AND ("maxStayNights" IS NULL OR "maxStayNights">=$4)
               ORDER BY priority,"sortOrder","updatedAt" DESC LIMIT 12''',
            qr["propertyId"], adults, children, nights,
        )
    return {
        "items": [serialize_campaign(row) for row in rows],
        "audience": {"adults": adults, "children": children, "stay_nights": nights},
        "truth": "Offers are manager-configured handoffs only; they do not confirm price, availability, payment or service delivery.",
    }


@guest_router.post("/rooms/{token}/offers/{campaign_id}/events", status_code=status.HTTP_201_CREATED)
async def record_guest_offer_event(
    token: str,
    campaign_id: uuid.UUID,
    payload: GuestOfferEvent,
    request: Request,
    tc_guest_session: str | None = Cookie(default=None, alias=GUEST_COOKIE),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            qr, stay, session = await authorized_context(conn, token, tc_guest_session)
            reservation = await conn.fetchrow(
                'SELECT adults,children,("checkOut"-"checkIn")::int AS nights FROM reservations WHERE id=$1 AND "propertyId"=$2',
                stay["reservation_id"], qr["propertyId"],
            )
            adults = int(reservation["adults"] if reservation else 1)
            children = int(reservation["children"] if reservation else 0)
            nights = int(reservation["nights"] if reservation else max(1, (stay["checkOut"] - stay["checkIn"]).days))
            campaign = await eligible_campaign(conn, campaign_id, qr["propertyId"], adults, children, nights)
            if not campaign:
                raise HTTPException(status_code=404, detail={"code": "GUEST_OFFER_NOT_AVAILABLE"})

            allowed_for_action = {
                "GUEST_REQUEST": {"CLICK", "REQUEST"},
                "EXTERNAL_URL": {"CLICK", "EXTERNAL_OPEN"},
                "AI_PROMPT": {"CLICK", "AI_PROMPT"},
            }[campaign["actionType"]]
            if payload.event_type not in allowed_for_action:
                raise HTTPException(status_code=422, detail={"code": "GUEST_OFFER_EVENT_ACTION_MISMATCH"})

            event_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO guest_offer_events (
                     id,"propertyId","campaignId","guestId","stayId","eventType","guestSessionId",metadata,"createdAt"
                   ) VALUES ($1,$2,$3,$4,$5,$6,$7,
                     jsonb_build_object('room_id',$8::text,'reservation_id',$9::text),now())''',
                event_id, qr["propertyId"], campaign_id, stay["guestId"], stay["stayId"], payload.event_type,
                session["id"], str(qr["roomId"]), str(stay["reservation_id"]),
            )
            await conn.execute(
                '''INSERT INTO guest_history_events (
                     id,"propertyId","guestId","stayId","eventType",source,"payloadJson","occurredAt","createdAt"
                   ) VALUES ($1,$2,$3,$4,'GUEST_OFFER_EVENT','GUEST_MARKETPLACE',
                     jsonb_build_object('campaign_id',$5::text,'campaign_code',$6::text,'event_type',$7::text),now(),now())''',
                uuid.uuid4(), qr["propertyId"], stay["guestId"], stay["stayId"], str(campaign_id), campaign["code"], payload.event_type,
            )
    return {"id": str(event_id), "campaign_id": str(campaign_id), "event_type": payload.event_type}
