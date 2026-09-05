import uuid
from datetime import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/guest-service-settings", tags=["guest-service-settings"])
manager_access = require_roles("OWNER", "MANAGER")


class GuestServiceSettingsPatch(BaseModel):
    breakfast_start: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    lunch_start: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    dinner_start: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    meal_order_cutoff_minutes: int | None = Field(default=None, ge=0, le=360)
    room_delivery_enabled: bool | None = None
    room_delivery_fee_kgs: int | None = Field(default=None, ge=0, le=100_000)
    scheduled_housekeeping_interval_days: int | None = Field(default=None, ge=1, le=30)
    scheduled_linen_change_included: bool | None = None
    on_demand_housekeeping_price_kgs: int | None = Field(default=None, ge=0, le=100_000)
    on_demand_linen_price_kgs: int | None = Field(default=None, ge=0, le=100_000)


async def _property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def ensure_settings(conn, property_id: uuid.UUID):
    await conn.execute(
        '''INSERT INTO property_guest_service_settings (
             id,"propertyId","mealOrderCutoffMinutes","roomDeliveryEnabled","roomDeliveryFeeKgs",
             "scheduledHousekeepingIntervalDays","scheduledLinenChangeIncluded","createdAt","updatedAt"
           ) VALUES ($1,$2,60,true,200,3,true,now(),now())
           ON CONFLICT ("propertyId") DO NOTHING''',
        uuid.uuid4(), property_id,
    )
    return await conn.fetchrow(
        '''SELECT id,"propertyId","breakfastStart","lunchStart","dinnerStart","mealOrderCutoffMinutes",
                  "roomDeliveryEnabled","roomDeliveryFeeKgs","scheduledHousekeepingIntervalDays",
                  "scheduledLinenChangeIncluded","onDemandHousekeepingPriceKgs","onDemandLinenPriceKgs","updatedAt"
           FROM property_guest_service_settings WHERE "propertyId"=$1''',
        property_id,
    )


async def load_settings(conn, property_id: uuid.UUID) -> dict[str, Any]:
    row = await ensure_settings(conn, property_id)
    return {
        "breakfast_start": row["breakfastStart"],
        "lunch_start": row["lunchStart"],
        "dinner_start": row["dinnerStart"],
        "meal_order_cutoff_minutes": int(row["mealOrderCutoffMinutes"]),
        "room_delivery_enabled": bool(row["roomDeliveryEnabled"]),
        "room_delivery_fee_kgs": int(row["roomDeliveryFeeKgs"]),
        "scheduled_housekeeping_interval_days": int(row["scheduledHousekeepingIntervalDays"]),
        "scheduled_linen_change_included": bool(row["scheduledLinenChangeIncluded"]),
        "on_demand_housekeeping_price_kgs": row["onDemandHousekeepingPriceKgs"],
        "on_demand_linen_price_kgs": row["onDemandLinenPriceKgs"],
        "updated_at": row["updatedAt"],
    }


def _time_string(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def serialize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        **settings,
        "breakfast_start": _time_string(settings["breakfast_start"]),
        "lunch_start": _time_string(settings["lunch_start"]),
        "dinner_start": _time_string(settings["dinner_start"]),
        "housekeeping_prices_configured": settings["on_demand_housekeeping_price_kgs"] is not None and settings["on_demand_linen_price_kgs"] is not None,
        "meal_times_configured": all(settings[key] is not None for key in ("breakfast_start", "lunch_start", "dinner_start")),
    }


@router.get("")
async def get_guest_service_settings(request: Request, user: dict[str, Any] = Depends(manager_access)):
    async with request.app.state.db.acquire() as conn:
        property_id = await _property_id(conn, user["property_code"])
        settings = await load_settings(conn, property_id)
    return serialize_settings(settings)


@router.patch("")
async def patch_guest_service_settings(
    payload: GuestServiceSettingsPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            property_id = await _property_id(conn, user["property_code"])
            current = await load_settings(conn, property_id)
            supplied = payload.model_fields_set

            def chosen(field: str, current_key: str):
                return getattr(payload, field) if field in supplied else current[current_key]

            def parsed_time(field: str, current_key: str):
                value = chosen(field, current_key)
                if isinstance(value, time) or value is None:
                    return value
                return time.fromisoformat(value)

            values = {
                "breakfast_start": parsed_time("breakfast_start", "breakfast_start"),
                "lunch_start": parsed_time("lunch_start", "lunch_start"),
                "dinner_start": parsed_time("dinner_start", "dinner_start"),
                "meal_order_cutoff_minutes": chosen("meal_order_cutoff_minutes", "meal_order_cutoff_minutes"),
                "room_delivery_enabled": chosen("room_delivery_enabled", "room_delivery_enabled"),
                "room_delivery_fee_kgs": chosen("room_delivery_fee_kgs", "room_delivery_fee_kgs"),
                "scheduled_housekeeping_interval_days": chosen("scheduled_housekeeping_interval_days", "scheduled_housekeeping_interval_days"),
                "scheduled_linen_change_included": chosen("scheduled_linen_change_included", "scheduled_linen_change_included"),
                "on_demand_housekeeping_price_kgs": chosen("on_demand_housekeeping_price_kgs", "on_demand_housekeeping_price_kgs"),
                "on_demand_linen_price_kgs": chosen("on_demand_linen_price_kgs", "on_demand_linen_price_kgs"),
            }

            await conn.execute(
                '''UPDATE property_guest_service_settings SET
                     "breakfastStart"=$2,"lunchStart"=$3,"dinnerStart"=$4,"mealOrderCutoffMinutes"=$5,
                     "roomDeliveryEnabled"=$6,"roomDeliveryFeeKgs"=$7,"scheduledHousekeepingIntervalDays"=$8,
                     "scheduledLinenChangeIncluded"=$9,"onDemandHousekeepingPriceKgs"=$10,
                     "onDemandLinenPriceKgs"=$11,"updatedAt"=now()
                   WHERE "propertyId"=$1''',
                property_id,
                values["breakfast_start"], values["lunch_start"], values["dinner_start"],
                values["meal_order_cutoff_minutes"], values["room_delivery_enabled"], values["room_delivery_fee_kgs"],
                values["scheduled_housekeeping_interval_days"], values["scheduled_linen_change_included"],
                values["on_demand_housekeeping_price_kgs"], values["on_demand_linen_price_kgs"],
            )
            await conn.execute(
                '''INSERT INTO audit_logs (
                     id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
                   ) VALUES ($1,$2,'STAFF',$3,'UPDATE_GUEST_SERVICE_SETTINGS','PropertyGuestServiceSettings',$4,
                     'PMS_SETTINGS','SUCCESS',jsonb_build_object(
                       'meal_order_cutoff_minutes',$5::int,'room_delivery_fee_kgs',$6::int,
                       'scheduled_housekeeping_interval_days',$7::int,'meal_times_configured',$8::boolean,
                       'on_demand_housekeeping_price_kgs',$9::int,'on_demand_linen_price_kgs',$10::int
                     ),now())''',
                uuid.uuid4(), property_id, user["id"], str(property_id),
                values["meal_order_cutoff_minutes"], values["room_delivery_fee_kgs"],
                values["scheduled_housekeeping_interval_days"],
                all(values[key] is not None for key in ("breakfast_start", "lunch_start", "dinner_start")),
                values["on_demand_housekeeping_price_kgs"], values["on_demand_linen_price_kgs"],
            )
            updated = await load_settings(conn, property_id)
    return serialize_settings(updated)
