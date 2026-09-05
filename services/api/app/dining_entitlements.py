import json
import uuid
from datetime import date, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from .auth import require_roles

router = APIRouter(prefix="/api/v1/dining", tags=["dining-entitlements"])
read_access = require_roles("OWNER", "MANAGER", "RECEPTION", "DINING_STAFF")
write_access = require_roles("OWNER", "MANAGER", "RECEPTION")
MealType = Literal["BREAKFAST", "LUNCH", "DINNER"]


class MealPlanUpsert(BaseModel):
    from_date: date
    through_date: date
    meals: list[MealType] = Field(min_length=1, max_length=3)
    adult_portions: int | None = Field(default=None, ge=0, le=50)
    child_portions: int | None = Field(default=None, ge=0, le=50)
    notes: str | None = Field(default=None, max_length=1000)
    replace_range: bool = False

    @model_validator(mode="after")
    def validate_range(self):
        if self.through_date < self.from_date:
            raise ValueError("through_date must be on or after from_date")
        if self.through_date - self.from_date > timedelta(days=62):
            raise ValueError("meal plan range cannot exceed 63 days")
        if len(set(self.meals)) != len(self.meals):
            raise ValueError("meal list contains duplicates")
        return self


class EntitlementPatch(BaseModel):
    adult_portions: int | None = Field(default=None, ge=0, le=50)
    child_portions: int | None = Field(default=None, ge=0, le=50)
    status: Literal["ACTIVE", "CANCELLED"] | None = None
    notes: str | None = Field(default=None, max_length=1000)


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, resource_id: str, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'DiningEntitlement',$5,'DINING_CORE','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, resource_id,
        json.dumps({**payload, "financial_effect": "NONE", "payment_effect": "NONE"}, ensure_ascii=False, default=str),
    )


def entitlement_item(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "stay_id": str(row["stayId"]),
        "reservation_id": str(row["reservationId"]),
        "guest_id": str(row["guestId"]),
        "service_date": row["serviceDate"],
        "meal_type": row["mealType"],
        "adult_portions": row["adultPortions"],
        "child_portions": row["childPortions"],
        "status": row["status"],
        "source": row["source"],
        "notes": row["notes"],
        "created_at": row["createdAt"],
        "updated_at": row["updatedAt"],
    }


@router.get("/stays/{stay_id}/entitlements")
async def stay_entitlements(
    stay_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        stay = await conn.fetchrow(
            '''SELECT s.id,r."bookingNumber",r."checkIn",r."checkOut",r.adults,r.children,
                      g."firstName",g."lastName",room.code AS room_code
               FROM stays s
               JOIN reservations r ON r.id=s."reservationId"
               JOIN guests g ON g.id=s."guestId"
               LEFT JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               LEFT JOIN rooms room ON room.id=ra."roomId"
               WHERE s.id=$1 AND s."propertyId"=$2''',
            stay_id, pid,
        )
        if not stay:
            raise HTTPException(status_code=404, detail="Stay not found")
        rows = await conn.fetch(
            '''SELECT id,"stayId","reservationId","guestId","serviceDate","mealType",
                      "adultPortions","childPortions",status,source,notes,"createdAt","updatedAt"
               FROM dining_entitlements WHERE "stayId"=$1 ORDER BY "serviceDate",
                 CASE "mealType" WHEN 'BREAKFAST' THEN 1 WHEN 'LUNCH' THEN 2 ELSE 3 END''',
            stay_id,
        )
    return {
        "stay": {
            "id": str(stay_id),
            "booking_number": stay["bookingNumber"],
            "check_in": stay["checkIn"],
            "check_out": stay["checkOut"],
            "adults": stay["adults"],
            "children": stay["children"],
            "guest_name": " ".join(part for part in [stay["firstName"], stay["lastName"]] if part) or "Гость",
            "room_code": stay["room_code"],
        },
        "items": [entitlement_item(row) for row in rows],
    }


@router.put("/stays/{stay_id}/meal-plan")
async def upsert_meal_plan(
    stay_id: uuid.UUID,
    payload: MealPlanUpsert,
    request: Request,
    user: dict[str, Any] = Depends(write_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            stay = await conn.fetchrow(
                '''SELECT s.id,s."reservationId",s."guestId",s.status::text AS stay_status,
                          r."checkIn",r."checkOut",r.adults,r.children,r.status::text AS reservation_status
                   FROM stays s JOIN reservations r ON r.id=s."reservationId"
                   WHERE s.id=$1 AND s."propertyId"=$2 FOR UPDATE''',
                stay_id, pid,
            )
            if not stay:
                raise HTTPException(status_code=404, detail="Stay not found")
            if stay["stay_status"] in {"CHECKED_OUT", "CANCELLED"} or stay["reservation_status"] in {"CHECKED_OUT", "CANCELLED", "NO_SHOW"}:
                raise HTTPException(status_code=409, detail={"code": "DINING_STAY_NOT_EDITABLE", "stay_status": stay["stay_status"]})
            if payload.from_date < stay["checkIn"] or payload.through_date > stay["checkOut"]:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "DINING_PLAN_OUTSIDE_STAY",
                        "check_in": str(stay["checkIn"]),
                        "check_out": str(stay["checkOut"]),
                    },
                )

            adults = stay["adults"] if payload.adult_portions is None else payload.adult_portions
            children = stay["children"] if payload.child_portions is None else payload.child_portions
            if adults + children <= 0:
                raise HTTPException(status_code=422, detail={"code": "DINING_PORTIONS_REQUIRED"})

            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'dining-plan:{stay_id}')
            if payload.replace_range:
                await conn.execute(
                    '''UPDATE dining_entitlements SET status='CANCELLED',"updatedAt"=now()
                       WHERE "stayId"=$1 AND "serviceDate" BETWEEN $2 AND $3''',
                    stay_id, payload.from_date, payload.through_date,
                )

            created_or_updated = 0
            day = payload.from_date
            while day <= payload.through_date:
                for meal in payload.meals:
                    await conn.execute(
                        '''INSERT INTO dining_entitlements (
                             id,"propertyId","stayId","reservationId","guestId","serviceDate","mealType",
                             "adultPortions","childPortions",status,source,notes,"createdById","createdAt","updatedAt"
                           ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'ACTIVE','MANAGER_PMS',$10,$11,now(),now())
                           ON CONFLICT ("stayId","serviceDate","mealType") DO UPDATE SET
                             "adultPortions"=EXCLUDED."adultPortions","childPortions"=EXCLUDED."childPortions",
                             status='ACTIVE',source='MANAGER_PMS',notes=EXCLUDED.notes,"createdById"=EXCLUDED."createdById","updatedAt"=now()''',
                        uuid.uuid4(), pid, stay_id, stay["reservationId"], stay["guestId"], day, meal,
                        adults, children, payload.notes, uuid.UUID(user["id"]),
                    )
                    created_or_updated += 1
                day += timedelta(days=1)

            await audit(
                conn, pid, user, "UPSERT_DINING_MEAL_PLAN", str(stay_id),
                {
                    "stay_id": str(stay_id), "reservation_id": str(stay["reservationId"]),
                    "from_date": payload.from_date, "through_date": payload.through_date,
                    "meals": payload.meals, "adult_portions": adults, "child_portions": children,
                    "replace_range": payload.replace_range,
                },
            )
    return {
        "stay_id": str(stay_id),
        "updated_items": created_or_updated,
        "from_date": payload.from_date,
        "through_date": payload.through_date,
        "meals": payload.meals,
        "adult_portions": adults,
        "child_portions": children,
        "truth": "Dining entitlement only; no Payment or accommodation total was changed.",
    }


@router.patch("/entitlements/{entitlement_id}")
async def patch_entitlement(
    entitlement_id: uuid.UUID,
    payload: EntitlementPatch,
    request: Request,
    user: dict[str, Any] = Depends(write_access),
):
    if all(value is None for value in [payload.adult_portions, payload.child_portions, payload.status, payload.notes]):
        raise HTTPException(status_code=422, detail="No change supplied")
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            current = await conn.fetchrow(
                '''SELECT id,"adultPortions","childPortions",status,notes FROM dining_entitlements
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                entitlement_id, pid,
            )
            if not current:
                raise HTTPException(status_code=404, detail="Dining entitlement not found")
            adults = current["adultPortions"] if payload.adult_portions is None else payload.adult_portions
            children = current["childPortions"] if payload.child_portions is None else payload.child_portions
            status_value = current["status"] if payload.status is None else payload.status
            if status_value == "ACTIVE" and adults + children <= 0:
                raise HTTPException(status_code=422, detail={"code": "DINING_PORTIONS_REQUIRED"})
            row = await conn.fetchrow(
                '''UPDATE dining_entitlements SET
                     "adultPortions"=$3,"childPortions"=$4,status=$5,notes=COALESCE($6,notes),"updatedAt"=now()
                   WHERE id=$1 AND "propertyId"=$2
                   RETURNING id,"stayId","reservationId","guestId","serviceDate","mealType",
                     "adultPortions","childPortions",status,source,notes,"createdAt","updatedAt"''',
                entitlement_id, pid, adults, children, status_value, payload.notes,
            )
            await audit(conn, pid, user, "PATCH_DINING_ENTITLEMENT", str(entitlement_id), entitlement_item(row))
    return entitlement_item(row)


@router.get("/production")
async def production(
    request: Request,
    from_date: date | None = Query(default=None),
    through_date: date | None = Query(default=None),
    user: dict[str, Any] = Depends(read_access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        local_today = await conn.fetchval(
            '''SELECT (now() AT TIME ZONE COALESCE(timezone,'Asia/Bishkek'))::date FROM properties WHERE id=$1''', pid,
        )
        start = from_date or local_today
        end = through_date or (start + timedelta(days=6))
        if end < start or end - start > timedelta(days=31):
            raise HTTPException(status_code=422, detail="Production range must be 1-32 days")
        rows = await conn.fetch(
            '''SELECT e.id,e."serviceDate",e."mealType",e."adultPortions",e."childPortions",e.notes,
                      e."stayId",e."reservationId",r."bookingNumber",r."checkIn",r."checkOut",
                      g."firstName",g."lastName",room.code AS room_code
               FROM dining_entitlements e
               JOIN reservations r ON r.id=e."reservationId"
               JOIN stays s ON s.id=e."stayId"
               JOIN guests g ON g.id=e."guestId"
               LEFT JOIN room_assignments ra ON ra."stayId"=s.id AND ra."endedAt" IS NULL
               LEFT JOIN rooms room ON room.id=ra."roomId"
               WHERE e."propertyId"=$1 AND e.status='ACTIVE' AND e."serviceDate" BETWEEN $2 AND $3
                 AND s.status IN ('PENDING','ACTIVE')
               ORDER BY e."serviceDate",CASE e."mealType" WHEN 'BREAKFAST' THEN 1 WHEN 'LUNCH' THEN 2 ELSE 3 END,
                        room.code NULLS LAST,r."bookingNumber"''',
            pid, start, end,
        )

        by_key: dict[tuple[date, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["serviceDate"], row["mealType"])
            bucket = by_key.setdefault(key, {
                "service_date": row["serviceDate"], "meal_type": row["mealType"],
                "adult_portions": 0, "child_portions": 0, "total_portions": 0,
                "guests": [],
            })
            adult = int(row["adultPortions"])
            child = int(row["childPortions"])
            bucket["adult_portions"] += adult
            bucket["child_portions"] += child
            bucket["total_portions"] += adult + child
            bucket["guests"].append({
                "entitlement_id": str(row["id"]),
                "stay_id": str(row["stayId"]),
                "reservation_id": str(row["reservationId"]),
                "booking_number": row["bookingNumber"],
                "guest_name": " ".join(part for part in [row["firstName"], row["lastName"]] if part) or "Гость",
                "room_code": row["room_code"],
                "adult_portions": adult,
                "child_portions": child,
                "check_in": row["checkIn"],
                "check_out": row["checkOut"],
                "departure_day": row["serviceDate"] == row["checkOut"],
                "notes": row["notes"],
            })

    days = []
    day = start
    while day <= end:
        meals = []
        for meal in ["BREAKFAST", "LUNCH", "DINNER"]:
            meals.append(by_key.get((day, meal), {
                "service_date": day, "meal_type": meal,
                "adult_portions": 0, "child_portions": 0, "total_portions": 0, "guests": [],
            }))
        days.append({"service_date": day, "meals": meals})
        day += timedelta(days=1)

    return {
        "from_date": start,
        "through_date": end,
        "days": days,
        "truth": "Production counts are derived from explicit active dining entitlements only.",
    }
