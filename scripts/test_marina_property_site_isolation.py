#!/usr/bin/env python3
"""Regression: one property's public site must never inherit another hotel's default content."""
from __future__ import annotations

import os
import sys
import unittest
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))
from app import customer_site_page, site_content  # noqa: E402


class FakeConnection:
    def __init__(self, published=None, published_version=0, room_types=None):
        self.published = published
        self.published_version = published_version
        self.room_types = room_types or []
        self.property_id = uuid.uuid4()

    async def fetchval(self, statement, code):
        assert "properties" in statement and code == site_content.PROPERTY_CODE
        return self.property_id

    async def fetchrow(self, statement, property_id, locale, scope):
        assert property_id == self.property_id and scope == "PUBLIC_SITE"
        if self.published is None:
            return None
        return {
            "id": uuid.uuid4(),
            "locale": locale,
            "draftJson": {},
            "publishedJson": self.published,
            "version": 2,
            "publishedVersion": self.published_version,
            "publishedAt": None,
            "updatedAt": None,
        }

    async def fetch(self, statement, property_id):
        assert 'room_types' in statement and 'rooms' in statement
        assert property_id == self.property_id
        return self.room_types

    @asynccontextmanager
    async def transaction(self):
        yield self


class FakeDB:
    def __init__(self, connection):
        self.connection = connection

    @asynccontextmanager
    async def acquire(self):
        yield self.connection


def request_for(connection):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=FakeDB(connection))))


class IsolatedPublicSiteTests(unittest.IsolatedAsyncioTestCase):
    async def test_unpublished_other_hotels_return_404_no_legacy_copy(self):
        # Force real-runtime conditions even when this test runs on GitHub
        # Actions, where historical smoke fixtures are available separately.
        with patch.dict(os.environ, {"APP_ENV": "production", "GITHUB_ACTIONS": "false", "CI": "false"}):
            for property_code in ("ASKA_TASH", "MARINA_HOTEL01", "MARINA_RC430", "THREE_CROWNS"):
                with self.subTest(property_code=property_code):
                    with patch.object(site_content, "PROPERTY_CODE", property_code), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
                        with self.assertRaises(HTTPException) as ctx:
                            await site_content.public_site_content(request_for(FakeConnection()))
                        self.assertEqual(ctx.exception.status_code, 404)

    async def test_unpublished_draft_is_not_publication(self):
        with patch.object(site_content, "PROPERTY_CODE", "ASKA_TASH"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            with self.assertRaises(HTTPException) as ctx:
                await site_content.public_site_content(request_for(FakeConnection({"seo": {"title": "Aska Tash"}}, published_version=0)))
            self.assertEqual(ctx.exception.status_code, 404)

    async def test_published_property_does_not_inherit_foreign_sections(self):
        own_content = {"seo": {"title": "ASKA TASH"}, "hero": {"title": "Our hotel"}}
        with patch.object(site_content, "PROPERTY_CODE", "ASKA_TASH"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            result = await site_content.public_site_content(request_for(FakeConnection(own_content, published_version=2)))
            self.assertEqual(result["property"], "ASKA_TASH")
            self.assertEqual(result["source"], "DATABASE")
            self.assertEqual(result["content"], own_content)
            self.assertNotIn("AK BERMET", str(result))

    async def test_admin_unpublished_property_is_empty_not_other_hotel(self):
        with patch.object(site_content, "PROPERTY_CODE", "ASKA_TASH"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            result = await site_content.admin_site_content(request_for(FakeConnection()), _user={"id": str(uuid.uuid4())})
            self.assertEqual(result["property"], "ASKA_TASH")
            self.assertTrue(all(item["source"] == "UNPUBLISHED" and item["draft"] == {} and item["published"] == {} for item in result["items"]))
            self.assertEqual([item["locale"] for item in result["items"]], ["ru", "kg", "kz", "en"])

    async def test_no_empty_publish_can_publish_foreign_default(self):
        with patch.object(site_content, "PROPERTY_CODE", "ASKA_TASH"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            with self.assertRaises(HTTPException) as ctx:
                await site_content.publish_site_content("ru", request_for(FakeConnection()), user={"id": str(uuid.uuid4())})
            self.assertEqual(ctx.exception.status_code, 409)

    async def test_historical_fixture_is_explicitly_isolated_to_staging(self):
        with patch.object(site_content, "PROPERTY_CODE", "AK_BERMET_TEST"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            with patch.dict(os.environ, {"APP_ENV": "staging"}):
                self.assertTrue(site_content.legacy_fixture_defaults_allowed())
                result = await site_content.public_site_content(request_for(FakeConnection()))
                self.assertEqual(result["source"], "DEFAULT")
            with patch.dict(os.environ, {"APP_ENV": "production"}):
                self.assertFalse(site_content.legacy_fixture_defaults_allowed())
                with self.assertRaises(HTTPException):
                    await site_content.public_site_content(request_for(FakeConnection()))

    def test_historical_three_crowns_fixture_only_on_github_actions(self):
        with patch.object(site_content, "PROPERTY_CODE", "THREE_CROWNS"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", False):
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "CI": "true", "APP_ENV": "test"}):
                self.assertTrue(site_content.legacy_fixture_defaults_allowed())
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "false", "CI": "true", "APP_ENV": "test"}):
                self.assertFalse(site_content.legacy_fixture_defaults_allowed())
            with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "CI": "true", "APP_ENV": "production"}):
                self.assertFalse(site_content.legacy_fixture_defaults_allowed())

    def test_safe_mode_never_allows_legacy_fixture(self):
        with patch.object(site_content, "PROPERTY_CODE", "AK_BERMET_TEST"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True):
            with patch.dict(os.environ, {"APP_ENV": "staging"}):
                self.assertFalse(site_content.legacy_fixture_defaults_allowed())

    def test_guest_entrance_never_mentions_another_property(self):
        for name in ("apps/web/app/guest/page.tsx", "apps/web/components/GuestLanding.tsx"):
            content = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("MARINA SMART", content)
            for legacy in ("AK BERMET", "Три Короны", "Three Crowns"):
                self.assertNotIn(legacy, content)


    async def test_customer_safe_mode_reads_legacy_publication_without_mutating_it(self):
        import copy
        original = {
            "hero": {"title": "Synthetic ALPHA", "copy": "Stay at ALPHA"},
            "contacts": {
                "phone": "+996 555 111 222", "whatsapp": "+996 555 111 222",
                "email": "alpha@example.test", "address": "ALPHA Test Street",
            },
            "seo": {"title": "ALPHA site", "description": "ALPHA only"},
            "rooms": {"title": "Old rooms section must be retained in storage"},
        }
        before = copy.deepcopy(original)
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True):
            result = await site_content.public_site_content(request_for(FakeConnection(original, published_version=3)))
        self.assertEqual(result["property"], "ALPHA")
        self.assertEqual(result["content"]["hero"]["subtitle"], "Stay at ALPHA")
        self.assertEqual(set(result["content"]), {"hero", "contacts", "seo"})
        self.assertEqual(result["published_version"], 3)
        self.assertEqual(original, before)
        self.assertIn("rooms", original)

    async def test_customer_safe_mode_rejects_incomplete_legacy_publication(self):
        original = {
            "hero": {"title": "ALPHA", "copy": "Our hotel"},
            "contacts": {"phone": "+996 555 111 222"},
            "seo": {"title": "ALPHA", "description": "Our hotel"},
            "rooms": {"title": "Catalog"},
        }
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True):
            with self.assertRaises(HTTPException) as ctx:
                await site_content.public_site_content(request_for(FakeConnection(original, published_version=2)))
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_customer_safe_mode_rejects_forbidden_claim_hidden_in_legacy_section(self):
        original = {
            "hero": {"title": "ALPHA", "copy": "Stay at ALPHA"},
            "contacts": {"phone": "+996 555 111 222", "whatsapp": "+996 555 111 222", "email": "alpha@example.test", "address": "ALPHA Street"},
            "seo": {"title": "ALPHA", "description": "ALPHA"},
            "rooms": {"copy": "Fixed 30% prepayment required"},
        }
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True):
            with self.assertRaises(HTTPException) as ctx:
                await site_content.public_site_content(request_for(FakeConnection(original, published_version=2)))
        self.assertEqual(ctx.exception.status_code, 422)

    async def test_customer_safe_mode_does_not_project_invalid_new_publication(self):
        original = {
            "hero": {"title": "ALPHA", "subtitle": "Our hotel"},
            "contacts": {"phone": "INVALID", "whatsapp": "+996 555 111 222", "email": "alpha@example.test", "address": "ALPHA Street"},
            "seo": {"title": "ALPHA", "description": "ALPHA"},
        }
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True):
            with self.assertRaises(HTTPException) as ctx:
                await site_content.public_site_content(request_for(FakeConnection(original, published_version=2)))
        self.assertEqual(ctx.exception.status_code, 422)



    async def test_customer_html_page_renders_legacy_published_copy_for_own_hotel(self):
        document = {
            "hero": {"title": "Hotel ALPHA", "copy": "Welcome to Alpha"},
            "contacts": {"phone": "+996 555 111 222", "whatsapp": "+996 555 111 222", "email": "alpha@example.test", "address": "ALPHA Avenue"},
            "seo": {"title": "Alpha Homepage", "description": "Only Alpha"},
            "rooms": {"title": "Historic rooms kept in PostgreSQL"},
        }
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True), patch.object(customer_site_page, "CUSTOMER_SITE_SAFE_MODE", True):
            response = await customer_site_page.customer_page(request_for(FakeConnection(document, published_version=2)), locale="ru")
        body = response.body.decode()
        self.assertIn("Hotel ALPHA", body)
        self.assertIn("Welcome to Alpha", body)
        self.assertIn("alpha@example.test", body)
        self.assertNotIn("Три Короны", body)
        self.assertNotIn("3korony", body)

    async def test_customer_html_page_does_not_publish_unpublished_legacy_draft(self):
        document = {
            "hero": {"title": "Hotel ALPHA", "copy": "Welcome"},
            "contacts": {"phone": "+996 555 111 222", "whatsapp": "+996 555 111 222", "email": "alpha@example.test", "address": "ALPHA Avenue"},
            "seo": {"title": "Alpha Homepage", "description": "Only Alpha"},
            "rooms": {"title": "Historical rooms"},
        }
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True), patch.object(customer_site_page, "CUSTOMER_SITE_SAFE_MODE", True):
            response = await customer_site_page.customer_page(request_for(FakeConnection(document, published_version=0)), locale="ru")
        self.assertNotIn("Hotel ALPHA", response.body.decode())
        self.assertEqual(response.headers["x-robots-tag"], "noindex, nofollow")



    async def test_customer_rooms_returns_only_own_published_categories(self):
        document = {
            "hero": {"title": "Hotel ALPHA", "copy": "Alpha stay"},
            "contacts": {"phone": "+996 555 111 222", "whatsapp": "+996 555 111 222", "email": "alpha@example.test", "address": "Alpha Avenue"},
            "seo": {"title": "Alpha Rooms", "description": "Alpha rooms"},
            "rooms": {"title": "Rooms catalogue"},
        }
        categories = [{"name": "Alpha Studio <safe>", "capacityAdults": 2, "capacityChildren": 1, "areaLabel": "32 m2"}]
        fake = FakeConnection(document, published_version=4, room_types=categories)
        with patch.object(site_content, "PROPERTY_CODE", "ALPHA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True), patch.object(customer_site_page, "CUSTOMER_SITE_SAFE_MODE", True):
            result = await customer_site_page.customer_rooms(request_for(fake), locale="en")
        body = result.body.decode()
        self.assertIn("Alpha Studio &lt;safe&gt;", body)
        self.assertIn("Hotel ALPHA", body)
        self.assertNotIn("Три Короны", body)
        self.assertNotIn("3korony", body)
        self.assertNotIn("KGS / night", body)
        self.assertEqual(fake.room_types, categories)

    async def test_customer_rooms_unpublished_cannot_reveal_internal_categories(self):
        fake = FakeConnection(published_version=0, room_types=[{"name": "INTERNAL SECRET"}])
        with patch.object(site_content, "PROPERTY_CODE", "BETA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True), patch.object(customer_site_page, "CUSTOMER_SITE_SAFE_MODE", True):
            result = await customer_site_page.customer_rooms(request_for(fake), locale="ru")
        self.assertNotIn("INTERNAL SECRET", result.body.decode())
        self.assertEqual(result.headers["x-robots-tag"], "noindex, nofollow")

    async def test_customer_rooms_new_document_without_catalogue_stays_unpublished(self):
        new_document = {
            "hero": {"title": "Hotel BETA", "subtitle": "Beta stay"},
            "contacts": {"phone": "+996 555 111 222", "whatsapp": "+996 555 111 222", "email": "beta@example.test", "address": "Beta Avenue"},
            "seo": {"title": "Beta", "description": "Beta"},
        }
        fake = FakeConnection(new_document, published_version=1, room_types=[{"name": "NOT OWNER PUBLISHED"}])
        with patch.object(site_content, "PROPERTY_CODE", "BETA"), patch.object(site_content, "CUSTOMER_SITE_SAFE_MODE", True), patch.object(customer_site_page, "CUSTOMER_SITE_SAFE_MODE", True):
            result = await customer_site_page.customer_rooms(request_for(fake), locale="ru")
        self.assertNotIn("NOT OWNER PUBLISHED", result.body.decode())
        self.assertEqual(result.headers["x-robots-tag"], "noindex, nofollow")



if __name__ == "__main__":
    unittest.main()
