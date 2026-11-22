"""MARINA FLEX QA-only transactional payment application.

No public route or real provider can invoke this module. Requires
FLEX_SETTLEMENT_MODE=CI_DISPOSABLE_ONLY AND a dedicated noninheriting
PostgreSQL role granted exclusively in disposable CI.

The caller must first verify an ephemeral CI signature via verify_qa_payment().
Finik callbacks, merchant API and Production must never enter here.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal

import asyncpg

from .flex_foundation import money
from .flex_qa_payment import PROVIDER, VerifiedQaPayment


@dataclass(frozen=True)
class QaSettlementResult:
    receipt_id: str
    invoice_id: str
    allocated: Decimal
    credit: Decimal
    replay: bool
    source: str = "CI_SIGNED_FIXTURE_NOT_BANK"


async def apply_verified_qa_payment(
    pool: asyncpg.Pool,
    verified: VerifiedQaPayment,
) -> QaSettlementResult:
    """Insert one simulated payment and allocate it, entirely in one DB txn.

    Concurrency: advisory invoice lock + unique event and receipt IDs.
    Database triggers additionally lock line/receipt rows and enforce capacity.
    """
    if os.environ.get("FLEX_SETTLEMENT_MODE") != "CI_DISPOSABLE_ONLY":
        raise RuntimeError("QA settlement is disabled")
    if type(verified) is not VerifiedQaPayment or verified.provider != PROVIDER:
        raise ValueError("Only authenticated CI payment evidence is accepted")
    if verified.currency != "KGS" or money(verified.amount) <= 0:
        raise ValueError("Only positive KGS sandbox evidence is supported")

    async with pool.acquire() as conn:
        async with conn.transaction(isolation="serializable"):
            # The verified event binds the hotel and invoice, so any cross-hotel
            # mismatch fails once the intent/issued-record joins are checked.
            await conn.execute(
                "SELECT set_config('flex.qa_hotel_id',$1,true)", verified.hotel_id
            )
            await conn.execute(
                "SELECT set_config('flex.qa_mode','CI_DISPOSABLE_ONLY',true)"
            )
            await conn.execute("SET LOCAL ROLE flex_qa_settlement_writer")
            # The same invoice is serialized across distinct synthetic events.
            await conn.fetchval(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                verified.invoice_id,
            )

            intent = await conn.fetchrow(
                "SELECT i.id,i.invoice_id,i.requested_amount,i.currency,i.state,"
                "       h.hotel_id,h.status AS invoice_status "
                "FROM flex_payment_intents i "
                "JOIN flex_invoices h ON h.id=i.invoice_id "
                "JOIN flex_issued_invoice_records issued ON issued.invoice_id=h.id "
                "WHERE i.id=$1 AND i.provider=$2",
                __import__("uuid").UUID(verified.payment_intent_id),
                PROVIDER,
            )
            if (
                intent is None
                or str(intent["invoice_id"]) != verified.invoice_id
                or str(intent["hotel_id"]) != verified.hotel_id
                or intent["state"] != "READY"
                or intent["invoice_status"] != "ISSUED"
                or intent["currency"] != "KGS"
                or intent["requested_amount"] != money(verified.amount)
            ):
                raise ValueError("QA event does not match an approved issued invoice and intent")

            previous = await conn.fetchrow(
                "SELECT e.payload_sha256, p.id, p.invoice_id, p.hotel_id, p.amount "
                "FROM flex_qa_settlement_evidence e "
                "JOIN flex_confirmed_payments p ON p.id=e.confirmed_payment_id "
                "WHERE e.provider_payment_id=$1",
                verified.provider_payment_id,
            )
            if previous is not None:
                if (
                    previous["payload_sha256"] != verified.payload_sha256
                    or str(previous["invoice_id"]) != verified.invoice_id
                    or str(previous["hotel_id"]) != verified.hotel_id
                    or previous["amount"] != money(verified.amount)
                ):
                    raise ValueError("Replayed provider transaction conflicts with prior proof")
                value = await conn.fetchval(
                    "SELECT coalesce(sum(amount),0) FROM flex_payment_allocations "
                    "WHERE payment_id=$1",
                    previous["id"],
                )
                allocated = money(value)
                return QaSettlementResult(
                    receipt_id=str(previous["id"]), invoice_id=verified.invoice_id,
                    allocated=allocated, credit=money(verified.amount-allocated),
                    replay=True,
                )

            event = await conn.fetchrow(
                "INSERT INTO flex_provider_events(provider,event_id,payload_sha256) "
                "VALUES($1,$2,$3) RETURNING id",
                PROVIDER, verified.provider_payment_id,
                verified.payload_sha256,
            )

            receipt = await conn.fetchrow(
                "INSERT INTO flex_confirmed_payments("
                "hotel_id,invoice_id,provider,provider_payment_id,amount,currency,confirmed_at"
                ") VALUES($1,$2,$3,$4,$5,'KGS',now()) RETURNING id",
                __import__("uuid").UUID(verified.hotel_id),
                __import__("uuid").UUID(verified.invoice_id),
                PROVIDER, verified.provider_payment_id, verified.amount,
            )

            # Invoice-line net paid balances (including explicit refund allocation
            # reversals). The item order is stable and signed invoice is immutable.
            lines = await conn.fetch(
                "SELECT l.id,l.amount, "
                " coalesce((SELECT sum(a.amount) FROM flex_payment_allocations a "
                "     WHERE a.invoice_line_id=l.id),0) "
                " - coalesce((SELECT sum(ar.amount) FROM flex_allocation_reversals ar "
                "     JOIN flex_payment_allocations a ON a.id=ar.allocation_id "
                "     WHERE a.invoice_line_id=l.id),0) AS net_paid "
                "FROM flex_invoice_lines l WHERE l.invoice_id=$1 "
                "ORDER BY l.sku,l.id",
                __import__("uuid").UUID(verified.invoice_id),
            )
            if not lines:
                raise ValueError("Issued invoice has no billable lines")
            remaining = money(verified.amount)
            allocated = Decimal("0.00")
            for line in lines:
                due = money(line["amount"] - line["net_paid"])
                if due < 0:
                    raise ValueError("Invoice line overpaid before new payment")
                applied = min(remaining, due)
                if applied:
                    await conn.execute(
                        "INSERT INTO flex_payment_allocations("
                        "invoice_id,payment_id,invoice_line_id,amount"
                        ") VALUES($1,$2,$3,$4)",
                        __import__("uuid").UUID(verified.invoice_id),
                        receipt["id"], line["id"], applied,
                    )
                    remaining = money(remaining-applied)
                    allocated = money(allocated+applied)

            await conn.execute(
                "INSERT INTO flex_qa_settlement_evidence("
                "provider_payment_id,intent_id,invoice_id,hotel_id,amount,currency,"
                "payload_sha256,confirmed_payment_id"
                ") VALUES($1,$2,$3,$4,$5,'KGS',$6,$7)",
                verified.provider_payment_id,
                __import__("uuid").UUID(verified.payment_intent_id),
                __import__("uuid").UUID(verified.invoice_id),
                __import__("uuid").UUID(verified.hotel_id),
                verified.amount, verified.payload_sha256, receipt["id"],
            )
            await conn.execute(
                "INSERT INTO flex_provider_event_attempts(provider_event_id,status)"
                " VALUES($1,'APPLIED')",
                event["id"],
            )
            return QaSettlementResult(
                receipt_id=str(receipt["id"]), invoice_id=verified.invoice_id,
                allocated=allocated, credit=remaining, replay=False,
            )
