"""P0 MARINA: finance and reservation payments must use verified hotel context.

This is a source regression test; PostgreSQL and HTTP scenarios run in
Finance Control CI and Two-Property Isolation CI.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarinaFinanceTenantBoundary(unittest.TestCase):
    def test_reservation_payments_never_resolve_from_hotel_code(self):
        path = ROOT / "services/api/app/reservation_payments.py"
        source = path.read_text(encoding="utf-8")
        self.assertIn("from .auth import require_roles, trusted_property_id", source)
        self.assertEqual(source.count("pid = await trusted_property_id(conn, user)"), 3)
        self.assertNotIn('SELECT id FROM properties WHERE code=$1', source)
        for handler in (
            "reservation_acquiring_readiness",
            "cancellation_finance_review",
            "record_reservation_payment",
        ):
            body = source.split("async def " + handler + "(", 1)[1].split("\n\n@router.", 1)[0]
            self.assertIn("pid = await trusted_property_id(conn, user)", body, handler)
            self.assertIn('"propertyId"', body, handler)

    def test_hotel_finance_uses_authenticated_property_id(self):
        source = (ROOT / "services/api/app/hotel_finance.py").read_text(encoding="utf-8")
        self.assertIn("from .auth import require_roles, trusted_property_id", source)
        self.assertEqual(source.count("pid = await trusted_property_id(conn, user)"), 2)
        self.assertNotIn("properties WHERE code=$1", source)
        self.assertIn("'SELECT id,timezone,currency FROM properties WHERE id=$1', pid", source)
        for handler in ("set_payment_requirement", "finance_summary"):
            body = source.split("async def " + handler + "(", 1)[1].split("\n\n@router.", 1)[0]
            self.assertIn("pid = await trusted_property_id(conn, user)", body, handler)

    def test_payment_guard_keeps_bank_collection_disabled(self):
        source = (ROOT / "services/api/app/reservation_payments.py").read_text(encoding="utf-8")
        self.assertIn("provider_connected\": False", source)
        self.assertIn("PAYMENT_METHOD_NOT_ALLOWED", source)
        self.assertIn('payment_access = require_roles("OWNER", "MANAGER", module_grant=False)', source)


if __name__ == "__main__":
    unittest.main()
