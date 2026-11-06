"""Customer-specific CMS regression: no legacy default and explicit owner publication."""
from __future__ import annotations

import os
import unittest

from fastapi import HTTPException

os.environ["MARINA_CUSTOMER_SITE_SAFE_MODE"] = "true"
os.environ["PROPERTY_CODE"] = "MARINA_CUSTOMER_TEST"

from app.customer_site_contract import validate_customer_site_content
from app.customer_site_page import render_customer_site
from app import site_content


GOOD = {
    "hero": {"title": "Hotel Alpha", "subtitle": "Own hotel content & facilities"},
    "contacts": {
        "phone": "+996 555 000 111",
        "whatsapp": "+996 555 000 111",
        "email": "owner@alpha.example",
        "address": "Own Address 12, City",
    },
    "seo": {"title": "Alpha Hotel — Rooms", "description": "A dedicated boutique hotel."},
}


class PerHotelSiteTests(unittest.TestCase):
    def test_customer_safe_mode(self):
        self.assertTrue(site_content.CUSTOMER_SITE_SAFE_MODE)
        self.assertEqual(site_content.PROPERTY_CODE, "MARINA_CUSTOMER_TEST")

    def test_valid_explicit_copy(self):
        self.assertEqual(validate_customer_site_content("en", GOOD)["hero"]["title"], "Hotel Alpha")

    def test_missing_sections_denied(self):
        with self.assertRaises(HTTPException):
            validate_customer_site_content("ru", {"hero": GOOD["hero"]})

    def test_bad_contact_denied(self):
        changed = {**GOOD, "contacts": {**GOOD["contacts"], "phone": "javascript:alert(1)"}}
        with self.assertRaises(HTTPException):
            validate_customer_site_content("en", changed)

    def test_existing_claim_truth_guard_kept(self):
        changed = {**GOOD, "seo": {**GOOD["seo"], "description": "Предоплата 30% обязательна."}}
        with self.assertRaises(HTTPException):
            site_content.validate_public_content("ru", changed)

    def test_unknown_fields_denied(self):
        changed = {**GOOD, "hero": {**GOOD["hero"], "unreviewed": "extra"}}
        with self.assertRaises(HTTPException):
            validate_customer_site_content("en", changed)

    def test_draft_cannot_include_html_in_result(self):
        changed = {**GOOD, "hero": {**GOOD["hero"], "subtitle": '<script>alert("x")</script>'}}
        response = render_customer_site("en", changed)
        body = response.body.decode()
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)

    def test_real_page_is_property_specific(self):
        response = render_customer_site("en", GOOD)
        body = response.body.decode()
        self.assertIn("Hotel Alpha", body)
        self.assertIn("owner@alpha.example", body)
        self.assertNotIn("3korony", body.casefold())
        self.assertNotIn("ak bermet", body.casefold())
        self.assertNotIn("Три Короны", body)

    def test_no_published_copy_is_neutral(self):
        for locale in ("ru", "kg", "en"):
            response = render_customer_site(locale, None)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["x-robots-tag"], "noindex, nofollow")
            self.assertNotIn("Hotel Alpha", response.body.decode())
            self.assertNotIn("3korony", response.body.decode().casefold())

    def test_canonical_cannot_be_invented_on_invalid_host(self):
        response = render_customer_site("en", GOOD)
        self.assertEqual(response.headers["x-robots-tag"], "noindex, nofollow")
        self.assertNotIn('rel="canonical"', response.body.decode())


if __name__ == "__main__":
    unittest.main()
