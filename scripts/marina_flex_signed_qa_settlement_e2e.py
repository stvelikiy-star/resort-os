#!/usr/bin/env python3
"""Two-hotel signed QA settlement E2E on disposable PostgreSQL only.

No Finik merchant keys or live bank network. Generated signing keys exist
only in this process; the CI merchant data is synthetic.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
import unittest
import uuid
from decimal import Decimal
from pathlib import Path

import asyncpg
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.flex_qa_payment import (  # noqa: E402
    PROVIDER, canonical_qa_envelope, verify_qa_payment,
)
from app.flex_qa_settlement import apply_verified_qa_payment  # noqa: E402

HOTEL_A = "00000000-0000-0000-0000-00000000000a"
HOTEL_B = "00000000-0000-0000-0000-00000000000b"
INTENT_A_1 = "00000000-0000-0000-0000-000000001001"
INTENT_A_2 = "00000000-0000-0000-0000-000000001002"
INTENT_B_1 = "00000000-0000-0000-0000-000000001003"


class SignedSandboxSettlement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.getenv("FLEX_SETTLEMENT_MODE") != "CI_DISPOSABLE_ONLY":
            raise RuntimeError("Only disposable CI is authorized")
        if not os.getenv("FLEX_DATABASE_URL") or not os.getenv("FLEX_TEST_DB_OWNER_URL"):
            raise RuntimeError("Disposable CI DB endpoints required")
        cls.signer = Ed25519PrivateKey.generate()
        cls.public_pem = cls.signer.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode()

    def event(self, hotel, invoice, intent, transaction, amount):
        return {
            "provider": PROVIDER,
            "event_type": "payment.succeeded",
            "hotel_id": hotel,
            "invoice_id": invoice,
            "payment_intent_id": intent,
            "provider_payment_id": transaction,
            "amount": amount,
            "currency": "KGS",
            "issued_at_ms": int(time.time() * 1000),
        }

    def verify(self, event, private=None, pem=None):
        key = private or self.signer
        signature = base64.b64encode(key.sign(canonical_qa_envelope(event))).decode()
        return verify_qa_payment(
            event=event, signature_b64=signature,
            sandbox_public_key_pem=pem or self.public_pem,
        )

    def test_01_signed_tenant_isolation_and_ledger(self):
        async def scenario():
            owner = await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            pool = await asyncpg.create_pool(
                dsn=os.environ["FLEX_DATABASE_URL"], min_size=1, max_size=4
            )
            try:
                invoices = await owner.fetch(
                    "SELECT invoice_number,id FROM flex_invoices "
                    "WHERE invoice_number IN ('FLEX_RLS_A','FLEX_RLS_B')"
                )
                invoice_by_number = {x["invoice_number"]: str(x["id"]) for x in invoices}
                a = invoice_by_number["FLEX_RLS_A"]
                b = invoice_by_number["FLEX_RLS_B"]
                event1 = self.event(HOTEL_A, a, INTENT_A_1, "CI_signed_payment_0001", "60.00")
                verified1 = self.verify(event1)
                result1 = await apply_verified_qa_payment(pool, verified1)
                self.assertFalse(result1.replay)
                self.assertEqual(result1.allocated, Decimal("60.00"))
                self.assertEqual(result1.credit, Decimal("0.00"))

                replay = await apply_verified_qa_payment(pool, self.verify(event1))
                self.assertTrue(replay.replay)
                self.assertEqual(replay.receipt_id, result1.receipt_id)
                self.assertEqual(replay.allocated, Decimal("60.00"))

                event2 = self.event(HOTEL_A, a, INTENT_A_2, "CI_signed_payment_0002", "50.00")
                result2 = await apply_verified_qa_payment(pool, self.verify(event2))
                self.assertEqual(result2.allocated, Decimal("40.00"))
                self.assertEqual(result2.credit, Decimal("10.00"))

                event_b = self.event(HOTEL_B, b, INTENT_B_1, "CI_signed_payment_0003", "200.00")
                result_b = await apply_verified_qa_payment(pool, self.verify(event_b))
                self.assertEqual(result_b.allocated, Decimal("200.00"))
                self.assertEqual(result_b.credit, Decimal("0.00"))

                # Validly signed event trying to redirect Hotel B's intent to
                # Hotel A must be denied before any ledger entry is written.
                forged_scope = self.event(HOTEL_A, a, INTENT_B_1,
                                          "CI_attacker_cross_hotel_0004", "200.00")
                with self.assertRaises(ValueError):
                    await apply_verified_qa_payment(pool, self.verify(forged_scope))
                mismatched_amount = self.event(HOTEL_A, a, INTENT_A_1,
                                               "CI_attacker_wrong_amount_0005", "10.00")
                with self.assertRaises(ValueError):
                    await apply_verified_qa_payment(pool, self.verify(mismatched_amount))

                # A replay with a reused provider payment ID but altered signed
                # payload cannot be credited as a second valid receipt.
                altered = dict(event1)
                altered["issued_at_ms"] += 1
                with self.assertRaises(ValueError):
                    await apply_verified_qa_payment(pool, self.verify(altered))

                count = await owner.fetchval(
                    "SELECT count(*) FROM flex_confirmed_payments "
                    "WHERE provider=$1", PROVIDER
                )
                self.assertEqual(count, 3)
                events = await owner.fetchval(
                    "SELECT count(*) FROM flex_provider_events WHERE provider=$1", PROVIDER
                )
                self.assertEqual(events, 3)
                self.assertEqual(
                    await owner.fetchval(
                        "SELECT outstanding FROM flex_refund_adjusted_invoice_balances "
                        "WHERE invoice_id=$1", uuid.UUID(a),
                    ),
                    Decimal("0.00"),
                )
                self.assertEqual(
                    await owner.fetchval(
                        "SELECT outstanding FROM flex_refund_adjusted_invoice_balances "
                        "WHERE invoice_id=$1", uuid.UUID(b),
                    ),
                    Decimal("0.00"),
                )
                self.assertEqual(
                    await owner.fetchval(
                        "SELECT unapplied_cash_credit FROM flex_refund_adjusted_invoice_balances "
                        "WHERE invoice_id=$1", uuid.UUID(a),
                    ),
                    Decimal("10.00"),
                )
                self.assertEqual(
                    await owner.fetchval(
                        "SELECT count(*) FROM flex_payment_allocations "
                        "WHERE invoice_id=$1", uuid.UUID(a),
                    ),
                    2,
                )
                # The same receipt can be accounted for on exactly one hotel.
                self.assertEqual(
                    await owner.fetchval(
                        "SELECT count(DISTINCT invoice_id) FROM flex_confirmed_payments "
                        "WHERE provider=$1 AND provider_payment_id=$2",
                        PROVIDER, "CI_signed_payment_0001",
                    ), 1,
                )
            finally:
                await pool.close()
                await owner.close()
        asyncio.run(scenario())

    def test_02_forged_and_expired_messages_never_confirm_cash(self):
        e = self.event(HOTEL_A, "00000000-0000-0000-0000-000000009999",
                       INTENT_A_1, "CI_forged_payment_0006", "25.00")
        with self.assertRaises(ValueError):
            self.verify(e, private=Ed25519PrivateKey.generate())
        stale = dict(e)
        stale["issued_at_ms"] -= 10 * 60 * 1000
        with self.assertRaises(ValueError):
            self.verify(stale)
        future = dict(e)
        future["issued_at_ms"] += 10 * 60 * 1000
        with self.assertRaises(ValueError):
            self.verify(future)
        for invalid in (
            {**e, "currency": "USD"},
            {**e, "amount": "0"},
            {**e, "provider": "FINIK_WEB_SDK"},
            {**e, "event_type": "payment.refunded"},
            {**e, "provider_payment_id": "short"},
        ):
            with self.subTest(payload=invalid), self.assertRaises(ValueError):
                self.verify(invalid)

    def test_03_fails_closed_if_simulator_not_authorized(self):
        e = self.event(HOTEL_A, "00000000-0000-0000-0000-000000009999",
                       INTENT_A_1, "CI_disabled_payment_0007", "1.00")
        old = os.environ.pop("FLEX_SETTLEMENT_MODE", None)
        try:
            with self.assertRaises(RuntimeError):
                self.verify(e)
        finally:
            if old is not None:
                os.environ["FLEX_SETTLEMENT_MODE"] = old

    def test_04_restricted_role_cannot_modify_invoice_or_bank_history(self):
        async def check():
            conn = await asyncpg.connect(os.environ["FLEX_DATABASE_URL"])
            try:
                async with conn.transaction():
                    await conn.execute(
                        "SELECT set_config('flex.qa_mode','CI_DISPOSABLE_ONLY',true)"
                    )
                    await conn.execute(
                        "SELECT set_config('flex.qa_hotel_id',$1,true)", HOTEL_A
                    )
                    await conn.execute("SET LOCAL ROLE flex_qa_settlement_writer")
                    for sql in (
                        "UPDATE flex_invoices SET total=0 WHERE 1=0",
                        "DELETE FROM flex_confirmed_payments WHERE 1=0",
                        "UPDATE flex_subscription_items SET unit_price=0 WHERE 1=0",
                    ):
                        with self.assertRaises(asyncpg.exceptions.InsufficientPrivilegeError):
                            async with conn.transaction():
                                await conn.execute(sql)
            finally:
                await conn.close()
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main(verbosity=2)
