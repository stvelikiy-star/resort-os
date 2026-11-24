#!/usr/bin/env python3
"""P0 FLEX catalog/admin domain tests: no DB, no money receipt and no PMS."""
from __future__ import annotations

import sys
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_catalog_admin import (  # noqa: E402
    NewSku, FuturePrice, NewConfigurationDraft, NewTariffPackageProposal,
    require_admin, ensure_draft_period, ensure_package_proposal,
)
from app.flex_foundation import PlatformPrincipal  # noqa: E402


class CatalogAdminP0(unittest.TestCase):
    def test_only_super_admin_with_mfa(self):
        admin = PlatformPrincipal(subject_id="qa-verified-admin", role="SUPER_ADMIN",
                                  mfa_verified=True)
        self.assertIsNone(require_admin(admin))
        for role, verified in [
            ("SUPER_ADMIN", False),
            ("HOTEL_OWNER", True),
            ("SALES_AGENT", True),
            ("INVESTOR", True),
            ("BILLING", True),
        ]:
            with self.subTest(role=role, verified=verified):
                with self.assertRaises(HTTPException) as e:
                    require_admin(PlatformPrincipal(
                        subject_id="qa-verified", role=role, mfa_verified=verified))
                self.assertEqual(e.exception.status_code, 403)

    def test_planned_sku_only_strict_definition(self):
        p = NewSku(sku="EXTRA_ANALYTICS", title="QA analytics",
                   capability_key="analytics.extra")
        self.assertEqual(p.sku, "EXTRA_ANALYTICS")
        for bad in ["lowercase", "9STARTS_WITH_DIGIT", "X", "BAD-SKU", "../escape"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    NewSku(sku=bad, title="QA analytics",
                           capability_key="analytics.extra")
        with self.assertRaises(ValidationError):
            NewSku(sku="VALID_SKU", title="Valid", capability_key="analytics.extra",
                   product_status="AVAILABLE")
        with self.assertRaises(ValidationError):
            NewSku(sku="VALID_SKU", title="Valid", capability_key="analytics.extra",
                   is_core=True)

    def test_money_string_and_future_price_only(self):
        future = datetime.now(timezone.utc) + timedelta(days=3)
        p = FuturePrice(monthly_price="1234.56", valid_from=future)
        self.assertEqual(p.monthly_price, "1234.56")
        for bad in ["-1", "1.234", "1e6", "NaN", "Infinity", "01.25", " ", ""]:
            with self.subTest(value=bad):
                with self.assertRaises(ValidationError):
                    FuturePrice(monthly_price=bad, valid_from=future)
        with self.assertRaises(ValidationError):
            FuturePrice(monthly_price="1000", currency="USD", valid_from=future)
        with self.assertRaises(ValidationError):
            FuturePrice(monthly_price="1000", valid_from=datetime.now(timezone.utc))
        with self.assertRaises(ValidationError):
            FuturePrice(monthly_price="1000", valid_from=future.replace(tzinfo=None))

    def test_draft_has_no_status_enforcement_or_payment_fields(self):
        kwargs = dict(
            hotel_id=uuid.uuid4(), title="QA Seasonal Plan",
            period_start=date.today() + timedelta(days=3),
            period_end=date.today() + timedelta(days=33),
            skus=["BASE_PMS", "OPTIONAL_FEATURE"],
        )
        p = NewConfigurationDraft(**kwargs)
        self.assertIsNone(ensure_draft_period(p))
        for extra in [{"enforcement": "ENFORCE"}, {"status": "ACTIVE"},
                      {"payment_received": True}, {"monthly_price": "1.00"}]:
            with self.subTest(extra=extra):
                with self.assertRaises(ValidationError):
                    NewConfigurationDraft(**kwargs, **extra)
        with self.assertRaises(ValidationError):
            NewConfigurationDraft(**{**kwargs,"skus":["BASE_PMS","BASE_PMS"]})
        invalid = NewConfigurationDraft(**{**kwargs,"period_end":date.today()})
        with self.assertRaises(HTTPException) as e:
            ensure_draft_period(invalid)
        self.assertEqual(e.exception.status_code, 422)


    def test_package_is_qa_proposal_with_strict_discounts_and_custom_price(self):
        base=dict(hotel_id=uuid.uuid4(),package_kind="BUSINESS",
                  title="QA Business",period_start=date.today()+timedelta(days=4),
                  skus=["AI_ASSISTANT"],discount_pct="10.00",trial_days=14)
        p=NewTariffPackageProposal(**base)
        self.assertEqual(p.discount_pct,"10.00")
        self.assertIsNone(ensure_package_proposal(p))
        for extra in [
            {"package_kind":"OTHER"},
            {"skus":["AI_ASSISTANT","AI_ASSISTANT"]},
            {"discount_pct":"100.01"},
            {"discount_pct":"-1"},
            {"trial_days":91},
            {"state":"ACTIVE"},
            {"enforcement":"ENFORCE"},
            {"payment_received":True}
        ]:
            with self.subTest(extra=extra),self.assertRaises(ValidationError):
                NewTariffPackageProposal(**{**base,**extra})
        for extra in [
            {"custom_monthly_price":"999.00"},
            {"package_kind":"CUSTOM","discount_pct":"10.00","custom_monthly_price":"999.00"}
        ]:
            with self.subTest(extra=extra),self.assertRaises(HTTPException):
                ensure_package_proposal(NewTariffPackageProposal(**{**base,**extra}))
        self.assertIsNone(ensure_package_proposal(NewTariffPackageProposal(
            **{**base,"package_kind":"CUSTOM","discount_pct":"0",
               "custom_monthly_price":"999.00"}
        )))


if __name__ == "__main__":
    unittest.main(verbosity=2)
