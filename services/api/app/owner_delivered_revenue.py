"""Owner-only delivery-date reconciliation for accommodation and dining.

Immutable source facts are read, never posted as a Payment or recognized revenue.
An owner can inspect delivered-night allocation and served kitchen/folio matching
without conflating booked rates, guest cash, folio charges, and restaurant orders.
"""
from datetime import date, timedelta
from collections import Counter
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from .auth import require_roles, trusted_property_id

router = APIRouter(prefix="/api/v1/admin/finance/owner",
                   tags=["owner-delivered-revenue-sources"])
owner_only=require_roles("OWNER",module_grant=False)
PREVIEW_LIMIT=500


def allocate_nights(total_kgs:int, check_in:date, check_out:date,
                    from_date:date, to_date:date):
    """Return exact whole-som night allocations. Full stay sums to booked face value.

    Remainder assigned to chronological nights, ensuring that partial-period
    reports are additive without rounding drift or a full booking in each period.
    No claim is made that booked price is an approved nightly room rate.
    """
    nights=(check_out-check_in).days
    if not isinstance(total_kgs,int) or total_kgs<0 or nights<1 or nights>730:
        raise ValueError("Invalid accommodation amount or night range")
    if from_date>to_date:
        raise ValueError("Invalid query period")
    base,extra=divmod(total_kgs,nights)
    first=max(0,(from_date-check_in).days)
    last=min(nights,(to_date-check_in).days+1)
    if last<=first:
        return []
    return [(check_in+timedelta(days=i),base+(1 if i<extra else 0))
            for i in range(first,last)]


def qualify_delivered_stay(row):
    if row["reservation_status"]!="CHECKED_OUT":
        return "RESERVATION_NOT_CHECKED_OUT"
    if row["stay_count"]!=1:
        return "MISSING_OR_MULTIPLE_ACTUAL_STAYS"
    if row["stay_status"]!="CHECKED_OUT" or not row["actual_in"] or not row["actual_out"]:
        return "ACTUAL_STAY_NOT_COMPLETED"
    if not row["has_room_assignment"]:
        return "MISSING_PHYSICAL_ROOM_ASSIGNMENT"
    if row["actual_in"]!=row["checkIn"] or row["actual_out"]!=row["checkOut"]:
        return "ACTUAL_NIGHTS_DIFFER_FROM_BOOKED_NIGHTS"
    if row["totalKgs"]<0 or not (1<=(row["checkOut"]-row["checkIn"]).days<=730):
        return "INVALID_BOOKING_PRICE_OR_DATES"
    return None


def classify_served_order(row):
    """No additive kitchen+folio double counting. One order is one candidate."""
    if row["status"]!="SERVED" or row["totalKgs"]<0:
        return "SERVED_ORDER_INVALID"
    if row["folio_id"] is None:
        return "SERVED_ORDER_NOT_LINKED_TO_FOLIO"
    if row["folio_status"] not in ("OPEN","PAID"):
        return "FOLIO_VOID_OR_WAIVED"
    if row["source_type"]!="KITCHEN_ORDER" or row["source_id"]!=row["id"]:
        return "FOLIO_SOURCE_MISMATCH"
    if row["folio_amount"]!=row["totalKgs"]:
        return "FOLIO_AMOUNT_MISMATCH"
    if row["service_date"] is None or row["service_date"]!=row["served_local_date"]:
        return "FOLIO_SERVICE_DATE_MISMATCH"
    return None


async def delivered_sources(conn,pid,from_date:date,to_date:date,tz:str):
    """Only call from a property-checked, REPEATABLE READ, readonly transaction."""
    reservation_rows=await conn.fetch(
        '''SELECT r.id,r."bookingNumber",r.status::text AS reservation_status,
                  r."checkIn",r."checkOut",r."totalKgs",
                  (SELECT COUNT(*)::int FROM stays ss
                    WHERE ss."propertyId"=r."propertyId" AND ss."reservationId"=r.id)
                      AS stay_count,
                  s.status::text AS stay_status,
                  ((s."actualCheckInAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date
                      AS actual_in,
                  ((s."actualCheckOutAt" AT TIME ZONE 'UTC') AT TIME ZONE $4)::date
                      AS actual_out,
                  EXISTS(SELECT 1 FROM room_assignments a
                         WHERE a."propertyId"=r."propertyId" AND a."stayId"=s.id)
                      AS has_room_assignment
           FROM reservations r
           LEFT JOIN LATERAL (
             SELECT id,status,"actualCheckInAt","actualCheckOutAt"
             FROM stays WHERE "propertyId"=r."propertyId" AND "reservationId"=r.id
             ORDER BY "createdAt" DESC LIMIT 1
           ) s ON TRUE
           WHERE r."propertyId"=$1 AND r."checkIn"<=$3
             AND r."checkOut">$2 AND r.status='CHECKED_OUT'
           ORDER BY r."checkIn",r.id''',pid,from_date,to_date,tz)
    night_total=0;night_count=0;eligible=0
    problem=Counter();preview=[]
    for row in reservation_rows:
        reason=qualify_delivered_stay(row)
        if reason:
            problem[reason]+=1
            continue
        try:
            nightly=allocate_nights(int(row["totalKgs"]),row["checkIn"],row["checkOut"],
                                   from_date,to_date)
        except ValueError:
            problem["INVALID_BOOKING_PRICE_OR_DATES"]+=1
            continue
        eligible+=1
        for day,amount in nightly:
            night_count+=1
            night_total+=amount
            if len(preview)<PREVIEW_LIMIT:
                preview.append({"reservation_id":str(row["id"]),
                                "service_date":day.isoformat(),
                                "allocated_booking_face_value_kgs":str(amount)})
    # Use completed service timestamp as the canonical service event date; a
    # folio with a differing service date is not silently moved to this period.
    orders=await conn.fetch(
        '''SELECT o.id,o.status,o."totalKgs",
                  (o."completedAt" AT TIME ZONE $4)::date AS served_local_date,
                  f.id AS folio_id,f.status AS folio_status,
                  f."sourceType" AS source_type,f."sourceId" AS source_id,
                  f."amountKgs" AS folio_amount,f."serviceDate" AS service_date
           FROM kitchen_orders o
           LEFT JOIN guest_folio_charges f ON f.id=o."folioChargeId"
             AND f."propertyId"=o."propertyId"
           WHERE o."propertyId"=$1 AND o.status='SERVED'
             AND (o."completedAt" AT TIME ZONE $4)::date>=$2
             AND (o."completedAt" AT TIME ZONE $4)::date<=$3
           ORDER BY o."completedAt",o.id''',pid,from_date,to_date,tz)
    served_total=0;valid_total=0;valid_count=0;order_errors=Counter()
    for row in orders:
        served_total+=int(row["totalKgs"])
        reason=classify_served_order(row)
        if reason:
            order_errors[reason]+=1
        else:
            valid_count+=1
            valid_total+=int(row["totalKgs"])
    # Do not add these guest-service/manual/banquet charges to served kitchen
    # totals. These are separate non-kitchen folio sources needing service proof.
    others=await conn.fetchrow(
        '''SELECT COUNT(*)::int AS charge_count,
                  COALESCE(SUM("amountKgs"),0)::bigint AS face_value
           FROM guest_folio_charges
           WHERE "propertyId"=$1 AND "sourceType"<>'KITCHEN_ORDER'
             AND status IN ('OPEN','PAID')
             AND "serviceDate">=$2 AND "serviceDate"<=$3''',
        pid,from_date,to_date)
    undated=await conn.fetchval(
        '''SELECT COUNT(*)::int FROM guest_folio_charges
           WHERE "propertyId"=$1 AND "sourceType"<>'KITCHEN_ORDER'
             AND status IN ('OPEN','PAID') AND "serviceDate" IS NULL''',pid)
    return {
        "scope":"OWNER_ONLY_PROPERTY_SCOPED",
        "period":{"from":from_date.isoformat(),"to":to_date.isoformat(),
                  "timezone":tz,"currency":"KGS"},
        "accommodation":{
            "qualified_reservations":eligible,
            "delivered_booked_nights_count":night_count,
            "allocated_booking_face_value_kgs":str(night_total),
            "night_preview_limit":PREVIEW_LIMIT,
            "night_preview_truncated":night_count>PREVIEW_LIMIT,
            "night_preview":preview,
            "excluded_reservations_count":sum(problem.values()),
            "exclusion_reasons":dict(problem),
            "qualified_source":"CHECKED_OUT_RESERVATION_WITH_MATCHED_ACTUAL_STAY",
            "rate_quality":"BOOKING_TOTAL_DISTRIBUTED_EVENLY_NOT_APPROVED_NIGHTLY_RATE",
        },
        "dining":{
            "served_orders_count":len(orders),
            "served_orders_face_value_kgs":str(served_total),
            "served_with_matching_folio_count":valid_count,
            "single_source_folio_linked_candidate_kgs":str(valid_total),
            "excluded_orders_count":sum(order_errors.values()),
            "exclusion_reasons":dict(order_errors),
            "non_dining_active_folio_charges":others["charge_count"],
            "non_dining_folio_face_value_kgs":str(others["face_value"]),
            "non_dining_undated_folio_count":undated,
            "kitchen_and_folio_double_counted":False,
        },
        "recognition":{
            "recognized_lodging_revenue_kgs":None,
            "recognized_dining_revenue_kgs":None,
            "recognized_other_services_revenue_kgs":None,
            "recognized_total_revenue_kgs":None,
            "status":"SERVICE_DELIVERY_CANDIDATES_NOT_ACCOUNTING_POSTINGS",
            "requires_rate_package_tax_discount_and_refund_reconciliation":True,
            "requires_approved_immutable_revenue_journal":True,
            "cash_received_as_revenue":False,
            "automatic_posting":False,
        },
    }


@router.get("/delivered-revenue-sources")
async def delivered_revenue_sources(request:Request,
                                    from_date:date=Query(),to_date:date=Query(),
                                    user=Depends(owner_only)):
    if to_date<from_date or (to_date-from_date).days>366:
        raise HTTPException(422,detail={"code":"OWNER_DELIVERED_REVENUE_RANGE"})
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction(isolation="repeatable_read",readonly=True):
            pid=await trusted_property_id(conn,user)
            tz=await conn.fetchval('SELECT timezone FROM properties WHERE id=$1',pid)
            if not tz:
                raise HTTPException(503,detail={"code":"PROPERTY_TIMEZONE_UNAVAILABLE"})
            return await delivered_sources(conn,pid,from_date,to_date,tz)
