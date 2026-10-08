import json
import os
import re
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles, router as auth_router, trusted_property_id
from .db import lifespan

PROPERTY_CODE = os.environ.get("PROPERTY_CODE", "THREE_CROWNS")
RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "DIRECT_2026_27")
MARKETING_POLICY_VERSION = os.environ.get("MARKETING_POLICY_VERSION", "2026-09-12")
MARKETING_CHANNELS = {"WHATSAPP", "EMAIL", "SMS", "TELEGRAM", "PHONE"}

app = FastAPI(
    title="MARINA SMART Core API",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins = [
    item.strip()
    for item in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
app.include_router(auth_router)


class ReservationRequestCreate(BaseModel):
    guest_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = Field(default=None, max_length=200)
    check_in: date
    check_out: date
    adults: int = Field(ge=1, le=20)
    children: int = Field(default=0, ge=0, le=20)
    room_type_code: str | None = None
    source: str = Field(default="WEB", max_length=60)
    notes: str | None = Field(default=None, max_length=2000)
    marketing_opt_in: bool = False
    marketing_channels: list[str] = Field(default_factory=list, max_length=5)
    marketing_policy_version: str = Field(default=MARKETING_POLICY_VERSION, min_length=2, max_length=80)
    utm_source: str | None = Field(default=None, max_length=200)
    utm_medium: str | None = Field(default=None, max_length=200)
    utm_campaign: str | None = Field(default=None, max_length=240)
    utm_content: str | None = Field(default=None, max_length=240)
    utm_term: str | None = Field(default=None, max_length=240)
    landing_page: str | None = Field(default=None, max_length=1000)
    referrer: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_request(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        normalized_channels = []
        for raw in self.marketing_channels:
            channel = raw.strip().upper()
            if channel not in MARKETING_CHANNELS:
                raise ValueError(f"unsupported marketing channel: {raw}")
            if channel not in normalized_channels:
                normalized_channels.append(channel)
        self.marketing_channels = normalized_channels
        if self.marketing_opt_in and not self.marketing_channels:
            raise ValueError("marketing_channels are required when marketing_opt_in=true")
        if "EMAIL" in self.marketing_channels and not self.email:
            raise ValueError("email is required for EMAIL marketing consent")
        return self


async def get_property_id(conn) -> uuid.UUID:
    property_id = await conn.fetchval(
        'SELECT id FROM properties WHERE code = $1', PROPERTY_CODE
    )
    if not property_id:
        raise HTTPException(status_code=503, detail="Property seed is not loaded")
    return property_id


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    return f"+{digits}" if digits else value.strip()


def nights_between(check_in: date, check_out: date) -> list[date]:
    return [check_in + timedelta(days=i) for i in range((check_out - check_in).days)]


async def price_room_type(conn, room_type_id, check_in: date, check_out: date) -> dict[str, Any]:
    nights = nights_between(check_in, check_out)
    if not nights:
        return {"sellable": False, "total_kgs": None, "reason": "INVALID_DATE_RANGE", "nights": []}

    rows = await conn.fetch(
        '''
        SELECT rp."validFrom", rp."validTo", rp."priceKgs", rp."mealIncluded",
               rp."saleStatus", rp.label
        FROM rate_periods rp
        JOIN rate_plans p ON p.id = rp."ratePlanId"
        WHERE rp."roomTypeId" = $1
          AND p.code = $2
          AND rp."validFrom" <= $4
          AND rp."validTo" >= $3
        ORDER BY rp."validFrom"
        ''',
        room_type_id,
        RATE_PLAN_CODE,
        check_in,
        check_out - timedelta(days=1),
    )

    nightly: list[dict[str, Any]] = []
    total = 0
    sellable = True
    reason = None

    for night in nights:
        matches = [r for r in rows if r["validFrom"] <= night <= r["validTo"]]
        if len(matches) > 1:
            sellable = False
            reason = "RATE_OVERLAP"
            nightly.append({"date": night, "price_kgs": None, "status": "AMBIGUOUS"})
            continue
        matched = matches[0] if matches else None
        if not matched:
            sellable = False
            reason = "RATE_MISSING"
            nightly.append({"date": night, "price_kgs": None, "status": "MISSING"})
            continue

        rate_status = str(matched["saleStatus"])
        price = matched["priceKgs"]
        if rate_status != "OPEN" or price <= 0:
            sellable = False
            reason = "RATE_REQUIRES_CONFIRMATION" if rate_status == "CONFIRM_REQUIRED" else "RATE_CLOSED"

        if price > 0:
            total += price

        nightly.append(
            {
                "date": night,
                "price_kgs": price,
                "meal_included": matched["mealIncluded"],
                "status": rate_status,
                "period": matched["label"],
            }
        )

    return {
        "sellable": sellable,
        "total_kgs": total if sellable else None,
        "reason": reason,
        "nights": nightly,
    }


@app.get("/health")
async def health(request: Request):
    async with request.app.state.db.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "service": "marina-smart-core"}


@app.get("/api/v1/booking/check-availability")
async def check_availability(
    request: Request,
    check_in: date,
    check_out: date,
    adults: int = Query(ge=1, le=20),
    children: int = Query(default=0, ge=0, le=20),
    room_type_code: str | None = None,
):
    if check_out <= check_in:
        raise HTTPException(status_code=422, detail="check_out must be after check_in")
    if (check_out - check_in).days > 60:
        raise HTTPException(status_code=422, detail="maximum stay search is 60 nights")

    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        rows = await conn.fetch(
            '''
            SELECT rt.id, rt.code, rt.name, rt."capacityAdults", rt."capacityChildren", rt."areaLabel",
                   r.id AS room_id, r.code AS room_code, r."buildingOrZone", r."floorLabel",
                   r."bedConfiguration", r."operationalState", r.notes AS room_notes
            FROM room_types rt
            JOIN rooms r ON r."roomTypeId" = rt.id
            WHERE rt."propertyId" = $1
              AND (
                  $7::boolean = true
                  OR (
                      rt."capacityAdults" >= $2
                      AND (
                          $3::int = 0
                          OR (rt."capacityChildren" IS NOT NULL AND rt."capacityChildren" >= $3)
                      )
                  )
              )
              AND ($4::text IS NULL OR rt.code = $4)
              AND r."operationalState" <> 'TECH_BLOCK'
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_blocks ib
                  WHERE ib."roomId" = r.id
                    AND ib.active = true
                    AND daterange(ib."startDate", ib."endDate", '[)')
                        && daterange($5::date, $6::date, '[)')
              )
            ORDER BY rt.name, r.code
            ''',
            property_id,
            adults,
            children,
            room_type_code,
            check_in,
            check_out,
            PROPERTY_CODE == "AK_BERMET_TEST",
        )

        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            room_max_capacity = None
            if PROPERTY_CODE == "AK_BERMET_TEST":
                try:
                    metadata = json.loads(row["room_notes"] or "{}")
                    room_max_capacity = int(metadata["max_capacity"])
                except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                    continue
                if adults + children > room_max_capacity:
                    continue

            key = str(row["id"])
            if key not in grouped:
                grouped[key] = {
                    "room_type_id": key,
                    "room_type_code": row["code"],
                    "room_type_name": row["name"],
                    "capacity_adults": row["capacityAdults"],
                    "capacity_children": row["capacityChildren"],
                    "children_capacity_confirmed": row["capacityChildren"] is not None,
                    "area": row["areaLabel"],
                    "available_rooms": [],
                }
            grouped[key]["available_rooms"].append(
                {
                    "id": str(row["room_id"]),
                    "code": row["room_code"],
                    "building_or_zone": row["buildingOrZone"],
                    "floor": row["floorLabel"],
                    "beds_raw": row["bedConfiguration"],
                    "operational_state": str(row["operationalState"]),
                    "max_capacity": room_max_capacity,
                }
            )

        result = []
        for item in grouped.values():
            pricing = await price_room_type(conn, item["room_type_id"], check_in, check_out)
            item["available_count"] = len(item["available_rooms"])
            manager_confirmation_required = (
                PROPERTY_CODE == "AK_BERMET_TEST"
                and (children > 0 or adults + children > int(item["capacity_adults"]))
            )
            pricing["manager_confirmation_required"] = manager_confirmation_required
            if manager_confirmation_required:
                pricing["confirmation_reason"] = (
                    "AK_BERMET_CHILD_OR_EXTRA_PLACE_PRICING_REQUIRES_MANAGER_CONFIRMATION"
                )
            item["pricing"] = pricing
            item["children_requested"] = children
            result.append(item)

    return {
        "property": PROPERTY_CODE,
        "check_in": check_in,
        "check_out": check_out,
        "nights": (check_out - check_in).days,
        "adults": adults,
        "children": children,
        "children_capacity_policy": (
            "AK_BERMET_CONFIRMED_ROOM_MAX_CAPACITY"
            if PROPERTY_CODE == "AK_BERMET_TEST"
            else "CONFIRMED_CAPACITY_REQUIRED_WHEN_CHILDREN_REQUESTED"
        ),
        "results": result,
        "rule": "Availability is informational until a paid reservation is created. An unpaid request is not a reservation.",
    }


@app.post("/api/v1/booking/requests", status_code=201)
async def create_reservation_request(payload: ReservationRequestCreate, request: Request):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await get_property_id(conn)
            room_type_id = None
            if payload.room_type_code:
                room_type_id = await conn.fetchval(
                    'SELECT id FROM room_types WHERE "propertyId" = $1 AND code = $2',
                    property_id,
                    payload.room_type_code,
                )
                if not room_type_id:
                    raise HTTPException(status_code=422, detail="Unknown room_type_code")

            request_id = uuid.uuid4()
            await conn.execute(
                '''
                INSERT INTO reservation_requests (
                    id, "propertyId", status, source, "guestName", phone, email,
                    "checkIn", "checkOut", adults, children, "desiredRoomTypeId", notes,
                    "utmSource", "utmMedium", "utmCampaign", "utmContent", "utmTerm", "landingPage", referrer,
                    "createdAt", "updatedAt"
                ) VALUES (
                    $1, $2, 'NEW', $3, $4, $5, $6,
                    $7, $8, $9, $10, $11, $12,
                    $13, $14, $15, $16, $17, $18, $19,
                    now(), now()
                )
                ''',
                request_id,
                property_id,
                payload.source,
                payload.guest_name,
                payload.phone,
                payload.email,
                payload.check_in,
                payload.check_out,
                payload.adults,
                payload.children,
                room_type_id,
                payload.notes,
                payload.utm_source,
                payload.utm_medium,
                payload.utm_campaign,
                payload.utm_content,
                payload.utm_term,
                payload.landing_page,
                payload.referrer,
            )

            if payload.marketing_opt_in:
                for channel in payload.marketing_channels:
                    if channel == "EMAIL":
                        contact_key = (payload.email or "").strip().lower()
                    else:
                        contact_key = normalize_phone(payload.phone)
                    await conn.execute(
                        '''
                        INSERT INTO marketing_consents (
                          id,"propertyId","requestId","contactKey",channel,status,source,"policyVersion",proof,"occurredAt","createdAt"
                        ) VALUES ($1,$2,$3,$4,$5,'OPTED_IN','PUBLIC_BOOKING',$6,'booking_form_checkbox',now(),now())
                        ''',
                        uuid.uuid4(),
                        property_id,
                        request_id,
                        contact_key,
                        channel,
                        payload.marketing_policy_version,
                    )

            audit_payload = payload.model_dump(mode="json")
            audit_payload["marketing_channels"] = payload.marketing_channels if payload.marketing_opt_in else []
            await conn.execute(
                '''
                INSERT INTO audit_logs (
                    id, "propertyId", "actorType", action, resource, "resourceId",
                    source, result, "afterJson", "createdAt"
                ) VALUES ($1, $2, 'GUEST', 'CREATE', 'ReservationRequest', $3, $4, 'SUCCESS', $5::jsonb, now())
                ''',
                uuid.uuid4(),
                property_id,
                str(request_id),
                payload.source,
                __import__("json").dumps(audit_payload, ensure_ascii=False),
            )

    return {
        "id": str(request_id),
        "status": "NEW",
        "is_reservation": False,
        "marketing_consent_recorded": payload.marketing_opt_in,
        "message": "Request received. Without confirmed prepayment this is not an active reservation.",
    }


@app.get("/api/v1/pms/grid")
async def pms_grid(
    request: Request,
    start: date,
    end: date,
    room_type_code: str | None = None,
    operational_state: str | None = None,
    _user: dict[str, Any] = Depends(require_roles("OWNER", "MANAGER", "RECEPTION", "AGENT")),
):
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    if (end - start).days > 62:
        raise HTTPException(status_code=422, detail="grid window is limited to 62 days")

    linked_agent_id = None
    async with request.app.state.db.acquire() as conn:
        property_id = await trusted_property_id(conn, _user)
        if _user["role"] == "AGENT":
            linked_agent_id = await conn.fetchval(
                'SELECT "bookingAgentId" FROM staff_users WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true',
                _user["id"],
                property_id,
            )
            if not linked_agent_id:
                raise HTTPException(status_code=403, detail="Agent account is not linked to an active booking agent")
        rooms = await conn.fetch(
            '''
            SELECT r.id, r.code, r.name, r."buildingOrZone", r."floorLabel",
                   r."bedConfiguration", r."operationalState",
                   rt.code AS room_type_code, rt.name AS room_type_name
            FROM rooms r
            JOIN room_types rt ON rt.id = r."roomTypeId"
            WHERE r."propertyId" = $1
              AND ($2::text IS NULL OR rt.code = $2)
              AND ($3::text IS NULL OR r."operationalState"::text = $3)
            ORDER BY rt.name, r.code
            ''',
            property_id,
            room_type_code,
            operational_state,
        )

        blocks = await conn.fetch(
            '''
            SELECT ib.id, ib."roomId", ib."blockType", ib."startDate", ib."endDate", ib.reason,
                   res.id AS reservation_id, res."bookingNumber", res.status AS reservation_status,
                   res."agentId" AS reservation_agent_id,
                   g."firstName", g."lastName", g.phone
            FROM inventory_blocks ib
            JOIN rooms r ON r.id = ib."roomId"
            LEFT JOIN reservations res ON res.id = ib."reservationId"
            LEFT JOIN guests g ON g.id = res."primaryGuestId"
            WHERE r."propertyId" = $1
              AND ib.active = true
              AND daterange(ib."startDate", ib."endDate", '[)') && daterange($2::date, $3::date, '[)')
            ORDER BY ib."startDate"
            ''',
            property_id,
            start,
            end,
        )

    blocks_by_room: dict[str, list[dict[str, Any]]] = {}
    for block in blocks:
        room_id = str(block["roomId"])
        own_agent_booking = (
            _user["role"] != "AGENT"
            or (linked_agent_id is not None and block["reservation_agent_id"] == linked_agent_id)
        )
        guest_name = (
            " ".join(filter(None, [block["firstName"], block["lastName"]])) or None
        ) if own_agent_booking else None
        blocks_by_room.setdefault(room_id, []).append(
            {
                "id": str(block["id"]),
                "type": str(block["blockType"]),
                "start": block["startDate"],
                "end": block["endDate"],
                "reason": block["reason"] if _user["role"] != "AGENT" else None,
                "reservation_id": str(block["reservation_id"]) if block["reservation_id"] and own_agent_booking else None,
                "booking_number": block["bookingNumber"] if own_agent_booking else None,
                "reservation_status": str(block["reservation_status"]) if block["reservation_status"] else None,
                "guest_name": guest_name,
                "guest_phone": block["phone"] if own_agent_booking else None,
            }
        )

    return {
        "property": PROPERTY_CODE,
        "start": start,
        "end": end,
        "rooms": [
            {
                "id": str(room["id"]),
                "code": room["code"],
                "name": room["name"],
                "room_type_code": room["room_type_code"],
                "room_type_name": room["room_type_name"],
                "building_or_zone": room["buildingOrZone"],
                "floor": room["floorLabel"],
                "beds_raw": room["bedConfiguration"],
                "operational_state": str(room["operationalState"]),
                "blocks": blocks_by_room.get(str(room["id"]), []),
            }
            for room in rooms
        ],
    }
