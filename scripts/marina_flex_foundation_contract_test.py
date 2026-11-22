#!/usr/bin/env python3
"""Dependency-free acceptance gate for dormant MARINA FLEX policy and accounting.

Never uses a database, user account, payment provider, Docker or network.
Run: python scripts/marina_flex_foundation_contract_test.py
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_foundation import (  # noqa: E402
    InvoiceBalance,
    allocate_confirmed_payment,
    decide_feature_access,
    money,
    percent_of,
    prorate_calendar_month,
)


class AccessRules(unittest.TestCase):
    def test_all_legacy_access_unchanged_when_off(self):
        for state in (None, "OFF", "READ_ONLY", "GRACE", "ON", "UNRECOGNIZED"):
            for operation in ("READ", "WRITE"):
                decision = decide_feature_access(
                    enforcement="OFF", feature_state=state, operation=operation
                )
                self.assertTrue(decision.allowed)
                self.assertFalse(decision.would_deny)

    def test_shadow_reports_but_never_blocks(self):
        decision = decide_feature_access(
            enforcement="SHADOW", feature_state=None, operation="WRITE"
        )
        self.assertTrue(decision.allowed)
        self.assertTrue(decision.would_deny)
        self.assertEqual(decision.reason, "NOT_ENTITLED")

    def test_enforce_rejects_unpaid_write(self):
        decision = decide_feature_access(
            enforcement="ENFORCE", feature_state="OFF", operation="WRITE"
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.would_deny)

    def test_enforce_accepts_active(self):
        for operation in ("READ", "WRITE"):
            decision = decide_feature_access(
                enforcement="ENFORCE", feature_state="ON", operation=operation
            )
            self.assertTrue(decision.allowed)

    def test_read_only_does_not_allow_write(self):
        read = decide_feature_access(
            enforcement="ENFORCE", feature_state="READ_ONLY", operation="READ"
        )
        write = decide_feature_access(
            enforcement="ENFORCE", feature_state="READ_ONLY", operation="WRITE"
        )
        self.assertTrue(read.allowed)
        self.assertFalse(write.allowed)

    def test_no_unbounded_grace(self):
        decision = decide_feature_access(
            enforcement="ENFORCE", feature_state="GRACE", operation="WRITE"
        )
        self.assertFalse(decision.allowed)

    def test_grace_expiration(self):
        now = datetime(2026, 11, 22, tzinfo=timezone.utc)
        before = decide_feature_access(
            enforcement="ENFORCE", feature_state="GRACE", operation="WRITE",
            now=now, valid_until=now + timedelta(seconds=1),
        )
        after = decide_feature_access(
            enforcement="ENFORCE", feature_state="GRACE", operation="WRITE",
            now=now, valid_until=now - timedelta(seconds=1),
        )
        self.assertTrue(before.allowed)
        self.assertFalse(after.allowed)

    def test_core_and_safety_unpaywalled(self):
        for operation in ("WRITE", "READ"):
            self.assertTrue(decide_feature_access(
                enforcement="ENFORCE", feature_state="OFF",
                operation=operation, is_core=True,
            ).allowed)
        for operation in ("PAY_SUBSCRIPTION", "READ_BILLING", "EXPORT_DATA",
                          "FINISH_ACTIVE_STAY", "SETTLE_EXISTING_PAYMENT",
                          "PROCESS_REFUND", "AUDIT_READ"):
            self.assertTrue(decide_feature_access(
                enforcement="ENFORCE", feature_state=None, operation=operation,
            ).allowed)

    def test_reject_unknown_modes(self):
        with self.assertRaises(ValueError):
            decide_feature_access(enforcement="yes", feature_state="ON", operation="READ")
        with self.assertRaises(ValueError):
            decide_feature_access(enforcement="ENFORCE", feature_state="ON", operation="DELETE_DB")

    def test_reject_naive_expiry(self):
        with self.assertRaises(ValueError):
            decide_feature_access(
                enforcement="ENFORCE", feature_state="GRACE", operation="WRITE",
                valid_until=datetime(2026, 1, 1),
                now=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )


class MoneyRules(unittest.TestCase):
    def test_rounds_som_at_minor_unit(self):
        self.assertEqual(money("1.005"), Decimal("1.01"))
        self.assertEqual(money("10"), Decimal("10.00"))

    def test_float_nan_inf_rejected(self):
        for value in (1.0, float("nan"), float("inf"), True):
            with self.assertRaises((TypeError, ValueError)):
                money(value)
        for value in ("NaN", "Infinity"):
            with self.assertRaises(ValueError):
                money(value)

    def test_commission_from_confirmed_allocation(self):
        self.assertEqual(percent_of("4500", 2500), Decimal("1125.00"))
        self.assertEqual(percent_of("0.01", 5000), Decimal("0.01"))
        self.assertEqual(percent_of("200.00", 0), Decimal("0.00"))

    def test_commission_invalid_contract(self):
        for bps in (-1, 10001, 0.5, True):
            with self.assertRaises(ValueError):
                percent_of("100", bps)
        with self.assertRaises(ValueError):
            percent_of("-20", 2000)

    def test_prorate_calendar_month(self):
        self.assertEqual(prorate_calendar_month(
            "3000", active_from=date(2026, 11, 11),
            period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
        ), Decimal("2000.00"))
        self.assertEqual(prorate_calendar_month(
            "1000", active_from=date(2026, 12, 1),
            period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
        ), Decimal("0.00"))
        self.assertEqual(prorate_calendar_month(
            "1000", active_from=date(2026, 10, 1),
            period_start=date(2026, 11, 1), period_end=date(2026, 11, 30),
        ), Decimal("1000.00"))

    def test_prorate_reject_non_month(self):
        with self.assertRaises(ValueError):
            prorate_calendar_month(
                "1000", active_from=date(2026, 11, 12),
                period_start=date(2026, 11, 2), period_end=date(2026, 11, 30),
            )

    def test_partial_payment_tracks_allocations_per_feature(self):
        result = allocate_confirmed_payment("160.00", (
            InvoiceBalance("pms", Decimal("100.00")),
            InvoiceBalance("ai", Decimal("100.00")),
        ))
        self.assertEqual([(x.line_id, x.amount) for x in result.allocations],
                         [("pms", Decimal("100.00")), ("ai", Decimal("60.00"))])
        self.assertEqual(result.unallocated_credit, Decimal("0.00"))
        self.assertEqual(
            sum((x.amount for x in result.allocations), Decimal("0.00")),
            Decimal("160.00"),
        )

    def test_overpayment_is_credit_not_subscription_revenue(self):
        result = allocate_confirmed_payment("250", (
            InvoiceBalance("one", Decimal("80.00")),
            InvoiceBalance("two", Decimal("20.00")),
        ))
        self.assertEqual(sum((x.amount for x in result.allocations), Decimal("0")), Decimal("100"))
        self.assertEqual(result.unallocated_credit, Decimal("150.00"))

    def test_allocation_bad_inputs(self):
        for amount in ("0", "-1"):
            with self.assertRaises(ValueError):
                allocate_confirmed_payment(amount, ())
        with self.assertRaises(ValueError):
            allocate_confirmed_payment("10", (
                InvoiceBalance("same", Decimal("10")),
                InvoiceBalance("same", Decimal("10")),
            ))
        with self.assertRaises(ValueError):
            allocate_confirmed_payment("10", (InvoiceBalance("x", Decimal("-1")),))


if __name__ == "__main__":
    unittest.main(verbosity=2)
