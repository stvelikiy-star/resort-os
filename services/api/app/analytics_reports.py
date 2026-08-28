from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import require_roles

router = APIRouter(prefix="/api/v1/admin/reports", tags=["admin-reports"])
manager_access = require_roles("OWNER", "MANAGER")


@router.get("/overview")
async def reports_overview(
    request: Request,
    from_date: date = Query(),
    to_date: date = Query(),
    user: dict[str, Any] = Depends(manager_access),
):
    if to_date < from_date:
        raise HTTPException(status_code=422, detail="to_date must be on or after from_date")
    if (to_date - from_date).days > 366:
        raise HTTPException(status_code=422, detail="report range cannot exceed 367 calendar days")

    end_exclusive = to_date + timedelta(days=1)
    period_days = (end_exclusive - from_date).days

    async with request.app.state.db.acquire() as conn:
        prop = await conn.fetchrow(
            'SELECT id,code,name,timezone,currency FROM properties WHERE code=$1',
            user["property_code"],
        )
        if not prop:
            raise HTTPException(status_code=503, detail="Property not loaded")
        pid = prop["id"]
        timezone = prop["timezone"]
        today = await conn.fetchval("SELECT (now() AT TIME ZONE $1)::date", timezone)

        room_summary = await conn.fetchrow(
            '''
            SELECT count(*)::int AS total,
                   count(*) FILTER (WHERE "operationalState"='CLEAN')::int AS clean,
                   count(*) FILTER (WHERE "operationalState"='DIRTY')::int AS dirty,
                   count(*) FILTER (WHERE "operationalState"='IN_INSPECTION')::int AS in_inspection,
                   count(*) FILTER (WHERE "operationalState"='TECH_BLOCK')::int AS tech_block,
                   count(*) FILTER (WHERE "operationalState"='UNKNOWN')::int AS unknown
            FROM rooms WHERE "propertyId"=$1
            ''',
            pid,
        )
        room_count = int(room_summary["total"] or 0)
        gross_room_nights = room_count * period_days

        occupancy = await conn.fetchrow(
            '''
            WITH reserved AS (
              SELECT COALESCE(SUM(
                GREATEST(
                  LEAST(ib."endDate", $3::date) - GREATEST(ib."startDate", $2::date),
                  0
                )
              ),0)::bigint AS booked_nights,
              COALESCE(SUM(
                (r."totalKgs"::numeric / NULLIF((r."checkOut"-r."checkIn"),0)) *
                GREATEST(
                  LEAST(ib."endDate", $3::date) - GREATEST(ib."startDate", $2::date),
                  0
                )
              ),0)::numeric AS allocated_booked_value
              FROM inventory_blocks ib
              JOIN rooms room ON room.id=ib."roomId"
              JOIN reservations r ON r.id=ib."reservationId"
              WHERE room."propertyId"=$1
                AND ib.active=true
                AND ib."blockType"='RESERVATION'
                AND r.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
                AND ib."endDate" > $2::date
                AND ib."startDate" < $3::date
            ), unavailable AS (
              SELECT COALESCE(SUM(
                GREATEST(
                  LEAST(ib."endDate", $3::date) - GREATEST(ib."startDate", $2::date),
                  0
                )
              ),0)::bigint AS unavailable_nights
              FROM inventory_blocks ib
              JOIN rooms room ON room.id=ib."roomId"
              WHERE room."propertyId"=$1
                AND ib.active=true
                AND ib."blockType" IN ('MAINTENANCE','MANUAL')
                AND ib."endDate" > $2::date
                AND ib."startDate" < $3::date
            )
            SELECT reserved.booked_nights,reserved.allocated_booked_value,unavailable.unavailable_nights
            FROM reserved CROSS JOIN unavailable
            ''',
            pid,
            from_date,
            end_exclusive,
        )

        booked_room_nights = int(occupancy["booked_nights"] or 0)
        unavailable_room_nights = int(occupancy["unavailable_nights"] or 0)
        available_room_nights = max(gross_room_nights - unavailable_room_nights, 0)
        allocated_booked_value = round(float(occupancy["allocated_booked_value"] or 0))
        occupancy_percent = round(booked_room_nights * 100 / available_room_nights, 1) if available_room_nights else 0.0
        adr_kgs = round(allocated_booked_value / booked_room_nights) if booked_room_nights else 0
        revpar_kgs = round(allocated_booked_value / available_room_nights) if available_room_nights else 0

        payment_summary = await conn.fetchrow(
            '''
            SELECT
              COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='RECEIVED'),0)::bigint AS received_kgs,
              COUNT(*) FILTER (WHERE p.status='RECEIVED')::int AS received_count,
              COALESCE(SUM(p."amountKgs") FILTER (WHERE p.status='REFUNDED'),0)::bigint AS refunded_kgs,
              COUNT(*) FILTER (WHERE p.status='FAILED')::int AS failed_count
            FROM payments p
            LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
            LEFT JOIN reservations r ON r.id=p."reservationId"
            WHERE COALESCE(rr."propertyId",r."propertyId")=$1
              AND (COALESCE(p."paidAt",p."createdAt") AT TIME ZONE $4)::date >= $2::date
              AND (COALESCE(p."paidAt",p."createdAt") AT TIME ZONE $4)::date < $3::date
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        stay_summary = await conn.fetchrow(
            '''
            SELECT
              count(*) FILTER (
                WHERE status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
                  AND "checkIn">=$2::date AND "checkIn"<$3::date
              )::int AS arrivals,
              count(*) FILTER (
                WHERE status IN ('CHECKED_IN','CHECKED_OUT')
                  AND "checkOut">=$2::date AND "checkOut"<$3::date
              )::int AS departures,
              count(*) FILTER (WHERE status='CHECKED_IN')::int AS in_house_now,
              count(*) FILTER (WHERE status='GUARANTEED')::int AS guaranteed_now
            FROM reservations WHERE "propertyId"=$1
            ''',
            pid,
            from_date,
            end_exclusive,
        )

        active_debt = await conn.fetchrow(
            '''
            WITH paid AS (
              SELECT "reservationId",COALESCE(SUM("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS paid_kgs
              FROM payments WHERE "reservationId" IS NOT NULL GROUP BY "reservationId"
            )
            SELECT COUNT(*) FILTER (WHERE GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)>0)::int AS debtor_count,
                   COALESCE(SUM(GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)),0)::bigint AS outstanding_kgs
            FROM reservations r
            LEFT JOIN paid p ON p."reservationId"=r.id
            WHERE r."propertyId"=$1 AND r.status IN ('GUARANTEED','CHECKED_IN')
            ''',
            pid,
        )

        debtors = await conn.fetch(
            '''
            WITH paid AS (
              SELECT "reservationId",COALESCE(SUM("amountKgs") FILTER (WHERE status='RECEIVED'),0)::bigint AS paid_kgs
              FROM payments WHERE "reservationId" IS NOT NULL GROUP BY "reservationId"
            )
            SELECT r.id,r."bookingNumber",r.status::text AS status,r."checkIn",r."checkOut",r."totalKgs",
                   COALESCE(p.paid_kgs,0)::bigint AS paid_kgs,
                   GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)::bigint AS outstanding_kgs,
                   g."firstName",g."lastName",g.phone
            FROM reservations r
            LEFT JOIN paid p ON p."reservationId"=r.id
            LEFT JOIN guests g ON g.id=r."primaryGuestId"
            WHERE r."propertyId"=$1
              AND r.status IN ('GUARANTEED','CHECKED_IN')
              AND GREATEST(r."totalKgs"-COALESCE(p.paid_kgs,0),0)>0
            ORDER BY outstanding_kgs DESC,r."checkIn"
            LIMIT 100
            ''',
            pid,
        )

        crm_summary = await conn.fetchrow(
            '''
            SELECT count(*)::int AS leads,
                   count(*) FILTER (WHERE status='NEW')::int AS new,
                   count(*) FILTER (WHERE status='QUOTED')::int AS quoted,
                   count(*) FILTER (WHERE status='AWAITING_PREPAYMENT')::int AS awaiting_prepayment,
                   count(*) FILTER (WHERE status='CONVERTED')::int AS converted,
                   count(*) FILTER (WHERE status IN ('REJECTED','CANCELLED','EXPIRED'))::int AS lost
            FROM reservation_requests
            WHERE "propertyId"=$1
              AND ("createdAt" AT TIME ZONE $4)::date >= $2::date
              AND ("createdAt" AT TIME ZONE $4)::date < $3::date
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )
        leads = int(crm_summary["leads"] or 0)
        converted = int(crm_summary["converted"] or 0)

        crm_channels = await conn.fetch(
            '''
            SELECT COALESCE(NULLIF(trim(source),''),'UNKNOWN') AS source,
                   count(*)::int AS leads,
                   count(*) FILTER (WHERE status='CONVERTED')::int AS converted
            FROM reservation_requests
            WHERE "propertyId"=$1
              AND ("createdAt" AT TIME ZONE $4)::date >= $2::date
              AND ("createdAt" AT TIME ZONE $4)::date < $3::date
            GROUP BY 1 ORDER BY leads DESC,source
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        room_types = await conn.fetch(
            '''
            WITH room_counts AS (
              SELECT rt.id,rt.code,rt.name,count(rm.id)::int AS room_count
              FROM room_types rt
              LEFT JOIN rooms rm ON rm."roomTypeId"=rt.id
              WHERE rt."propertyId"=$1
              GROUP BY rt.id,rt.code,rt.name
            ), booked AS (
              SELECT rm."roomTypeId" AS room_type_id,
                     COALESCE(SUM(GREATEST(LEAST(ib."endDate",$3::date)-GREATEST(ib."startDate",$2::date),0)),0)::bigint AS booked_nights,
                     COALESCE(SUM(
                       (res."totalKgs"::numeric / NULLIF((res."checkOut"-res."checkIn"),0)) *
                       GREATEST(LEAST(ib."endDate",$3::date)-GREATEST(ib."startDate",$2::date),0)
                     ),0)::numeric AS allocated_value,
                     count(DISTINCT res.id)::int AS reservation_count
              FROM inventory_blocks ib
              JOIN rooms rm ON rm.id=ib."roomId"
              JOIN reservations res ON res.id=ib."reservationId"
              WHERE rm."propertyId"=$1 AND ib.active=true AND ib."blockType"='RESERVATION'
                AND res.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
                AND ib."endDate">$2::date AND ib."startDate"<$3::date
              GROUP BY rm."roomTypeId"
            ), unavailable AS (
              SELECT rm."roomTypeId" AS room_type_id,
                     COALESCE(SUM(GREATEST(LEAST(ib."endDate",$3::date)-GREATEST(ib."startDate",$2::date),0)),0)::bigint AS unavailable_nights
              FROM inventory_blocks ib
              JOIN rooms rm ON rm.id=ib."roomId"
              WHERE rm."propertyId"=$1 AND ib.active=true AND ib."blockType" IN ('MAINTENANCE','MANUAL')
                AND ib."endDate">$2::date AND ib."startDate"<$3::date
              GROUP BY rm."roomTypeId"
            )
            SELECT rc.code,rc.name,rc.room_count,
                   COALESCE(b.booked_nights,0)::bigint AS booked_nights,
                   COALESCE(u.unavailable_nights,0)::bigint AS unavailable_nights,
                   COALESCE(b.allocated_value,0)::numeric AS allocated_value,
                   COALESCE(b.reservation_count,0)::int AS reservation_count
            FROM room_counts rc
            LEFT JOIN booked b ON b.room_type_id=rc.id
            LEFT JOIN unavailable u ON u.room_type_id=rc.id
            ORDER BY rc.name
            ''',
            pid,
            from_date,
            end_exclusive,
        )

        channel_value = await conn.fetch(
            '''
            WITH reservation_value AS (
              SELECT res.id,COALESCE(NULLIF(trim(rr.source),''),'UNKNOWN') AS source,
                     SUM(
                       (res."totalKgs"::numeric / NULLIF((res."checkOut"-res."checkIn"),0)) *
                       GREATEST(LEAST(ib."endDate",$3::date)-GREATEST(ib."startDate",$2::date),0)
                     )::numeric AS allocated_value
              FROM reservations res
              JOIN inventory_blocks ib ON ib."reservationId"=res.id AND ib.active=true AND ib."blockType"='RESERVATION'
              JOIN rooms room ON room.id=ib."roomId"
              LEFT JOIN reservation_requests rr ON rr.id=res."requestId"
              WHERE res."propertyId"=$1
                AND res.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
                AND ib."endDate">$2::date AND ib."startDate"<$3::date
              GROUP BY res.id,source
            )
            SELECT source,count(*)::int AS reservations,COALESCE(SUM(allocated_value),0)::numeric AS allocated_value
            FROM reservation_value GROUP BY source ORDER BY allocated_value DESC,source
            ''',
            pid,
            from_date,
            end_exclusive,
        )

        operations = await conn.fetch(
            '''
            SELECT type::text AS type,
                   count(*) FILTER (
                     WHERE ("createdAt" AT TIME ZONE $4)::date >= $2::date
                       AND ("createdAt" AT TIME ZONE $4)::date < $3::date
                   )::int AS created_in_period,
                   count(*) FILTER (
                     WHERE status='DONE'
                       AND "completedAt" IS NOT NULL
                       AND ("completedAt" AT TIME ZONE $4)::date >= $2::date
                       AND ("completedAt" AT TIME ZONE $4)::date < $3::date
                   )::int AS completed_in_period,
                   count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION'))::int AS active_now,
                   count(*) FILTER (WHERE status IN ('OPEN','IN_PROGRESS','IN_INSPECTION') AND priority='URGENT')::int AS urgent_now
            FROM operational_tasks
            WHERE "propertyId"=$1
            GROUP BY type ORDER BY type
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

        daily = await conn.fetch(
            '''
            WITH days AS (
              SELECT generate_series($2::date,$3::date - 1,interval '1 day')::date AS d
            ), booked AS (
              SELECT day.d,count(DISTINCT ib."roomId")::int AS booked_rooms
              FROM days day
              LEFT JOIN inventory_blocks ib ON ib.active=true AND ib."blockType"='RESERVATION'
                AND ib."startDate"<=day.d AND ib."endDate">day.d
              LEFT JOIN rooms rm ON rm.id=ib."roomId" AND rm."propertyId"=$1
              LEFT JOIN reservations r ON r.id=ib."reservationId" AND r.status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
              WHERE rm.id IS NOT NULL AND r.id IS NOT NULL
              GROUP BY day.d
            ), payments_day AS (
              SELECT (p."paidAt" AT TIME ZONE $4)::date AS d,COALESCE(SUM(p."amountKgs"),0)::bigint AS received_kgs
              FROM payments p
              LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
              LEFT JOIN reservations r ON r.id=p."reservationId"
              WHERE COALESCE(rr."propertyId",r."propertyId")=$1 AND p.status='RECEIVED' AND p."paidAt" IS NOT NULL
                AND (p."paidAt" AT TIME ZONE $4)::date >= $2::date
                AND (p."paidAt" AT TIME ZONE $4)::date < $3::date
              GROUP BY 1
            ), arrivals AS (
              SELECT "checkIn" AS d,count(*)::int AS arrivals
              FROM reservations
              WHERE "propertyId"=$1 AND status IN ('GUARANTEED','CHECKED_IN','CHECKED_OUT')
                AND "checkIn">=$2::date AND "checkIn"<$3::date GROUP BY 1
            ), departures AS (
              SELECT "checkOut" AS d,count(*)::int AS departures
              FROM reservations
              WHERE "propertyId"=$1 AND status IN ('CHECKED_IN','CHECKED_OUT')
                AND "checkOut">=$2::date AND "checkOut"<$3::date GROUP BY 1
            )
            SELECT day.d,COALESCE(booked.booked_rooms,0)::int AS booked_rooms,
                   COALESCE(payments_day.received_kgs,0)::bigint AS received_kgs,
                   COALESCE(arrivals.arrivals,0)::int AS arrivals,
                   COALESCE(departures.departures,0)::int AS departures
            FROM days day
            LEFT JOIN booked ON booked.d=day.d
            LEFT JOIN payments_day ON payments_day.d=day.d
            LEFT JOIN arrivals ON arrivals.d=day.d
            LEFT JOIN departures ON departures.d=day.d
            ORDER BY day.d
            ''',
            pid,
            from_date,
            end_exclusive,
            timezone,
        )

    room_type_items = []
    for row in room_types:
        gross = int(row["room_count"] or 0) * period_days
        unavailable = int(row["unavailable_nights"] or 0)
        available = max(gross - unavailable, 0)
        booked = int(row["booked_nights"] or 0)
        allocated = round(float(row["allocated_value"] or 0))
        room_type_items.append(
            {
                "code": row["code"],
                "name": row["name"],
                "room_count": int(row["room_count"] or 0),
                "reservation_count": int(row["reservation_count"] or 0),
                "booked_room_nights": booked,
                "available_room_nights": available,
                "occupancy_percent": round(booked * 100 / available, 1) if available else 0.0,
                "allocated_booked_value_kgs": allocated,
                "adr_kgs": round(allocated / booked) if booked else 0,
                "revpar_kgs": round(allocated / available) if available else 0,
            }
        )

    return {
        "property": {
            "code": prop["code"],
            "name": prop["name"],
            "timezone": timezone,
            "currency": prop["currency"],
            "local_date": today,
        },
        "range": {"from": from_date, "to": to_date, "days": period_days},
        "kpi": {
            "room_count": room_count,
            "gross_room_nights": gross_room_nights,
            "unavailable_room_nights": unavailable_room_nights,
            "available_room_nights": available_room_nights,
            "booked_room_nights": booked_room_nights,
            "occupancy_percent": occupancy_percent,
            "allocated_booked_value_kgs": allocated_booked_value,
            "adr_kgs": adr_kgs,
            "revpar_kgs": revpar_kgs,
            "received_payments_kgs": int(payment_summary["received_kgs"] or 0),
            "received_payment_count": int(payment_summary["received_count"] or 0),
            "active_outstanding_kgs": int(active_debt["outstanding_kgs"] or 0),
            "active_debtor_count": int(active_debt["debtor_count"] or 0),
            "arrivals": int(stay_summary["arrivals"] or 0),
            "departures": int(stay_summary["departures"] or 0),
            "in_house_now": int(stay_summary["in_house_now"] or 0),
            "guaranteed_now": int(stay_summary["guaranteed_now"] or 0),
        },
        "rooms_now": dict(room_summary),
        "crm": {
            **dict(crm_summary),
            "conversion_percent": round(converted * 100 / leads, 1) if leads else 0.0,
            "channels": [
                {
                    **dict(row),
                    "conversion_percent": round(int(row["converted"] or 0) * 100 / int(row["leads"] or 1), 1),
                }
                for row in crm_channels
            ],
        },
        "payments": {
            "received_kgs": int(payment_summary["received_kgs"] or 0),
            "received_count": int(payment_summary["received_count"] or 0),
            "refunded_status_amount_kgs": int(payment_summary["refunded_kgs"] or 0),
            "failed_count": int(payment_summary["failed_count"] or 0),
        },
        "room_types": room_type_items,
        "channels": [
            {
                "source": row["source"],
                "reservations": int(row["reservations"] or 0),
                "allocated_booked_value_kgs": round(float(row["allocated_value"] or 0)),
            }
            for row in channel_value
        ],
        "operations": [dict(row) for row in operations],
        "debtors": [
            {
                "reservation_id": str(row["id"]),
                "booking_number": row["bookingNumber"],
                "status": row["status"],
                "guest_name": " ".join(part for part in [row["firstName"], row["lastName"]] if part) or None,
                "phone": row["phone"],
                "check_in": row["checkIn"],
                "check_out": row["checkOut"],
                "total_kgs": int(row["totalKgs"]),
                "paid_kgs": int(row["paid_kgs"] or 0),
                "outstanding_kgs": int(row["outstanding_kgs"] or 0),
            }
            for row in debtors
        ],
        "daily": [
            {
                "date": row["d"],
                "booked_rooms": int(row["booked_rooms"] or 0),
                "occupancy_percent": round(int(row["booked_rooms"] or 0) * 100 / room_count, 1) if room_count else 0.0,
                "received_kgs": int(row["received_kgs"] or 0),
                "arrivals": int(row["arrivals"] or 0),
                "departures": int(row["departures"] or 0),
            }
            for row in daily
        ],
        "truth": {
            "source_of_truth": "RESORT_CORE",
            "received_payments": "Cash collection metric: only manager-recorded Payment.status=RECEIVED facts attributed by paidAt in the hotel timezone.",
            "allocated_booked_value": "Management allocation, not statutory revenue recognition. Reservation.totalKgs is distributed evenly across stay nights overlapping the selected range because a normalized nightly posted-revenue ledger is not yet stored.",
            "adr_revpar": "Management ADR/RevPAR derived from allocated booked value. Use accounting exports for statutory financial reporting.",
            "availability": "Available room-nights subtract active MAINTENANCE/MANUAL inventory blocks. Historical out-of-service accuracy depends on retaining those blocks.",
            "crm": "Request statuses are current statuses of leads created in the selected range, not a historical stage-as-of snapshot.",
        },
    }
