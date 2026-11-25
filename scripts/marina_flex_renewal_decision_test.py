#!/usr/bin/env python3
"""Pure MARINA FLEX renewal acceptance. No database writes, live bank or PMS."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_renewal import RenewalLedgerEvidence, decide_renewal  # noqa: E402

HOTEL = "00000000-0000-0000-0000-00000000000a"
OTHER = "00000000-0000-0000-0000-00000000000b"
SUB = "00000000-0000-0000-0000-0000000000aa"
INVOICE = "00000000-0000-0000-0000-0000000000ab"
AGREEMENT = "00000000-0000-0000-0000-0000000000ac"
PAYMENT = "00000000-0000-0000-0000-0000000000ad"
NOW = datetime(2026, 12, 1, 8, tzinfo=timezone.utc)


class RenewalEvidenceRules(unittest.TestCase):
    def paid(self, *, source="CI_SIGNED_FIXTURE_NOT_BANK"):
        return RenewalLedgerEvidence(
            subscription_id=SUB, hotel_id=HOTEL, invoice_id=INVOICE,
            invoice_hotel_id=HOTEL, agreement_version_id=AGREEMENT,
            invoice_agreement_version_id=AGREEMENT, current_state="GRACE",
            current_period_end=date(2026, 11, 30),
            invoice_period_start=date(2026, 12, 1),
            invoice_period_end=date(2026, 12, 31),
            invoice_total_kg=Decimal("10000.00"),
            refunded_net_allocated_kg=Decimal("10000.00"),
            outstanding_kg=Decimal("0.00"),
            settlement_source=source, last_confirmed_payment_id=PAYMENT,
            settlement_confirmed_at=NOW,
            agreement_signed=True, hotel_link_verified=True, invoice_finalized=True,
        )

    def run_decision(self, evidence):
        return decide_renewal(evidence, now=NOW)

    def test_simulated_payment_can_only_prepare_preview(self):
        result = self.run_decision(self.paid())
        self.assertTrue(result.can_prepare)
        self.assertFalse(result.bank_authorized)
        self.assertEqual(result.reason, "CI_ONLY_NEVER_RENEW_PRODUCTION")
        self.assertEqual(result.execution_state, "PROPOSAL_ONLY_NO_MUTATION")
        self.assertEqual(result.new_period_end, date(2026, 12, 31))

    def test_bank_verified_evidence_also_does_not_mutate(self):
        bank = self.run_decision(self.paid(source="VERIFIED_BANK_SETTLED"))
        self.assertTrue(bank.can_prepare)
        self.assertTrue(bank.bank_authorized)
        self.assertEqual(bank.reason, "AWAIT_APPROVED_BANK_RENEWAL_WRITER")
        self.assertEqual(bank.execution_state, "PROPOSAL_ONLY_NO_MUTATION")

    def test_partial_payment_or_refund_cannot_renew(self):
        for paid, due in (("9900.00", "100.00"), ("0.00", "10000.00"),
                          ("5000.00", "5000.00")):
            case = replace(self.paid(source="VERIFIED_BANK_SETTLED"),
                           refunded_net_allocated_kg=Decimal(paid),
                           outstanding_kg=Decimal(due))
            self.assertFalse(self.run_decision(case).can_prepare)

    def test_cancelled_and_grandfathered_are_never_changed(self):
        for state in ("CANCELLED", "GRANDFATHERED"):
            result = self.run_decision(replace(self.paid(
                source="VERIFIED_BANK_SETTLED"), current_state=state))
            self.assertFalse(result.can_prepare)
            self.assertFalse(result.bank_authorized)

    def test_missing_contract_link_or_issued_invoice_is_rejected(self):
        for change in (
            {"agreement_signed": False},
            {"hotel_link_verified": False},
            {"invoice_finalized": False},
        ):
            self.assertFalse(self.run_decision(replace(self.paid(), **change)).can_prepare)

    def test_no_timestamp_or_payment_reference(self):
        for change in (
            {"last_confirmed_payment_id": None},
            {"settlement_confirmed_at": None},
        ):
            self.assertFalse(self.run_decision(replace(self.paid(), **change)).can_prepare)

    def test_cross_hotel_contract_or_period_mismatch(self):
        cases = (
            {"invoice_hotel_id": OTHER},
            {"invoice_agreement_version_id": OTHER},
            {"invoice_period_start": date(2026, 11, 1)},
            {"invoice_period_end": date(2026, 12, 30)},
            {"invoice_period_start": date(2026, 12, 2)},
            {"current_period_end": date(2026, 11, 29)},
            {"invoice_id": "untrusted"},
        )
        for changes in cases:
            with self.subTest(change=changes), self.assertRaises(ValueError):
                self.run_decision(replace(self.paid(), **changes))

    def test_signed_terms_cross_year_and_leap_day(self):
        for months, end in ((1,date(2026,12,31)),(3,date(2027,2,28)),
                            (6,date(2027,5,31)),(12,date(2027,11,30))):
            with self.subTest(months=months):
                evidence=replace(self.paid(),term_months=months,invoice_period_end=end)
                result=self.run_decision(evidence)
                self.assertTrue(result.can_prepare)
                self.assertFalse(result.bank_authorized)
                self.assertEqual(result.new_period_end,end)
                self.assertEqual(result.execution_state,"PROPOSAL_ONLY_NO_MUTATION")
                self.assertFalse(self.run_decision(replace(evidence,
                    refunded_net_allocated_kg=Decimal("9999.99"),
                    outstanding_kg=Decimal("0.01"))).can_prepare)
                with self.assertRaises(ValueError):
                    self.run_decision(replace(evidence,invoice_period_end=end+timedelta(days=1)))
        leap=replace(self.paid(),current_period_end=date(2027,11,30),
                     invoice_period_start=date(2027,12,1),invoice_period_end=date(2028,2,29),
                     term_months=3)
        self.assertEqual(self.run_decision(leap).new_period_end,date(2028,2,29))

    def test_invalid_signed_terms_are_rejected(self):
        for term in (0,2,4,13,True,"12",None):
            with self.subTest(term=term),self.assertRaises(ValueError):
                self.run_decision(replace(self.paid(),term_months=term))

    def test_inconsistent_revenue_after_refund_denied(self):
        for change in (
            {"refunded_net_allocated_kg": Decimal("11000.00")},
            {"refunded_net_allocated_kg": Decimal("-1.00")},
            {"outstanding_kg": Decimal("-1.00")},
            {"outstanding_kg": Decimal("50.00")},
        ):
            with self.assertRaises(ValueError):
                self.run_decision(replace(self.paid(), **change))

    def test_unknown_receipt_or_future_timestamp_denied(self):
        for changes in (
            {"settlement_source": "FINIK_UNVERIFIED_WEBHOOK"},
            {"settlement_source": "SCREENSHOT"},
            {"current_state": "UNKNOWN"},
            {"settlement_confirmed_at": NOW+timedelta(minutes=3)},
        ):
            with self.assertRaises(ValueError):
                self.run_decision(replace(self.paid(), **changes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
