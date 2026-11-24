#!/usr/bin/env python3
"""MARINA FLEX lifecycle/preview contract. No database, money movement or PMS."""
from __future__ import annotations

import sys
import unittest
import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_pricing import PriceItem, quote_month  # noqa: E402
from app.flex_subscriptions import (  # noqa: E402
    BillingEvidence, SubscriptionEvidence, decide_subscription_state,
    prepare_invoice_preview,
)

HOTEL = "00000000-0000-0000-0000-00000000000a"
AGREEMENT = "00000000-0000-0000-0000-0000000000ab"
INVOICE = "00000000-0000-0000-0000-0000000000ac"
PAYMENT = "00000000-0000-0000-0000-0000000000ad"
DUE = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
GRACE = DUE + timedelta(days=3)


class SubscriptionStateMachine(unittest.TestCase):
    def evidence(self, state="ACTIVE", due=DUE, grace=GRACE,
                 outstanding="100.00", verified_payment=None,
                 verified=True, signed=True):
        return SubscriptionEvidence(
            hotel_link_verified=verified,
            agreement_signed=signed, current_status=state,
            payment_due_at=due, grace_until=grace,
            billing=BillingEvidence(
                invoice_id=INVOICE, outstanding=Decimal(outstanding),
                currency="KGS", last_verified_payment_id=verified_payment,
            ),
        )

    def decide(self, event, evidence, now=DUE):
        return decide_subscription_state(event=event, evidence=evidence, now=now)

    def test_active_overdue_enters_due_then_grace(self):
        due = self.decide("MARK_PAYMENT_DUE", self.evidence(), DUE)
        self.assertEqual(due.next_state, "PAYMENT_DUE")
        grace = self.decide("ENTER_GRACE", self.evidence(state="PAYMENT_DUE"), DUE)
        self.assertEqual(grace.next_state, "GRACE")

    def test_grace_not_suspended_early(self):
        for state in ("PAYMENT_DUE", "GRACE"):
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    self.decide("SUSPEND_EXPIRED", self.evidence(state=state), DUE)
                suspended = self.decide(
                    "SUSPEND_EXPIRED", self.evidence(state=state), GRACE
                )
                self.assertEqual(suspended.next_state, "SUSPENDED")

    def test_restore_only_with_confirmed_zero_balance(self):
        state = self.evidence(state="SUSPENDED", outstanding="0",
                              verified_payment=PAYMENT)
        restored = self.decide("REACTIVATE_PAID", state, GRACE)
        self.assertEqual(restored.next_state, "ACTIVE")
        for outstanding,payment in (("100",PAYMENT),("0",None),("0","not-a-uuid")):
            with self.subTest(outstanding=outstanding,payment=payment):
                with self.assertRaises(ValueError):
                    self.decide("REACTIVATE_PAID", self.evidence(
                        state="SUSPENDED", outstanding=outstanding,
                        verified_payment=payment,
                    ))

    def test_protect_grandfathered_and_cancelled(self):
        for status in ("GRANDFATHERED", "CANCELLED"):
            for event in ("REACTIVATE_PAID", "ENTER_GRACE", "SUSPEND_EXPIRED"):
                with self.assertRaises(ValueError):
                    self.decide(event, self.evidence(state=status), GRACE)

    def test_no_unsigned_agreement_or_unverified_pms(self):
        for valid,signed in ((False,True),(True,False)):
            with self.assertRaises(ValueError):
                self.decide(
                    "MARK_PAYMENT_DUE",
                    self.evidence(verified=valid, signed=signed),
                    DUE,
                )

    def test_cannot_mark_due_before_due_or_without_debt(self):
        with self.assertRaises(ValueError):
            self.decide(
                "MARK_PAYMENT_DUE", self.evidence(), DUE-timedelta(seconds=1)
            )
        with self.assertRaises(ValueError):
            self.decide(
                "MARK_PAYMENT_DUE", self.evidence(outstanding="0"), DUE
            )

    def test_grace_without_grace_limit_or_expired_rejected(self):
        with self.assertRaises(ValueError):
            self.decide(
                "ENTER_GRACE", self.evidence(state="PAYMENT_DUE",grace=None), DUE
            )
        with self.assertRaises(ValueError):
            self.decide(
                "ENTER_GRACE", self.evidence(state="PAYMENT_DUE"), GRACE
            )

    def test_bad_time_currency_state_or_event_denied(self):
        cases = (
            ("WRONG", self.evidence(), DUE),
            ("MARK_PAYMENT_DUE", self.evidence(state="UNKNOWN"), DUE),
            ("MARK_PAYMENT_DUE", replace(
                self.evidence(), payment_due_at=datetime(2026,11,22)), DUE),
            ("MARK_PAYMENT_DUE", self.evidence(), datetime(2026,11,22)),
            ("MARK_PAYMENT_DUE", self.evidence(grace=DUE-timedelta(days=1)), DUE),
            ("MARK_PAYMENT_DUE", self.evidence(outstanding="-1"), DUE),
            ("MARK_PAYMENT_DUE", replace(
                self.evidence(), billing=BillingEvidence(INVOICE,Decimal("1"),"USD")
            ), DUE),
        )
        for event,evidence,now in cases:
            with self.subTest(event=event,evidence=evidence):
                with self.assertRaises(ValueError):
                    self.decide(event, evidence, now)


class DraftInvoiceMath(unittest.TestCase):
    def quote(self, version=1, price="10000.00"):
        return quote_month(
            hotel_id=HOTEL, period_start=date(2026,11,1),
            catalog_items=(PriceItem(
                sku="BASE_PMS",price_version=version,
                monthly_price=Decimal(price),
            ),),
        )

    def test_preview_never_issues_payment_or_invoice(self):
        preview = prepare_invoice_preview(
            quote=self.quote(), agreement_id=AGREEMENT,
            hotel_link_verified=True, agreement_signed=True,
        )
        self.assertEqual(preview.status, "NON_ISSUABLE")
        self.assertIsNone(preview.invoice_number)
        self.assertIsNone(preview.qr_reference)
        self.assertEqual(preview.amount_excluding_unresolved_taxes, Decimal("10000.00"))
        same = prepare_invoice_preview(
            quote=self.quote(), agreement_id=AGREEMENT,
            hotel_link_verified=True, agreement_signed=True,
        )
        self.assertEqual(preview.preview_id,same.preview_id)
        change = prepare_invoice_preview(
            quote=self.quote(version=2, price="11000"), agreement_id=AGREEMENT,
            hotel_link_verified=True, agreement_signed=True,
        )
        self.assertNotEqual(preview.preview_id, change.preview_id)

    def test_draft_requires_verified_link_and_signed_contract(self):
        for verified,signed in ((False,True),(True,False)):
            with self.subTest(verified=verified,signed=signed):
                with self.assertRaises(ValueError):
                    prepare_invoice_preview(
                        quote=self.quote(), agreement_id=AGREEMENT,
                        hotel_link_verified=verified, agreement_signed=signed,
                    )

    def test_agreement_id_is_not_free_text(self):
        with self.assertRaises(ValueError):
            prepare_invoice_preview(
                quote=self.quote(), agreement_id="client-supplied-id",
                hotel_link_verified=True,agreement_signed=True,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
