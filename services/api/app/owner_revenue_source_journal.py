"""Immutable OWNER approval journal for delivered revenue *source evidence*.

Approval means that a property-scoped room night or served dining/folio
source was verified by OWNER. It is NOT tax, discount, refund or package
reconciliation and never creates recognized revenue, P&L or a Payment.
Reversing an approval inserts another immutable event.
"""
import json
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from .auth import require_roles, trusted_property_id
from .owner_delivered_revenue import (allocate_nights, classify_served_order,
                                      qualify_delivered_stay)

router = APIRouter(prefix="/api/v1/admin/finance/owner/revenue-source-events",
                   tags=["owner-revenue-source-journal"])
owner_only = require_roles("OWNER", module_grant=False)


class SourceApproval(BaseModel):
    id: uuid.UUID
    source_type: Literal["ROOM_NIGHT", "DINING_ORDER", "OTHER_SERVICE"]
    source_id: uuid.UUID
    service_date: date
    reason: str = Field(min_length=8, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_not_whitespace(cls, value):
        normal = " ".join(value.split())
        if len(normal) < 8:
            raise ValueError("Approval reason must contain at least 8 nonblank characters")
        return normal


class SourceReversal(BaseModel):
    id: uuid.UUID
    reason: str = Field(min_length=8, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_not_whitespace(cls, value):
        normal = " ".join(value.split())
        if len(normal) < 8:
            raise ValueError("Reversal reason must contain at least 8 nonblank characters")
        return normal


def event_view(row, repeated=False):
    return {
        "id": str(row["id"]),
        "source_type": row["sourceType"],
        "source_id": str(row["sourceId"]),
        "service_date": row["serviceDate"].isoformat(),
        "action": row["action"],
        "face_value_kgs": str(row["faceValueKgs"]),
        "reason": row["reason"],
        "reverses_id": str(row["reversesId"]) if row["reversesId"] else None,
        "created_at": row["createdAt"].isoformat(),
        "already_processed": repeated,
        "source_evidence_approved": row["action"] == "APPROVE_SOURCE",
        "recognized_revenue_kgs": None,
        "recognized_profit_kgs": None,
        "customer_payment_created": False,
        "recognized_revenue_posted": False,
    }


async def qualified_source(conn, property_id, tz, body):
    """Derive amount and immutable approval snapshot, never trust client money."""
    if body.source_type == "ROOM_NIGHT":
        row = await conn.fetchrow(
            '''SELECT r.id,r.status::text AS reservation_status,
                      r."checkIn",r."checkOut",r."totalKgs",
                      (SELECT COUNT(*)::int FROM stays a
                       WHERE a."propertyId"=r."propertyId"
                         AND a."reservationId"=r.id) AS stay_count,
                      s.status::text AS stay_status,
                      ((s."actualCheckInAt" AT TIME ZONE 'UTC')
                        AT TIME ZONE $3)::date AS actual_in,
                      ((s."actualCheckOutAt" AT TIME ZONE 'UTC')
                        AT TIME ZONE $3)::date AS actual_out,
                      EXISTS(SELECT 1 FROM room_assignments a
                        WHERE a."propertyId"=r."propertyId" AND a."stayId"=s.id)
                        AS has_room_assignment
               FROM reservations r
               LEFT JOIN LATERAL (
                  SELECT id,status,"actualCheckInAt","actualCheckOutAt"
                  FROM stays WHERE "propertyId"=r."propertyId"
                    AND "reservationId"=r.id ORDER BY "createdAt" DESC LIMIT 1
               ) s ON TRUE
               WHERE r.id=$1 AND r."propertyId"=$2 FOR SHARE OF r''',
            body.source_id, property_id, tz)
        if not row:
            raise HTTPException(404, detail={"code": "REVENUE_RESERVATION_NOT_FOUND"})
        reason=qualify_delivered_stay(row)
        if reason:
            raise HTTPException(409,detail={"code":reason})
        if not (row["checkIn"] <= body.service_date < row["checkOut"]):
            raise HTTPException(409,detail={"code":"REVENUE_NIGHT_NOT_DELIVERED"})
        nightly=allocate_nights(row["totalKgs"],row["checkIn"],row["checkOut"],
                               body.service_date,body.service_date)
        if len(nightly)!=1:
            raise HTTPException(409,detail={"code":"REVENUE_NIGHT_NOT_DELIVERED"})
        amount=Decimal(nightly[0][1])
        snapshot={
            "qualification":"ACTUAL_STAY_MATCHED",
            "check_in":row["checkIn"].isoformat(),
            "check_out":row["checkOut"].isoformat(),
            "actual_in":row["actual_in"].isoformat(),
            "actual_out":row["actual_out"].isoformat(),
            "booked_total_kgs":str(row["totalKgs"]),
            "night_allocation":"EVEN_BOOKING_FACE_VALUE_WITH_INTEGER_REMAINDER",
            "rate_and_tax_accounting_approved":False,
        }
    elif body.source_type == "DINING_ORDER":
        row=await conn.fetchrow(
            '''SELECT o.id,o.status,o."totalKgs",
                      (o."completedAt" AT TIME ZONE $3)::date AS served_local_date,
                      f.id AS folio_id,f.status AS folio_status,
                      f."sourceType" AS source_type,f."sourceId" AS source_id,
                      f."amountKgs" AS folio_amount,f."serviceDate" AS service_date
               FROM kitchen_orders o
               LEFT JOIN guest_folio_charges f ON f.id=o."folioChargeId"
                 AND f."propertyId"=o."propertyId"
               WHERE o.id=$1 AND o."propertyId"=$2 FOR SHARE OF o''',
            body.source_id,property_id,tz)
        if not row:
            raise HTTPException(404,detail={"code":"REVENUE_DINING_ORDER_NOT_FOUND"})
        reason=classify_served_order(row)
        if reason:
            raise HTTPException(409,detail={"code":reason})
        if row["served_local_date"] != body.service_date:
            raise HTTPException(409,detail={"code":"REVENUE_DINING_WRONG_SERVICE_DATE"})
        amount=Decimal(row["totalKgs"])
        snapshot={
            "qualification":"SERVED_WITH_MATCHED_FOLIO",
            "folio_charge_id":str(row["folio_id"]),
            "folio_status":row["folio_status"],
            "folio_amount_kgs":str(row["folio_amount"]),
            "served_date":row["served_local_date"].isoformat(),
            "tax_discount_refund_accounting_approved":False,
        }
    else:
        row=await conn.fetchrow(
            """SELECT f.id AS folio_id,
                      owner_guest_service_revenue_proof($1,$2,$3) AS amount
               FROM guest_folio_charges f
               WHERE f."propertyId"=$1 AND f."sourceType"='GUEST_SERVICE'
                 AND f."sourceId"=$2 AND f.status IN ('OPEN','PAID')""",
            property_id,body.source_id,body.service_date)
        if not row or row["amount"] is None:
            raise HTTPException(409,detail={"code":"REVENUE_GUEST_SERVICE_NOT_QUALIFIED"})
        amount=Decimal(row["amount"])
        snapshot={"qualification":"COMPLETED_GUEST_SERVICE_WITH_MATCHED_FOLIO",
                  "folio_charge_id":str(row["folio_id"]),
                  "tax_discount_refund_accounting_approved":False}
    return amount,snapshot


async def lock_keys(conn,*keys):
    # Keep ordering stable to prevent deadlocks when source-ID and event-ID
    # happen to be used concurrently by another OWNER operation.
    for key in sorted(set(keys)):
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",key)


@router.post("",status_code=201)
async def approve_source(body:SourceApproval,request:Request,
                         user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            owner_id=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"revenue-event:"+str(body.id),
                            "revenue-source:"+str(pid)+":"+body.source_type+":"+
                            str(body.source_id)+":"+body.service_date.isoformat())
            prior=await conn.fetchrow(
                'SELECT * FROM owner_revenue_source_events WHERE id=$1',body.id)
            if prior:
                if (prior["propertyId"]!=pid or
                    prior["sourceType"]!=body.source_type or
                    prior["sourceId"]!=body.source_id or
                    prior["serviceDate"]!=body.service_date or
                    prior["action"]!="APPROVE_SOURCE" or
                    prior["reason"]!=body.reason or
                    prior["createdById"]!=owner_id):
                    raise HTTPException(409,detail={"code":"REVENUE_EVENT_ID_CONFLICT"})
                return event_view(prior,True)
            duplicate=await conn.fetchval(
                '''SELECT id FROM owner_revenue_source_events
                   WHERE "propertyId"=$1 AND "sourceType"=$2
                     AND "sourceId"=$3 AND "serviceDate"=$4
                     AND action='APPROVE_SOURCE' ''',
                pid,body.source_type,body.source_id,body.service_date)
            if duplicate:
                raise HTTPException(409,detail={"code":"REVENUE_SOURCE_ALREADY_APPROVED"})
            tz=await conn.fetchval(
                'SELECT timezone FROM properties WHERE id=$1',pid)
            if not tz:
                raise HTTPException(503,detail={"code":"PROPERTY_TIMEZONE_UNAVAILABLE"})
            face,snapshot=await qualified_source(conn,pid,tz,body)
            row=await conn.fetchrow(
                '''INSERT INTO owner_revenue_source_events
                   (id,"propertyId","sourceType","sourceId","serviceDate",action,
                    "faceValueKgs","sourceSnapshot",reason,"createdById")
                   VALUES ($1,$2,$3,$4,$5,'APPROVE_SOURCE',$6,$7::jsonb,$8,$9)
                   RETURNING *''',body.id,pid,body.source_type,body.source_id,
                body.service_date,face,json.dumps(snapshot,separators=(",",":")),
                body.reason,owner_id)
            return event_view(row)


@router.post("/{approval_id}/reverse",status_code=201)
async def reverse_source(approval_id:uuid.UUID,body:SourceReversal,
                         request:Request,user=Depends(owner_only)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            owner_id=uuid.UUID(str(user["id"]))
            await lock_keys(conn,"revenue-event:"+str(body.id),
                            "revenue-reversal:"+str(approval_id),
                            "revenue-approval:"+str(pid)+":"+str(approval_id))
            prior=await conn.fetchrow(
                'SELECT * FROM owner_revenue_source_events WHERE id=$1',body.id)
            if prior:
                if (prior["propertyId"]!=pid or
                    prior["action"]!="REVERSE_SOURCE" or
                    prior["reversesId"]!=approval_id or
                    prior["reason"]!=body.reason or
                    prior["createdById"]!=owner_id):
                    raise HTTPException(409,detail={"code":"REVENUE_REVERSAL_ID_CONFLICT"})
                return event_view(prior,True)
            approved=await conn.fetchrow(
                '''SELECT * FROM owner_revenue_source_events
                   WHERE id=$1 AND "propertyId"=$2 AND action='APPROVE_SOURCE' ''',
                approval_id,pid)
            if not approved:
                raise HTTPException(404,detail={"code":"REVENUE_APPROVAL_NOT_FOUND"})
            duplicate=await conn.fetchval(
                '''SELECT id FROM owner_revenue_source_events
                   WHERE "propertyId"=$1 AND "reversesId"=$2
                     AND action='REVERSE_SOURCE' ''',pid,approval_id)
            if duplicate:
                raise HTTPException(409,detail={"code":"REVENUE_ALREADY_REVERSED"})
            # Same tenant/source serialization as the database posting triggers.
            # Older databases can still run legacy code; staging with the new
            # accounting tables must fail closed if the guard is not installed.
            if await conn.fetchval("SELECT to_regclass('owner_accounting_postings') IS NOT NULL"):
                await conn.execute("SELECT owner_lock_revenue_posting($1,$2)",pid,approval_id)
                if await conn.fetchval("SELECT owner_revenue_has_active_posting($1,$2)",pid,approval_id):
                    raise HTTPException(409,detail={"code":"OWNER_REVENUE_ACTIVE_POSTING_REQUIRES_REVERSAL"})
            row=await conn.fetchrow(
                '''INSERT INTO owner_revenue_source_events
                   (id,"propertyId","sourceType","sourceId","serviceDate",action,
                    "faceValueKgs","sourceSnapshot","reversesId",reason,"createdById")
                   VALUES ($1,$2,$3,$4,$5,'REVERSE_SOURCE',$6,$7::jsonb,$8,$9,$10)
                   RETURNING *''',body.id,pid,approved["sourceType"],
                approved["sourceId"],approved["serviceDate"],
                approved["faceValueKgs"],(approved["sourceSnapshot"] if isinstance(approved["sourceSnapshot"],str)
                 else json.dumps(approved["sourceSnapshot"])),
                approval_id,body.reason,owner_id)
            return event_view(row)


async def source_approval_snapshot(conn,property_id,from_date,to_date):
    """Counts are source-approved facts, NOT recognized revenue or P&L."""
    row=await conn.fetchrow(
        '''SELECT COUNT(*) FILTER (WHERE e.action='APPROVE_SOURCE')::int
                    AS approval_count,
                  COUNT(*) FILTER (WHERE e.action='REVERSE_SOURCE')::int
                    AS reversal_count,
                  COUNT(*) FILTER (WHERE e.action='APPROVE_SOURCE'
                    AND e."sourceType"='ROOM_NIGHT'
                    AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
                      WHERE r."reversesId"=e.id))::int AS active_nights,
                  COUNT(*) FILTER (WHERE e.action='APPROVE_SOURCE'
                    AND e."sourceType"='DINING_ORDER'
                    AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
                      WHERE r."reversesId"=e.id))::int AS active_dining_orders,
                  COALESCE(SUM(e."faceValueKgs") FILTER (
                    WHERE e.action='APPROVE_SOURCE'
                    AND NOT EXISTS(SELECT 1 FROM owner_revenue_source_events r
                      WHERE r."reversesId"=e.id)),0) AS active_face_value
           FROM owner_revenue_source_events e
           WHERE e."propertyId"=$1 AND e."serviceDate">=$2
             AND e."serviceDate"<=$3''',
        property_id,from_date,to_date)
    return {
        "approval_events_count":row["approval_count"],
        "reversal_events_count":row["reversal_count"],
        "active_room_nights_count":row["active_nights"],
        "active_served_dining_count":row["active_dining_orders"],
        "active_source_face_value_kgs":str(row["active_face_value"]),
        "status":"SOURCE_APPROVAL_NOT_ACCOUNTING_RECOGNITION",
        "recognized_revenue_kgs":None,
        "recognized_profit_kgs":None,
    }


@router.get("")
async def list_events(request:Request,from_date:date=Query(),
                      to_date:date=Query(),user=Depends(owner_only)):
    if from_date>to_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"REVENUE_JOURNAL_DATE_RANGE"})
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        rows=await conn.fetch(
            '''SELECT * FROM owner_revenue_source_events
               WHERE "propertyId"=$1 AND "serviceDate">=$2
                 AND "serviceDate"<=$3
               ORDER BY "createdAt" DESC,id DESC LIMIT 200''',
            pid,from_date,to_date)
        return {
            "scope":"OWNER_ONLY_PROPERTY_SCOPED",
            "items":[event_view(row) for row in rows],
            "limit":200,
            "history_append_only":True,
            "recognized_revenue_kgs":None,
            "recognized_profit_kgs":None,
            "accounting_policy_status":"SOURCE_APPROVAL_NOT_REVENUE_RECOGNITION",
        }
