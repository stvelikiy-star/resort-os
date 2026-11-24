#!/usr/bin/env python3
"""Deterministic MARINA FLEX quote tests. No PostgreSQL, payments or network."""
from __future__ import annotations

import json
import sys
import unittest
import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_pricing import PriceItem, quote_month, quote_package_term  # noqa: E402

HOTEL = str(uuid.UUID("00000000-0000-0000-0000-00000000000a"))


class CommercialQuoteTest(unittest.TestCase):
    def base(self):
        return PriceItem("BASE_PMS", 1, Decimal("10000.00"))

    def ai(self):
        return PriceItem(
            "AI_ASSISTANT", 2, Decimal("4000.00"), enabled_from=date(2026, 11, 16),
            discount_bps=1000,
        )

    def quote(self, *items, start=date(2026, 11, 1)):
        return quote_month(hotel_id=HOTEL, period_start=start, catalog_items=tuple(items))

    def test_full_base_and_seasonal_midmonth_module(self):
        q = self.quote(self.ai(), self.base())
        self.assertEqual(q.period_end, date(2026, 11, 30))
        self.assertEqual(q.subtotal, Decimal("11800.00"))
        self.assertEqual(q.renewal_monthly, Decimal("13600.00"))
        self.assertEqual(q.tax_status, "NOT_CALCULATED")
        item = next(x for x in q.lines if x.sku == "AI_ASSISTANT")
        self.assertEqual(item.active_days, 15)
        self.assertEqual(item.gross, Decimal("2000.00"))
        self.assertEqual(item.discount, Decimal("200.00"))
        self.assertEqual(item.subtotal, Decimal("1800.00"))

    def test_stable_fingerprint_independent_of_input_order(self):
        self.assertEqual(
            self.quote(self.ai(), self.base()).quote_fingerprint,
            self.quote(self.base(), self.ai()).quote_fingerprint,
        )
        self.assertNotEqual(
            self.quote(self.base(), self.ai()).quote_fingerprint,
            self.quote(self.base(), replace(self.ai(), price_version=3)).quote_fingerprint,
        )

    def test_leap_month_calendar_proportion(self):
        q = self.quote(
            PriceItem("BASE_PMS", 1, Decimal("2900"), enabled_from=date(2028, 2, 15)),
            start=date(2028, 2, 1),
        )
        self.assertEqual(q.period_end, date(2028, 2, 29))
        self.assertEqual(q.lines[0].active_days, 15)
        self.assertEqual(q.subtotal, Decimal("1500.00"))

    def test_full_month_before_start_and_not_started(self):
        q1 = self.quote(replace(self.base(), enabled_from=date(2026, 9, 1)))
        q2 = self.quote(replace(self.base(), enabled_from=date(2027, 1, 1)))
        self.assertEqual(q1.subtotal, Decimal("10000.00"))
        self.assertEqual(q2.subtotal, Decimal("0.00"))

    def test_one_sku_cannot_be_billed_twice(self):
        with self.assertRaises(ValueError):
            self.quote(self.base(), self.base())

    def test_unavailable_product_never_sold(self):
        for state in ("PLANNED", "BETA", "RETIRED"):
            with self.subTest(state=state):
                with self.assertRaises(ValueError):
                    self.quote(replace(self.base(), product_status=state))

    def test_invalid_price_currency_quantity_discount_or_snapshot(self):
        modifications = (
            {"currency": "USD"}, {"monthly_price": Decimal("-0.01")},
            {"monthly_price": 0.5}, {"monthly_price": Decimal("1e20")},
            {"quantity": 0}, {"quantity": 10001}, {"quantity": True},
            {"discount_bps": -1}, {"discount_bps": 10001}, {"discount_bps": 1.5},
            {"price_version": 0}, {"price_version": True},
            {"sku": "bad-sku"}, {"pricing_source": "CLIENT"},
        )
        for mod in modifications:
            with self.subTest(mod=mod):
                with self.assertRaises((ValueError, TypeError)):
                    self.quote(replace(self.base(), **mod))

    def test_max_discount_and_legacy_individual_price(self):
        q = self.quote(PriceItem(
            "BASE_PMS", 23, Decimal("5000"), discount_bps=10000,
            pricing_source="LEGACY",
        ))
        self.assertEqual(q.subtotal, Decimal("0.00"))
        self.assertEqual(q.renewal_monthly, Decimal("0.00"))

    def test_bad_period_and_hotel_identifier(self):
        with self.assertRaises(ValueError):
            quote_month(hotel_id=HOTEL, period_start=date(2026, 11, 2), catalog_items=(self.base(),))
        with self.assertRaises(ValueError):
            quote_month(hotel_id="from-user-header", period_start=date(2026, 11, 1), catalog_items=(self.base(),))
        with self.assertRaises(ValueError):
            quote_month(hotel_id=HOTEL, period_start=date(2026, 11, 1), catalog_items=())




class PackageTermTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads((Path(__file__).resolve().parents[1] / "docs/flex/commercial-policy-20261124.json").read_text())
        cls.addons = {k: Decimal(v) for k, v in cls.policy["module_monthly_prices"].items()}

    def quote(self, kind, months, discount, addons=(), one_time=0):
        plan = self.policy["monthly_packages"][kind]
        return quote_package_term(package_kind=kind,
            package_monthly_price=Decimal(plan.get("price", plan.get("base_price"))),
            included_modules=tuple(plan["modules"]), addon_monthly_prices=self.addons,
            selected_addons=addons, months=months, discount_pct=Decimal(discount),
            one_time_total=Decimal(one_time))

    def test_approved_package_totals(self):
        for kind, totals in {
            "BASE": (5000, 13500, 24000, 42000, 36000),
            "BUSINESS": (15000, 40500, 72000, 126000, 108000),
            "PREMIUM": (25000, 67500, 120000, 210000, 180000),
        }.items():
            for (months, discount), expected in zip(((1,0),(3,10),(6,20),(12,30),(12,40)), totals):
                with self.subTest(kind=kind, months=months, discount=discount):
                    self.assertEqual(self.quote(kind, months, discount).subscription_total, Decimal(expected))

    def test_included_modules_not_billed_twice(self):
        q = self.quote("BUSINESS", 1, 0, ("RESTAURANT", "MULTI_HOTEL"))
        self.assertEqual(q.monthly_total, Decimal(20000))
        self.assertEqual(q.extra_modules, ("MULTI_HOTEL",))

    def test_setup_not_discounted(self):
        q = self.quote("BASE", 12, 40, one_time=25000)
        self.assertEqual(q.payable_total, Decimal(61000))
        self.assertEqual(q.one_time_total, Decimal(25000))

    def test_custom_base_plus_modules(self):
        self.assertEqual(self.quote("CUSTOM", 1, 0, ("QR_ZONE", "RESTAURANT")).monthly_total, Decimal(10000))

    def test_reject_duplicate_unknown_and_invalid_term(self):
        for addons in (("QR_ZONE", "QR_ZONE"), ("UNKNOWN",), ("PMS",)):
            with self.assertRaises(ValueError):
                self.quote("BASE", 1, 0, addons)
        with self.assertRaises(ValueError):
            self.quote("BASE", 2, 0)
        with self.assertRaises(ValueError):
            self.quote("BASE", 1, 101)


if __name__ == "__main__":
    unittest.main(verbosity=2)
