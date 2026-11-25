"""Read compatibility for the legacy schema and additive refund ledger.

Only constant, internal SQL is accepted. A partially installed migration
must fail closed; an entirely absent migration means the legacy schema.
"""
from fastapi import HTTPException

LEGACY_BALANCES = """(
 SELECT p.id AS "paymentId",r."propertyId",r.id AS "reservationId",
        p."amountKgs" AS "originalAmountKgs",
        CASE WHEN p.status='REFUNDED' THEN p."amountKgs"::bigint ELSE 0::bigint END AS "refundedKgs",
        CASE WHEN p.status='RECEIVED' THEN p."amountKgs"::bigint ELSE 0::bigint END AS "remainingReceivedKgs",
        p.status AS "receiptStatus"
 FROM payments p JOIN reservations r ON r.id=p."reservationId"
)"""
LEGACY_REFUNDS = """(
 SELECT NULL::uuid AS "propertyId",NULL::uuid AS "paymentId",
        NULL::text AS "evidenceReference",NULL::integer AS "amountKgs",
        NULL::timestamptz AS "refundedAt" WHERE false
) AS legacy_partial_refunds"""


async def refund_compatible_sql(conn, sql: str) -> str:
    state = await conn.fetchrow(
        """SELECT to_regclass('public.owner_reservation_payment_balances') IS NOT NULL AS balances,
                  to_regclass('public.owner_partial_refund_events') IS NOT NULL AS events""")
    if state["balances"] and state["events"]:
        return sql
    if state["balances"] or state["events"]:
        raise HTTPException(503,detail={"code":"PARTIAL_REFUND_SCHEMA_INCOMPLETE"})
    return (sql.replace("owner_reservation_payment_balances",LEGACY_BALANCES)
               .replace("owner_partial_refund_events",LEGACY_REFUNDS))
