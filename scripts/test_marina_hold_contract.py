"""Regression guard: HOLD cannot be consumed before validation.

Run: python -m unittest scripts/test_marina_hold_contract.py -v
This is a source contract; DB/browser race tests remain separate release gates.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HoldContractTests(unittest.TestCase):
    def test_booking_preview_precedes_hold_retirement(self):
        source = (ROOT / "services/api/app/pms_reservation_create.py").read_text()
        confirm = source.split('async def commit_grid_reservation(', 1)[1]
        preview = confirm.index("preview = await build_preview(")
        retirement = confirm.index("retired = await conn.fetchval(")
        reservation_insert = confirm.index("INSERT INTO reservations (")
        self.assertLess(preview, retirement)
        self.assertIn('"expiresAt" <= clock_timestamp()', confirm)
        self.assertLess(retirement, reservation_insert)
        self.assertIn('"confirmedReservationId"=$2', confirm)

    def test_expiry_is_database_backed(self):
        migration = (ROOT / "packages/database/prisma/migrations/zz114_marina_60minute_holds_20261029/migration.sql").read_text()
        self.assertIn("interval '60 minutes'", migration)
        self.assertIn('"propertyId"', migration)
        api = (ROOT / "services/api/app/pms_holds.py").read_text()
        self.assertIn('FOR UPDATE SKIP LOCKED', api)
        self.assertIn('UPDATE inventory_blocks SET active=false', api)

    def test_hold_dates_use_property_timezone(self):
        api = (ROOT / "services/api/app/pms_holds.py").read_text()
        self.assertIn('now() AT TIME ZONE timezone', api)
        self.assertIn('HOLD_DATES_IN_PAST', api)
        self.assertIn('payload.check_in < local_today', api)
        self.assertNotIn('payload.check_out <= local_today', api)

    def test_frontend_exposes_hold_and_resume(self):
        modal = (ROOT / "apps/admin/components/PMSNewReservationModal.tsx").read_text()
        grid = (ROOT / "apps/admin/components/PMSOwnerGrid.tsx").read_text()
        self.assertIn("HOLD на 60 минут", modal)
        self.assertIn("hold_id: hold?.id", modal)
        self.assertIn("initialHoldId:", grid)


if __name__ == "__main__":
    unittest.main()
