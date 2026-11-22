#!/usr/bin/env python3
"""FLEX invoice math: no provider, no database, no network, no issuance."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.flex_pricing import PriceItem, quote_month  # noqa: E402
from app.flex_foundation import InvoiceBalance  # noqa: E402
from app.flex_billing import (  # noqa: E402
    ApprovedTaxRule, PaymentEvidence, plan_invoice_issuance,
    plan_payment_application,
)

HOTEL = "00000000-0000-0000-0000-00000000000a"
AGREEMENT = "00000000-0000-0000-0000-0000000000ab"
TAX_RULE = "00000000-0000-0000-0000-0000000000ac"
INVOICE = "00000000-0000-0000-0000-0000000000ad"
PAYMENT = "00000000-0000-0000-0000-0000000000ae"


class InvoicePlanContract(unittest.TestCase):
    def quote(self):
        return quote_month(
            hotel_id=HOTEL, period_start=date(2026, 11, 1),
            catalog_items=(
                PriceItem("BASE_PMS", 1, Decimal("10000.00")),
                PriceItem("AI_ASSISTANT", 1, Decimal("4000.00"),
                          enabled_from=date(2026, 11, 16), discount_bps=1000),
            ),
        )

    def rule(self, treatment="ADDED", basis_points=1200):
        # 12% is an artificial CI fixture, NOT a Kyrgyz tax recommendation.
        return ApprovedTaxRule(
            version_id=TAX_RULE, treatment=treatment, rate_bps=basis_points,
            approval_reference="QA-FICTIONAL-TAX-RULE",
        )

    def plan(self, *, rule=None, signed=True, linked=True):
        return plan_invoice_issuance(
            quote=self.quote(), agreement_version_id=AGREEMENT,
            contract_signed=signed, pms_link_verified=linked,
            tax_policy=rule or self.rule(),
        )

    def test_invoice_line_tax_and_total_conserve_amount(self):
        plan = self.plan()
        self.assertEqual(plan.status, "PREPARED_NOT_ISSUED")
        self.assertEqual(plan.net_amount, Decimal("11800.00"))
        self.assertEqual(plan.tax_amount, Decimal("1416.00"))
        self.assertEqual(plan.payable_amount, Decimal("13216.00"))
        self.assertEqual(
            sum((x.payable_amount for x in plan.lines), Decimal("0")),
            plan.payable_amount,
        )
        self.assertEqual(len(plan.issuance_digest), 64)

    def test_no_tax_rule_never_implies_one(self):
        exempt = self.plan(rule=self.rule("EXEMPT", 0))
        self.assertEqual(exempt.tax_amount, Decimal("0.00"))
        self.assertEqual(exempt.payable_amount, Decimal("11800.00"))

    def test_repeated_inputs_reproduce_digest(self):
        p1, p2 = self.plan(), self.plan()
        self.assertEqual(p1.issuance_digest, p2.issuance_digest)
        self.assertNotEqual(
            p1.issuance_digest,
            self.plan(rule=self.rule("EXEMPT", 0)).issuance_digest,
        )

    def test_no_unsigned_contract_or_unverified_pms(self):
        for signed, linked in ((False, True), (True, False), (False, False)):
            with self.assertRaises(ValueError):
                self.plan(signed=signed, linked=linked)

    def test_tax_policy_must_be_explicitly_approved(self):
        cases = (
            self.rule("INCLUSIVE", 1000),
            self.rule("EXEMPT", 100),
            self.rule("ADDED", -1),
            self.rule("ADDED", 10001),
            replace(self.rule(), approval_reference="  "),
            replace(self.rule(), version_id="fake-id"),
        )
        for rule in cases:
            with self.subTest(rule=rule):
                with self.assertRaises(ValueError):
                    self.plan(rule=rule)


class PaymentApplicationContract(unittest.TestCase):
    def payment(self, *, amount="130.00", confirmed=True,
                invoice=INVOICE, currency="KGS"):
        return PaymentEvidence(
            confirmed_payment_id=PAYMENT,
            invoice_id=invoice, amount=Decimal(amount),
            currency=currency, provider_confirmed=confirmed,
        )

    def lines(self):
        return (
            InvoiceBalance("base", Decimal("100.00")),
            InvoiceBalance("ai", Decimal("70.00")),
        )

    def test_partial_payment_is_attributed_to_specific_skus(self):
        plan = plan_payment_application(
            payment=self.payment(), invoice_id=INVOICE,
            line_balances=self.lines(),
        )
        self.assertEqual(
            [(x.line_id, x.amount) for x in plan.allocations],
            [("base", Decimal("100.00")), ("ai", Decimal("30.00"))],
        )
        self.assertEqual(plan.total_allocated, Decimal("130.00"))
        self.assertEqual(plan.unapplied_credit, Decimal("0.00"))
        self.assertFalse(plan.would_fully_pay)

    def test_exact_payment_and_overpayment(self):
        exact = plan_payment_application(
            payment=self.payment(amount="170.00"), invoice_id=INVOICE,
            line_balances=self.lines(),
        )
        self.assertTrue(exact.would_fully_pay)
        over = plan_payment_application(
            payment=self.payment(amount="210.00"), invoice_id=INVOICE,
            line_balances=self.lines(),
        )
        self.assertEqual(over.total_allocated, Decimal("170.00"))
        self.assertEqual(over.unapplied_credit, Decimal("40.00"))
        self.assertTrue(over.would_fully_pay)

    def test_no_qr_screenshot_or_unverified_cash(self):
        for wrong in (
            self.payment(confirmed=False),
            self.payment(currency="USD"),
            self.payment(invoice=HOTEL),
            self.payment(amount="0"),
            self.payment(amount="-10"),
        ):
            with self.subTest(payment=wrong), self.assertRaises(ValueError):
                plan_payment_application(
                    payment=wrong, invoice_id=INVOICE, line_balances=self.lines(),
                )

    def test_reject_empty_or_duplicate_lines(self):
        with self.assertRaises(ValueError):
            plan_payment_application(
                payment=self.payment(), invoice_id=INVOICE, line_balances=(),
            )
        with self.assertRaises(ValueError):
            plan_payment_application(
                payment=self.payment(), invoice_id=INVOICE,
                line_balances=(
                    InvoiceBalance("same", Decimal("10.00")),
                    InvoiceBalance("same", Decimal("10.00")),
                ),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
