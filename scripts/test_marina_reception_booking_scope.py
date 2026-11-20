"""RECEPTION can use only canonical CORE_RATE PMS booking in shared staging.

Source-level regression; the browser+PostgreSQL proof is in
scripts/marina_shared_https_pms_ci.mjs.
"""
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app import auth, pms_reservation_create as booking  # noqa: E402


def preview(**changes):
    values = {
        "room_id": uuid.uuid4(), "check_in": "2027-01-10",
        "check_out": "2027-01-12", "adults": 2,
        "guest_phone": "+996555771188",
    }
    return booking.GridReservationPreviewPayload(**(values | changes))


def commit(**changes):
    values = {
        **preview().model_dump(),
        "guest_name": "Synthetic Reception Guest",
        "phone": "+996555771188",
        "expected_total_kgs": 6000,
        "expected_pricing_source": "CORE_RATE",
    }
    return booking.GridReservationCommitPayload(**(values | changes))


class ReceptionBookingScopeTests(unittest.TestCase):
    def test_reception_can_only_use_shared_isolated_mode(self):
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", False):
            with self.assertRaises(HTTPException) as captured:
                booking.enforce_reception_booking_scope(preview())
        self.assertEqual(captured.exception.status_code, 403)

    def test_original_guest_identity_is_preserved_and_price_is_core_only(self):
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True):
            allowed = booking.enforce_reception_booking_scope(preview())
            approved_commit = booking.enforce_reception_booking_scope(commit())
        self.assertEqual(allowed.discount_percent, 0)
        self.assertIsNone(allowed.guest_phone)
        self.assertIsNone(allowed.manager_total_kgs)
        self.assertEqual(approved_commit.phone, "+996555771188")
        self.assertEqual(approved_commit.guest_name, "Synthetic Reception Guest")
        self.assertEqual(approved_commit.expected_total_kgs, 6000)
        self.assertIsNone(approved_commit.guest_phone)

    def test_manager_pricing_and_privileged_fields_are_refused(self):
        denied = (
            {"manager_total_kgs": 1},
            {"discount_percent": 25},
            {"discount_reason": "STAFF_OVERRIDE"},
            {"extra_bed_count": 1, "extra_bed_unit_kgs": 500},
            {"extra_bed_unit_kgs": 500},
            {"hold_id": uuid.uuid4()},
            {"agent_id": uuid.uuid4()},
        )
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True):
            for change in denied:
                with self.subTest(change=change), self.assertRaises(HTTPException) as captured:
                    booking.enforce_reception_booking_scope(preview(**change))
                self.assertEqual(captured.exception.status_code, 403)
                self.assertEqual(
                    captured.exception.detail["code"],
                    "RECEPTION_PRICE_OR_HOLD_OVERRIDE_FORBIDDEN",
                )

    def test_commit_cannot_assert_manager_override_source(self):
        with patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True):
            with self.assertRaises(HTTPException) as captured:
                booking.enforce_reception_booking_scope(commit(expected_pricing_source="MANAGER_OVERRIDE"))
        self.assertEqual(captured.exception.status_code, 403)
        self.assertEqual(captured.exception.detail["code"], "RECEPTION_CORE_RATE_REQUIRED")

    def test_no_new_duplicate_or_unreviewed_pms_route(self):
        source = (Path(__file__).resolve().parents[1] /
                  "services/api/app/pms_reservation_create.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('@router.post("/new/preview")'), 1)
        self.assertEqual(source.count('@router.post("/new/commit"'), 1)
        self.assertIn('manager_access = require_roles("OWNER", "MANAGER", "AGENT", "RECEPTION")', source)
        self.assertIn('payload = enforce_reception_booking_scope(payload)', source)


if __name__ == "__main__":
    unittest.main()
