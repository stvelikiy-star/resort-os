import json
import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/folio", tags=["guest-folio"])
access = require_roles("OWNER", "MANAGER", "RECEPTION")
manager_access = require_roles("OWNER", "MANAGER")


class ManualChargeCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=2, max_length=500)
    amount_kgs: int = Field(gt=0, le=10_000_000)
    service_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ChargeStatusPatch(BaseModel):
    status: Literal["WAIVED", "VOID"]
    reason: str = Field(min_length=2, max_length=1000)


async def property_id(conn, property_code: str) -> uuid.UUID:
    value = await conn.fetchval('SELECT id FROM properties WHERE code=$1', property_code)
    if not value:
        raise HTTPException(status_code=503, detail="Property not loaded")
    return value


async def audit(conn, pid: uuid.UUID, user: dict[str, Any], action: str, resource_id: str, payload: dict[str, Any]):
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,'STAFF',$3,$4,'GuestFolioCharge',$5,'FOLIO','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), pid, user["id"], action, resource_id,
        json.dumps(payload, ensure_ascii=False, default=str),
    )


async def ensure_kitchen_order_charge(conn, order_id: uuid.UUID, *, actor_type: str, actor_id: str | None) -> uuid.UUID | None:
    """Create the commercial receivable for a stay-linked kitchen order, idempotently.

    This never creates a Payment. Payment means money was actually received. A folio
    charge means the guest owes the amount until finance settles/waives it.
    """
    await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))', f'folio:kitchen:{order_id}')
    order = await conn.fetchrow(
        '''SELECT o.id,o."propertyId",o."reservationId",o."stayId",o."orderNumber",o."totalKgs",
                  o."mealType",o."deliveryToRoom",o."deliveryFeeKgs",o."folioChargeId",
                  s."guestId"
           FROM kitchen_orders o
           LEFT JOIN stays s ON s.id=o."stayId"
           WHERE o.id=$1 FOR UPDATE''', order_id,
    )
    if not order or not order["reservationId"]:
        return None
    if order["folioChargeId"]:
        return order["folioChargeId"]

    existing = await conn.fetchval(
        '''SELECT id FROM guest_folio_charges
           WHERE "sourceType"='KITCHEN_ORDER' AND "sourceId"=$1 AND status<>'VOID'
           LIMIT 1''', order_id,
    )
    if existing:
        await conn.execute('UPDATE kitchen_orders SET "folioChargeId"=$2,"updatedAt"=now() WHERE id=$1', order_id, existing)
        return existing

    service_date = await conn.fetchval(
        '''SELECT (o."openedAt" AT TIME ZONE COALESCE(p.timezone,'Asia/Bishkek'))::date
           FROM kitchen_orders o JOIN properties p ON p.id=o."propertyId" WHERE o.id=$1''', order_id,
    )
    charge_id = uuid.uuid4()
    delivery_note = f"; доставка {int(order['deliveryFeeKgs'] or 0)} сом" if order["deliveryToRoom"] else ""
    description = f"Питание · {order['orderNumber']}{delivery_note}"
    await conn.execute(
        '''INSERT INTO guest_folio_charges (
             id,"propertyId","reservationId","stayId","guestId","sourceType","sourceId",code,description,
             "amountKgs",status,"serviceDate","createdByType","createdById",metadata,"createdAt","updatedAt"
           ) VALUES ($1,$2,$3,$4,$5,'KITCHEN_ORDER',$6,'DINING_ORDER',$7,$8,'OPEN',$9,$10,$11,$12::jsonb,now(),now())''',
        charge_id, order["propertyId"], order["reservationId"], order["stayId"], order["guestId"], order_id,
        description, int(order["totalKgs"]), service_date, actor_type, actor_id,
        json.dumps({
            "order_number": order["orderNumber"],
            "meal_type": order["mealType"],
            "delivery_to_room": bool(order["deliveryToRoom"]),
            "delivery_fee_kgs": int(order["deliveryFeeKgs"] or 0),
            "payment_effect": "NONE",
        }, ensure_ascii=False),
    )
    await conn.execute('UPDATE kitchen_orders SET "folioChargeId"=$2,"updatedAt"=now() WHERE id=$1', order_id, charge_id)
    await conn.execute(
        '''INSERT INTO audit_logs (
             id,"propertyId","actorType","actorId",action,resource,"resourceId",source,result,"afterJson","createdAt"
           ) VALUES ($1,$2,$3,$4,'POST_KITCHEN_ORDER_TO_FOLIO','GuestFolioCharge',$5,'FOLIO','SUCCESS',$6::jsonb,now())''',
        uuid.uuid4(), order["propertyId"], actor_type, actor_id, str(charge_id),
        json.dumps({
            "order_id": str(order_id), "order_number": order["orderNumber"], "amount_kgs": int(order["totalKgs"]),
            "reservation_id": str(order["reservationId"]), "payment_created": False,
        }, ensure_ascii=False),
    )
    return charge_id


async def reservation_folio_snapshot(conn, pid: uuid.UUID, reservation_id: uuid.UUID) -> dict[str, Any]:
    reservation = await conn.fetchrow(
        '''SELECT r.id,r."bookingNumber",r."totalKgs",r.status::text AS status,r."primaryGuestId",
                  g."firstName",g."lastName",s.id AS stay_id
           FROM reservations r
           LEFT JOIN guests g ON g.id=r."primaryGuestId"
           LEFT JOIN stays s ON s."reservationId"=r.id
           WHERE r.id=$1 AND r."propertyId"=$2''', reservation_id, pid,
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    charges = await conn.fetch(
        '''SELECT id,"sourceType","sourceId",code,description,"amountKgs",status,"serviceDate",
                  "createdByType","createdById",metadata,"createdAt","updatedAt"
           FROM guest_folio_charges
           WHERE "propertyId"=$1 AND "reservationId"=$2
           ORDER BY "createdAt" ASC''', pid, reservation_id,
    )
    payments = await conn.fetch(
        '''SELECT id,"amountKgs",method,status::text AS status,provider,"externalRef",metadata,"paidAt","createdAt"
           FROM payments WHERE "reservationId"=$1 ORDER BY COALESCE("paidAt","createdAt"),"createdAt"''', reservation_id,
    )
    active_charges = [row for row in charges if row["status"] not in {"WAIVED", "VOID"}]
    extras = sum(int(row["amountKgs"]) for row in active_charges)
    accommodation = int(reservation["totalKgs"])
    grand_total = accommodation + extras
    paid = sum(int(row["amountKgs"]) for row in payments if row["status"] == "RECEIVED")
    return {
        "reservation": {
            "id": str(reservation["id"]),
            "booking_number": reservation["bookingNumber"],
            "status": reservation["status"],
            "guest_name": " ".join(part for part in [reservation["firstName"], reservation["lastName"]] if part) or "Гость",
            "stay_id": str(reservation["stay_id"]) if reservation["stay_id"] else None,
        },
        "totals": {
            "accommodation_kgs": accommodation,
            "extras_kgs": extras,
            "grand_total_kgs": grand_total,
            "paid_kgs": paid,
            "remaining_kgs": max(grand_total - paid, 0),
            "overpaid_kgs": max(paid - grand_total, 0),
        },
        "charges": [
            {
                "id": str(row["id"]), "source_type": row["sourceType"],
                "source_id": str(row["sourceId"]) if row["sourceId"] else None,
                "code": row["code"], "description": row["description"], "amount_kgs": int(row["amountKgs"]),
                "status": row["status"], "service_date": row["serviceDate"],
                "created_by_type": row["createdByType"], "created_by_id": row["createdById"],
                "metadata": row["metadata"], "created_at": row["createdAt"], "updated_at": row["updatedAt"],
            }
            for row in charges
        ],
        "payments": [
            {
                "id": str(row["id"]), "amount_kgs": int(row["amountKgs"]), "method": row["method"],
                "status": row["status"], "provider": row["provider"], "external_ref": row["externalRef"],
                "metadata": row["metadata"], "paid_at": row["paidAt"], "recorded_at": row["createdAt"],
            }
            for row in payments
        ],
    }


@router.get("/reservations/{reservation_id}")
async def reservation_folio(
    reservation_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        pid = await property_id(conn, user["property_code"])
        return await reservation_folio_snapshot(conn, pid, reservation_id)


@router.post("/reservations/{reservation_id}/charges", status_code=status.HTTP_201_CREATED)
async def create_manual_charge(
    reservation_id: uuid.UUID,
    payload: ManualChargeCreate,
    request: Request,
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            reservation = await conn.fetchrow(
                '''SELECT r.id,r."primaryGuestId",s.id AS stay_id FROM reservations r
                   LEFT JOIN stays s ON s."reservationId"=r.id
                   WHERE r.id=$1 AND r."propertyId"=$2 FOR UPDATE''', reservation_id, pid,
            )
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            charge_id = uuid.uuid4()
            await conn.execute(
                '''INSERT INTO guest_folio_charges (
                     id,"propertyId","reservationId","stayId","guestId","sourceType",code,description,"amountKgs",status,
                     "serviceDate","createdByType","createdById",metadata,"createdAt","updatedAt"
                   ) VALUES ($1,$2,$3,$4,$5,'MANUAL',$6,$7,$8,'OPEN',$9,'STAFF',$10,$11::jsonb,now(),now())''',
                charge_id, pid, reservation_id, reservation["stay_id"], reservation["primaryGuestId"],
                payload.code.strip().upper(), payload.description.strip(), payload.amount_kgs, payload.service_date,
                user["id"], json.dumps({"notes": payload.notes}, ensure_ascii=False),
            )
            await audit(conn, pid, user, "CREATE_MANUAL_FOLIO_CHARGE", str(charge_id), {
                "reservation_id": str(reservation_id), "amount_kgs": payload.amount_kgs,
                "code": payload.code.strip().upper(), "payment_created": False,
            })
            snapshot = await reservation_folio_snapshot(conn, pid, reservation_id)
    return {"charge_id": str(charge_id), "folio": snapshot}


@router.post("/kitchen-orders/{order_id}/post", status_code=status.HTTP_201_CREATED)
async def post_kitchen_order(
    order_id: uuid.UUID,
    request: Request,
    user: dict[str, Any] = Depends(access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            owns = await conn.fetchval('SELECT 1 FROM kitchen_orders WHERE id=$1 AND "propertyId"=$2', order_id, pid)
            if not owns:
                raise HTTPException(status_code=404, detail="Kitchen order not found")
            charge_id = await ensure_kitchen_order_charge(conn, order_id, actor_type="STAFF", actor_id=user["id"])
            if not charge_id:
                raise HTTPException(status_code=409, detail={"code": "KITCHEN_ORDER_NOT_LINKED_TO_RESERVATION"})
    return {"order_id": str(order_id), "charge_id": str(charge_id), "payment_created": False}


@router.patch("/charges/{charge_id}")
async def patch_charge(
    charge_id: uuid.UUID,
    payload: ChargeStatusPatch,
    request: Request,
    user: dict[str, Any] = Depends(manager_access),
):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid = await property_id(conn, user["property_code"])
            row = await conn.fetchrow(
                '''SELECT id,"reservationId",status,"amountKgs",description FROM guest_folio_charges
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''', charge_id, pid,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Folio charge not found")
            if row["status"] in {"WAIVED", "VOID"}:
                raise HTTPException(status_code=409, detail={"code": "FOLIO_CHARGE_ALREADY_CLOSED", "status": row["status"]})
            await conn.execute(
                '''UPDATE guest_folio_charges SET status=$2,
                     metadata=COALESCE(metadata,'{}'::jsonb) || jsonb_build_object('close_reason',$3::text,'closed_by',$4::text,'closed_at',now()),
                     "updatedAt"=now() WHERE id=$1''',
                charge_id, payload.status, payload.reason.strip(), user["id"],
            )
            await audit(conn, pid, user, "CLOSE_FOLIO_CHARGE", str(charge_id), {
                "from_status": row["status"], "status": payload.status, "reason": payload.reason,
                "amount_kgs": int(row["amountKgs"]), "reservation_id": str(row["reservationId"]),
            })
            snapshot = await reservation_folio_snapshot(conn, pid, row["reservationId"])
    return {"charge_id": str(charge_id), "status": payload.status, "folio": snapshot}
