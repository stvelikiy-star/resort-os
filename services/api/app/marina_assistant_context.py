from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .main import get_property_id


MANAGER_ROLES = {"OWNER", "MANAGER"}
RECEPTION_ROLES = {"OWNER", "MANAGER", "RECEPTION"}
OPS_ROLES = {"OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"}
AGENT_ROLE = "AGENT"


def _serialize_rows(rows) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, value in dict(row).items():
            if isinstance(value, (datetime,)):
                item[key] = value.isoformat()
            elif hasattr(value, "isoformat"):
                item[key] = value.isoformat()
            else:
                item[key] = value
        result.append(item)
    return result


async def build_assistant_live_context(request, user: dict[str, Any]) -> dict[str, Any]:
    """Return a small, role-filtered, read-only operational snapshot for MARINA AI."""
    role = str(user.get("role") or "UNKNOWN")
    context: dict[str, Any] = {
        "available": True,
        "read_only": True,
        "role": role,
        "property_code": user.get("property_code"),
    }

    try:
        async with request.app.state.db.acquire() as conn:
            property_id = await get_property_id(conn)
            property_row = await conn.fetchrow(
                'SELECT code, name, timezone, currency FROM properties WHERE id=$1',
                property_id,
            )
            tz_name = (property_row["timezone"] if property_row else None) or "Asia/Bishkek"
            try:
                hotel_now = datetime.now(ZoneInfo(str(tz_name)))
            except Exception:
                hotel_now = datetime.now(ZoneInfo("Asia/Bishkek"))
            hotel_date = hotel_now.date()

            context["property"] = {
                "code": property_row["code"] if property_row else user.get("property_code"),
                "name": property_row["name"] if property_row else None,
                "timezone": tz_name,
                "currency": property_row["currency"] if property_row else "KGS",
                "hotel_date": hotel_date.isoformat(),
            }

            if role in MANAGER_ROLES | {"RECEPTION", "AGENT"}:
                room_rows = await conn.fetch(
                    '''
                    SELECT "operationalState"::text AS state, count(*)::int AS count
                    FROM rooms
                    WHERE "propertyId"=$1
                    GROUP BY "operationalState"
                    ORDER BY "operationalState"
                    ''',
                    property_id,
                )
                context["room_states"] = {row["state"]: row["count"] for row in room_rows}

            if role in RECEPTION_ROLES:
                reservation_rows = await conn.fetch(
                    '''
                    SELECT r."bookingNumber" AS booking_number,
                           r.status::text AS status,
                           r."checkIn" AS check_in,
                           r."checkOut" AS check_out,
                           COALESCE(NULLIF(trim(concat_ws(' ', g."firstName", g."lastName")), ''), 'Без имени') AS guest_name
                    FROM reservations r
                    LEFT JOIN guests g ON g.id=r."primaryGuestId"
                    WHERE r."propertyId"=$1
                      AND (r."checkIn"=$2::date OR r."checkOut"=$2::date OR r.status='CHECKED_IN')
                      AND r.status NOT IN ('CANCELLED')
                    ORDER BY r."checkIn", r."bookingNumber"
                    LIMIT 80
                    ''',
                    property_id,
                    hotel_date,
                )
                context["today_reservations"] = _serialize_rows(reservation_rows)

                request_rows = await conn.fetch(
                    '''
                    SELECT status::text AS status, count(*)::int AS count
                    FROM reservation_requests
                    WHERE "propertyId"=$1
                      AND status NOT IN ('CONVERTED','REJECTED','CANCELLED','EXPIRED')
                    GROUP BY status
                    ORDER BY status
                    ''',
                    property_id,
                )
                context["open_request_counts"] = {row["status"]: row["count"] for row in request_rows}

            if role in MANAGER_ROLES:
                finance = await conn.fetchrow(
                    '''
                    SELECT
                      COALESCE(sum(p."amountKgs") FILTER (
                        WHERE p.status='RECEIVED'
                          AND COALESCE(p."paidAt", p."createdAt")::date=$2::date
                      ),0)::bigint AS received_today_kgs,
                      count(*) FILTER (
                        WHERE p.status='PENDING'
                      )::int AS pending_payments
                    FROM payments p
                    LEFT JOIN reservations r ON r.id=p."reservationId"
                    LEFT JOIN reservation_requests rr ON rr.id=p."requestId"
                    WHERE COALESCE(r."propertyId", rr."propertyId")=$1
                    ''',
                    property_id,
                    hotel_date,
                )
                context["finance_summary"] = dict(finance) if finance else {}

            if role in OPS_ROLES:
                filters = ['t."propertyId"=$1', "t.status NOT IN ('DONE','CANCELLED')"]
                args: list[Any] = [property_id]
                if role == "MAID":
                    filters.append("t.type='HOUSEKEEPING'")
                    filters.append('(t."assignedToId" IS NULL OR t."assignedToId"=$2)')
                    args.append(user["id"])
                elif role == "TECHNICIAN":
                    filters.append("t.type='MAINTENANCE'")
                    filters.append('(t."assignedToId" IS NULL OR t."assignedToId"=$2)')
                    args.append(user["id"])
                rows = await conn.fetch(
                    f'''
                    SELECT t.id::text AS id,
                           t.type::text AS type,
                           t.status::text AS status,
                           t.priority::text AS priority,
                           t.title,
                           r.code AS room_code,
                           t."serviceDate" AS service_date
                    FROM operational_tasks t
                    LEFT JOIN rooms r ON r.id=t."roomId"
                    WHERE {" AND ".join(filters)}
                    ORDER BY
                      CASE t.priority WHEN 'URGENT' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'NORMAL' THEN 2 ELSE 3 END,
                      t."createdAt"
                    LIMIT 60
                    ''',
                    *args,
                )
                context["active_tasks"] = _serialize_rows(rows)

            if role == AGENT_ROLE:
                linked_agent_id = await conn.fetchval(
                    'SELECT "bookingAgentId" FROM staff_users WHERE id=$1 AND "propertyId"=$2 AND "isActive"=true',
                    user["id"],
                    property_id,
                )
                if linked_agent_id:
                    agent_rows = await conn.fetch(
                        '''
                        SELECT r."bookingNumber" AS booking_number,
                               r.status::text AS status,
                               r."checkIn" AS check_in,
                               r."checkOut" AS check_out
                        FROM reservations r
                        WHERE r."propertyId"=$1
                          AND r."agentId"=$2
                          AND r."checkOut">=$3::date
                          AND r.status NOT IN ('CANCELLED','CHECKED_OUT')
                        ORDER BY r."checkIn"
                        LIMIT 60
                        ''',
                        property_id,
                        linked_agent_id,
                        hotel_date,
                    )
                    context["agent_reservations"] = _serialize_rows(agent_rows)
                else:
                    context["agent_linked"] = False

            # Dining/store staff intentionally receive no reservation/finance PII here.
            context["privacy"] = {
                "contains_passwords": False,
                "contains_guest_pin": False,
                "contains_tokens": False,
                "role_filtered": True,
            }
            return context
    except Exception:
        # AI chat remains available as a training assistant if live context fails.
        return {
            "available": False,
            "read_only": True,
            "role": role,
            "property_code": user.get("property_code"),
            "reason": "live_context_unavailable",
        }
