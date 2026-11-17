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
from app import site_content  # noqa: E402


class FakeConnection:
    def __init__(self, published=None, published_version=0):
        self.published = published
        self.published_version = published_version
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


if __name__ == "__main__":
    unittest.main()
