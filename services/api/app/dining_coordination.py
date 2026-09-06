"""Cross-endpoint coordination for the physical dining floor.

`kitchen_table_reservations` owns scheduled restaurant windows while
`dining_table_sessions` owns live hotel-guest seating.  They share the same
physical `kitchen_tables`, so every mutation that can change live occupancy must
serialize on the same advisory-lock key and compare the two domains before it
changes table state.
"""
from __future__ import annotations

import uuid
from typing import Any


ACTIVE_SESSION_STATUSES = ("WAITING", "SEATED")
ACTIVE_RESERVATION_STATUSES = ("BOOKED", "SEATED")


async def lock_dining_tables(conn, *table_ids: uuid.UUID) -> None:
    """Serialize physical-table mutations in deterministic UUID order."""
    unique = sorted({str(table_id) for table_id in table_ids if table_id is not None})
    for table_id in unique:
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            f"dining-table:{table_id}",
        )


async def lock_dining_stay(conn, stay_id: uuid.UUID) -> None:
    """Serialize live seating mutations for one Stay across different tables."""
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
        f"dining-stay:{stay_id}",
    )


async def active_session_for_table(
    conn,
    table_id: uuid.UUID,
    *,
    exclude_session_id: uuid.UUID | None = None,
):
    return await conn.fetchrow(
        '''SELECT id,"stayId","reservationId","tableId",status,"serviceDate","partySize","mealType"
           FROM dining_table_sessions
           WHERE "tableId"=$1 AND status IN ('WAITING','SEATED')
             AND ($2::uuid IS NULL OR id<>$2)
           ORDER BY CASE status WHEN 'SEATED' THEN 0 ELSE 1 END,"createdAt"
           LIMIT 1 FOR UPDATE''',
        table_id,
        exclude_session_id,
    )


async def current_reservation_for_table(
    conn,
    table_id: uuid.UUID,
    *,
    exclude_reservation_id: uuid.UUID | None = None,
):
    """Return the BOOKED/SEATED reservation whose window contains database now()."""
    return await conn.fetchrow(
        '''SELECT id,"stayId","reservationId","tableId","startsAt","endsAt",status,"guestName"
           FROM kitchen_table_reservations
           WHERE "tableId"=$1 AND status IN ('BOOKED','SEATED')
             AND "startsAt"<=now() AND "endsAt">now()
             AND ($2::uuid IS NULL OR id<>$2)
           ORDER BY CASE status WHEN 'SEATED' THEN 0 ELSE 1 END,"startsAt",id
           LIMIT 1 FOR UPDATE''',
        table_id,
        exclude_reservation_id,
    )


async def reservation_window_contains_now(conn, starts_at, ends_at) -> bool:
    return bool(await conn.fetchval("SELECT $1::timestamptz<=now() AND $2::timestamptz>now()", starts_at, ends_at))


def reservation_matches_session(reservation: Any, session: Any) -> bool:
    """Match only by canonical Stay/Reservation links; guest names are never identity."""
    if not reservation or not session:
        return False
    reservation_stay = reservation["stayId"]
    reservation_booking = reservation["reservationId"]
    session_stay = session["stayId"]
    session_booking = session["reservationId"]
    return bool(
        (reservation_stay is not None and reservation_stay == session_stay)
        or (reservation_booking is not None and reservation_booking == session_booking)
    )


def live_table_status(session: Any) -> str:
    return "OCCUPIED" if session["status"] == "SEATED" else "RESERVED"
