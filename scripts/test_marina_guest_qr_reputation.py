#!/usr/bin/env python3
"""Offline contract test: existing PIN session, hotel history and review isolation."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "services/api/app/guest_stay_reviews.py").read_text()
entry = (ROOT / "services/api/app/app_entry.py").read_text()
history = (ROOT / "services/api/app/guest_crm.py").read_text()
growth = (ROOT / "services/api/app/growth_control.py").read_text()
page = (ROOT / "apps/web/app/g/[token]/page.tsx").read_text()
ui = (ROOT / "apps/web/components/GuestStayReview.tsx").read_text()
migration = (ROOT / "packages/database/prisma/migrations/zz110_marina_guest_stay_reviews_20261022/migration.sql").read_text()

class GuestReputationContract(unittest.TestCase):
    def test_api_is_valid_and_uses_verified_stay(self):
        ast.parse(api)
        self.assertIn("authorized_context(conn, token, tc_guest_session)", api)
        self.assertEqual(api.count("authorized_context(conn, token, tc_guest_session)"), 3)
        self.assertIn('"propertyId"=$1 AND "stayId"=$2 AND "guestId"=$3', api)
        self.assertIn("ON CONFLICT (\"stayId\")", api)
        self.assertIn('app.include_router(guest_stay_reviews_router)', entry)

    def test_qr_never_exposes_guest_without_pin(self):
        self.assertIn('body?.authenticated && body?.active_stay', ui)
        self.assertIn('credentials:"include"', ui)
        self.assertIn('rating<=3', ui)
        self.assertIn("<GuestStayReview token={token} />", page)
        self.assertNotIn("GREEN_API_TOKEN", ui)
        self.assertIn("Orders are not available yet.", ui)

    def test_review_is_in_guest_history_and_manager_queue(self):
        ast.parse(history)
        ast.parse(growth)
        self.assertIn('"guest_review": reviews_by_stay.get(str(row["id"]))', history)
        self.assertIn('guest_stay_reviews', growth)
        self.assertIn('manager_attention_required', growth)
        self.assertIn('outbound_authority', growth)

    def test_database_isolation_and_validation(self):
        self.assertIn('CONSTRAINT guest_stay_reviews_stay_unique UNIQUE ("stayId")', migration)
        self.assertIn('rating BETWEEN 1 AND 5', migration)
        self.assertIn('char_length(comment) <= 2000', migration)
        self.assertIn('"propertyId" uuid NOT NULL', migration)

if __name__ == "__main__":
    unittest.main()
