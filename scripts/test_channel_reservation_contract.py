"""Validate normalized intake without inventing missing provider information."""
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from pydantic import ValidationError
from app.channel_reservations import ChannelReservationImport, ledger_key


class ChannelContractTests(unittest.TestCase):
    def payload(self):
        return dict(provider="BOOKING_COM", external_id="external-123", revision=1, room_id=str(uuid.uuid4()), guest_name="Test guest", check_in="2027-08-01", check_out="2027-08-03", total_kgs=9000)

    def test_phone_not_fabricated(self):
        result = ChannelReservationImport(**self.payload())
        self.assertIsNone(result.phone)

    def test_missing_confirmation_data_rejected(self):
        for field in ("room_id", "guest_name", "check_in", "check_out", "total_kgs"):
            payload = self.payload()
            del payload[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ChannelReservationImport(**payload)

    def test_unsupported_or_invalid_values_rejected(self):
        for changes in ({"currency": "USD"}, {"provider": "UNKNOWN"}, {"revision": 0}, {"check_out": "2027-08-01"}, {"check_out": "2027-12-01"}, {"total_kgs": -1}, {"property_id": str(uuid.uuid4())}, {"external_id": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ChannelReservationImport(**{**self.payload(), **changes})

    def test_cancellation_without_creation_can_be_retained(self):
        result = ChannelReservationImport(provider="AIRBNB", external_id="cancel-first", revision=2, status="CANCELLED")
        self.assertIsNone(result.room_id)
        self.assertIsNone(result.total_kgs)

    def test_external_identity_is_stable_without_truncation(self):
        self.assertEqual(ledger_key("external-123"), ledger_key("external-123"))
        self.assertNotEqual(ledger_key("a" * 179 + "1"), ledger_key("a" * 179 + "2"))


if __name__ == "__main__":
    unittest.main()
