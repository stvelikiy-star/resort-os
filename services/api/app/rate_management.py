import json
import os
import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

RATE_PLAN_CODE = os.environ.get("RATE_PLAN_CODE", "DIRECT_2026_27")

router = APIRouter(prefix="/api/v1/admin/rates", tags=["admin-rates"])
manager_access = require_roles("OWNER", "MANAGER")

RateSaleStatus = Literal["OPEN", "CLOSED", "CONFIRM_REQUIRED"]


class RatePeriodCreate(BaseModel):
    room_type_id: uuid.UUID
    label: str = Field(min_length=2, max_length=120)
    valid_from: date
    valid_to: date
    price_kgs: int = Field(ge=0, le=10_000_000)
    meal_included: str = Field(default="NONE", min_length=1, max_length=80)
    sale_status: RateSaleStatus = "OPEN"
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_period(self):
        if self.valid_to < self.valid_from:
            raise ValueError("valid_to must be on or after valid_from")
        if self.sale_status == "OPEN" and self.price_kgs <= 0:
            raise ValueError("OPEN rate period must have a positive price")
        return self


class RatePeriodPatch(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    valid_from: date | None = None
    valid_to: date | None = None
    price_kgs: int | None = Field(default=None, ge=0, le=10_000_000)
    meal_included: str | None = Field(default=None, min_length=1, max_length=80)
    sale_status: RateSaleStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


async def _context(conn, property_code: str):
    row = await conn.fetchrow(
        '''
        SELECT p.id AS property_id,p.timezone,p.currency,
               rp.id AS rate_plan_id,rp.code AS rate_plan_code,rp.name AS rate_plan_name,rp.currency AS rate_currency
        FROM properties p
        JOIN rate_plans rp ON rp."propertyId"=p.id AND rp.code=$2
        WHERE p.code=$1
        ''',
        property_code,
        RATE_PLAN_CODE,
    )
    if not row:
        raise HTTPException(status_code=503, detail="Active rate plan is not loaded")
    return row


async def _ensure_room_type(conn, property_id: uuid.UUID, room_type_id: uuid.UUID):
    row = await conn.fetchrow(
        '''
        SELECT id,code,name,"capacityAdults","capacityChildren"
        FROM room_types
        WHERE id=$1 AND "propertyId"=$2
        ''',
        room_type_id,
        property_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Room type not found")
    return row


async def _lock_rate_lane(conn, rate_plan_id: uuid.UUID, room_type_id: uuid.UUID) -> None:
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
        f"rate:{rate_plan_id}:{room_type_id}",
    )


async def _ensure_no_overlap(
    conn,
    *,
    rate_plan_id: uuid.UUID,
    room_type_id: uuid.UUID,
    valid_from: date,
    valid_to: date,
    exclude_id: uuid.UUID | None = None,
):
    row = await conn.fetchrow(
        '''
        SELECT id,label,"validFrom","validTo"
        FROM rate_periods
        WHERE "ratePlanId"=$1
          AND "roomTypeId"=$2
          AND "validFrom" <= $4
          AND "validTo" >= $3
          AND ($5::uuid IS NULL OR id <> $5)
        ORDER BY "validFrom"
        LIMIT 1
        ''',
        rate_plan_id,
        room_type_id,
        valid_from,
        valid_to,
        exclude_id,
    )
    if row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RATE_PERIOD_OVERLAP",
                "period_id": str(row["id"]),
                "label": row["label"],
                "valid_from": row["validFrom"].isoformat(),
                "valid_to": row["validTo"].isoformat(),
            },
        )


def _period_payload(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "room_type_id": str(row["roomTypeId"]),
        "label": row["label"],
        "valid_from": row["validFrom"],
        "valid_to": row["validTo"],
        "price_kgs": int(row["priceKgs"]),
        "meal_included": row["mealIncluded"],
        "sale_status": row["saleStatus"],
        "notes": row["notes"],
        "updated_at": row["updatedAt"],
    }


async def _audit(
    conn,
    *,
    property_id: uuid.UUID,
    user: dict[str, Any],
    action: str,
    resource_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
):
    await conn.execute(
        '''
        INSERT INTO audit_logs (
          id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,
          "beforeJson","afterJson","createdAt"
        ) VALUES ($1,$2,'STAFF',$3,$4,'RatePeriod',$5,'RATE_MANAGEMENT','SUCCESS',$6::jsonb,$7::jsonb,now())
        ''',
        uuid.uuid4(),
        property_id,
        user["id"],
        action,
        resource_id,
        json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
    )


@router.get("")
async def rate_overview(
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        ctx = await _context(conn, user["property_code"])
        room_types = await conn.fetch(
            '''
            SELECT rt.id,rt.code,rt.name,rt."capacityAdults",rt."capacityChildren",
                   count(r.id)::int AS room_count
            FROM room_types rt
            LEFT JOIN rooms r ON r."roomTypeId"=rt.id AND r."propertyId"=rt."propertyId"
            WHERE rt."propertyId"=$1
            GROUP BY rt.id
            ORDER BY rt.name
            ''',
            ctx["property_id"],
        )
        periods = await conn.fetch(
            '''
            SELECT rp.id,rp."roomTypeId",rp.label,rp."validFrom",rp."validTo",rp."priceKgs",
                   rp."mealIncluded",rp."saleStatus"::text AS "saleStatus",rp.notes,rp."updatedAt"
            FROM rate_periods rp
            WHERE rp."ratePlanId"=$1
            ORDER BY rp."roomTypeId",rp."validFrom",rp."validTo"
            ''',
            ctx["rate_plan_id"],
        )

    return {
        "property_code": user["property_code"],
        "timezone": ctx["timezone"],
        "currency": ctx["rate_currency"] or ctx["currency"],
        "rate_plan": {
            "id": str(ctx["rate_plan_id"]),
            "code": ctx["rate_plan_code"],
            "name": ctx["rate_plan_name"],
        },
        "room_types": [
            {
                "id": str(row["id"]),
                "code": row["code"],
                "name": row["name"],
                "capacity_adults": row["capacityAdults"],
                "capacity_children": row["capacityChildren"],
                "room_count": row["room_count"],
            }
            for row in room_types
        ],
        "periods": [_period_payload(row) for row in periods],
        "rules": {
            "open_requires_positive_price": True,
            "overlap_allowed": False,
            "existing_reservation_totals_rewritten": False,
            "delete_supported": False,
        },
    }


@router.post("/periods", status_code=status.HTTP_201_CREATED)
async def create_rate_period(
    payload: RatePeriodCreate,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            ctx = await _context(conn, user["property_code"])
            await _ensure_room_type(conn, ctx["property_id"], payload.room_type_id)
            await _lock_rate_lane(conn, ctx["rate_plan_id"], payload.room_type_id)
            await _ensure_no_overlap(
                conn,
                rate_plan_id=ctx["rate_plan_id"],
                room_type_id=payload.room_type_id,
                valid_from=payload.valid_from,
                valid_to=payload.valid_to,
            )
            period_id = uuid.uuid4()
            row = await conn.fetchrow(
                '''
                INSERT INTO rate_periods (
                  id,"ratePlanId","roomTypeId",label,"validFrom","validTo","priceKgs",
                  "mealIncluded","saleStatus",notes,"createdAt","updatedAt"
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::"RateSaleStatus",$10,now(),now())
                RETURNING id,"roomTypeId",label,"validFrom","validTo","priceKgs",
                          "mealIncluded","saleStatus"::text AS "saleStatus",notes,"updatedAt"
                ''',
                period_id,
                ctx["rate_plan_id"],
                payload.room_type_id,
                payload.label.strip(),
                payload.valid_from,
                payload.valid_to,
                payload.price_kgs,
                payload.meal_included.strip(),
                payload.sale_status,
                payload.notes.strip() if payload.notes else None,
            )
            after = _period_payload(row)
            await _audit(
                conn,
                property_id=ctx["property_id"],
                user=user,
                action="CREATE_RATE_PERIOD",
                resource_id=str(period_id),
                before=None,
                after=after,
            )
    return after


@router.patch("/periods/{period_id}")
async def patch_rate_period(
    period_id: uuid.UUID,
    payload: RatePeriodPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            ctx = await _context(conn, user["property_code"])
            current = await conn.fetchrow(
                '''
                SELECT rp.id,rp."roomTypeId",rp.label,rp."validFrom",rp."validTo",rp."priceKgs",
                       rp."mealIncluded",rp."saleStatus"::text AS "saleStatus",rp.notes,rp."updatedAt"
                FROM rate_periods rp
                WHERE rp.id=$1 AND rp."ratePlanId"=$2
                FOR UPDATE
                ''',
                period_id,
                ctx["rate_plan_id"],
            )
            if not current:
                raise HTTPException(status_code=404, detail="Rate period not found")

            before = _period_payload(current)
            await _lock_rate_lane(conn, ctx["rate_plan_id"], current["roomTypeId"])
            valid_from = payload.valid_from if payload.valid_from is not None else current["validFrom"]
            valid_to = payload.valid_to if payload.valid_to is not None else current["validTo"]
            price_kgs = payload.price_kgs if payload.price_kgs is not None else int(current["priceKgs"])
            sale_status = payload.sale_status if payload.sale_status is not None else current["saleStatus"]
            label = payload.label.strip() if payload.label is not None else current["label"]
            meal_included = payload.meal_included.strip() if payload.meal_included is not None else current["mealIncluded"]
            notes = payload.notes.strip() if payload.notes else (None if payload.notes == "" else current["notes"])

            if valid_to < valid_from:
                raise HTTPException(status_code=422, detail="valid_to must be on or after valid_from")
            if sale_status == "OPEN" and price_kgs <= 0:
                raise HTTPException(status_code=422, detail="OPEN rate period must have a positive price")

            await _ensure_no_overlap(
                conn,
                rate_plan_id=ctx["rate_plan_id"],
                room_type_id=current["roomTypeId"],
                valid_from=valid_from,
                valid_to=valid_to,
                exclude_id=period_id,
            )

            row = await conn.fetchrow(
                '''
                UPDATE rate_periods
                SET label=$2,"validFrom"=$3,"validTo"=$4,"priceKgs"=$5,
                    "mealIncluded"=$6,"saleStatus"=$7::"RateSaleStatus",notes=$8,"updatedAt"=now()
                WHERE id=$1
                RETURNING id,"roomTypeId",label,"validFrom","validTo","priceKgs",
                          "mealIncluded","saleStatus"::text AS "saleStatus",notes,"updatedAt"
                ''',
                period_id,
                label,
                valid_from,
                valid_to,
                price_kgs,
                meal_included,
                sale_status,
                notes,
            )
            after = _period_payload(row)
            await _audit(
                conn,
                property_id=ctx["property_id"],
                user=user,
                action="UPDATE_RATE_PERIOD",
                resource_id=str(period_id),
                before=before,
                after=after,
            )
    return after
