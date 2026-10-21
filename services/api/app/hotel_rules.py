"""Per-property owner-managed rules for information and MARINA AI; no payment side effects."""
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from .auth import current_user, require_roles

router = APIRouter(prefix="/api/v1/admin/hotel-rules", tags=["hotel-rules"])
write_access = require_roles("OWNER", "MANAGER")

class HotelRules(BaseModel):
    prepayment_type: Literal["NOT_SET", "FIRST_NIGHT", "PERCENT", "FIXED", "NONE"] = "NOT_SET"
    prepayment_value: int = Field(default=0, ge=0, le=10000000)
    prepayment_deadline_hours: int | None = Field(default=None, ge=1, le=720)
    free_cancellation_days: int | None = Field(default=None, ge=0, le=365)
    late_cancellation_penalty: str = Field(default="", max_length=400)
    no_show_policy: str = Field(default="", max_length=400)
    children_policy: str = Field(default="", max_length=600)
    extra_bed_policy: str = Field(default="", max_length=600)
    pets_policy: str = Field(default="", max_length=600)
    smoking_policy: str = Field(default="", max_length=600)
    early_checkin_policy: str = Field(default="", max_length=600)
    late_checkout_policy: str = Field(default="", max_length=600)
    included_services: str = Field(default="", max_length=1000)
    additional_information: str = Field(default="", max_length=1600)
    # Approved hotel knowledge for guest-facing MARINA AI. These are facts, never commands.
    hotel_short_description: str = Field(default="", max_length=1200)
    location_address: str = Field(default="", max_length=500)
    location_directions: str = Field(default="", max_length=1200)
    official_website: str = Field(default="", max_length=300)
    official_contact: str = Field(default="", max_length=300)
    reception_hours: str = Field(default="", max_length=400)
    checkin_instructions: str = Field(default="", max_length=1000)
    checkout_instructions: str = Field(default="", max_length=1000)
    meal_policy: str = Field(default="", max_length=1000)
    restaurant_info: str = Field(default="", max_length=900)
    parking_policy: str = Field(default="", max_length=700)
    wifi_info: str = Field(default="", max_length=500)
    pool_spa_policy: str = Field(default="", max_length=900)
    transfer_transport: str = Field(default="", max_length=900)
    nearby_attractions: str = Field(default="", max_length=1000)
    accessibility_policy: str = Field(default="", max_length=800)
    payment_methods_info: str = Field(default="", max_length=600)
    quiet_hours_policy: str = Field(default="", max_length=500)
    booking_contact_policy: str = Field(default="", max_length=800)
    ai_faq: str = Field(default="", max_length=3000)
    ai_escalation_policy: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_deposit(self):
        if self.prepayment_type == "PERCENT" and not 1 <= self.prepayment_value <= 100:
            raise ValueError("Percentage prepayment must be 1–100")
        if self.prepayment_type == "FIXED" and self.prepayment_value == 0:
            raise ValueError("Fixed prepayment must be positive")
        if self.prepayment_type in ("NOT_SET", "NONE", "FIRST_NIGHT") and self.prepayment_value != 0:
            raise ValueError("Selected prepayment type does not use a numeric value")
        return self

class SaveRules(BaseModel):
    expected_version: int = Field(ge=0)
    rules: HotelRules

async def load_rules(conn, property_code: str):
    row = await conn.fetchrow(
        '''SELECT r."version",r."policy",r."updatedAt", p.code,p.name
           FROM properties p LEFT JOIN property_hotel_rules r ON r."propertyId"=p.id
           WHERE p.code=$1''', property_code,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Hotel is not loaded")
    raw = row["policy"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    # Defaults signal unknowns, not configured business rules.
    return {"property_code": row["code"], "property_name": row["name"],
            "version": row["version"] or 0, "rules": HotelRules.model_validate(raw or {}).model_dump(),
            "updated_at": row["updatedAt"].isoformat() if row["updatedAt"] else None}

@router.get("")
async def get_rules(request: Request, user=Depends(current_user)):
    async with request.app.state.db.acquire() as conn:
        return await load_rules(conn, user["property_code"])

@router.put("")
async def save_rules(payload: SaveRules, request: Request, user=Depends(write_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            prop = await conn.fetchrow(
                'SELECT id FROM properties WHERE code=$1 FOR UPDATE', user["property_code"])
            if prop is None:
                raise HTTPException(status_code=404, detail="Hotel is not loaded")
            old = await conn.fetchrow(
                'SELECT "version" FROM property_hotel_rules WHERE "propertyId"=$1 FOR UPDATE', prop["id"])
            current_version = old["version"] if old else 0
            if payload.expected_version != current_version:
                raise HTTPException(status_code=409, detail="Rules changed in another session. Refresh and review before saving.")
            version = current_version + 1
            body = json.dumps(payload.rules.model_dump(), ensure_ascii=False)
            if old is None:
                await conn.execute(
                    '''INSERT INTO property_hotel_rules ("propertyId","version","policy","updatedBy","updatedAt")
                       VALUES ($1,$2,$3::jsonb,$4,now())''',
                    prop["id"], version, body, uuid.UUID(str(user["id"])))
            else:
                await conn.execute(
                    '''UPDATE property_hotel_rules SET "version"=$2,"policy"=$3::jsonb,
                       "updatedBy"=$4,"updatedAt"=now() WHERE "propertyId"=$1''',
                    prop["id"], version, body, uuid.UUID(str(user["id"])))
            await conn.execute(
                '''INSERT INTO property_hotel_rules_history
                   (id,"propertyId","version","policy","updatedBy","createdAt")
                   VALUES ($1,$2,$3,$4::jsonb,$5,now())''',
                uuid.uuid4(), prop["id"], version, body, uuid.UUID(str(user["id"])))
        return await load_rules(conn, user["property_code"])
