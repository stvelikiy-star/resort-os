"""Validate normalized intake without inventing missing provider information."""
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from pydantic import ValidationError
from app.channel_reservations import ChannelReservationImport, ledger_key, parse_channel_csv


class ChannelContractTests(unittest.TestCase):
    def payload(self):
        return dict(provider="BOOKING_COM", external_id="external-123", revision=1, room_id=str(uuid.uuid4()), guest_name="Test guest", check_in="2027-08-01", check_out="2027-08-03", total_kgs=9000)

    def test_csv_accepts_bom_quoted_guest_and_cancellation(self):
        text = '\ufeffprovider,external_id,revision,status,room_id,guest_name,check_in,check_out,total_kgs\n'
        text += f'BOOKING_COM,csv-1,1,CONFIRMED,{uuid.uuid4()},"Guest, Name",2027-08-01,2027-08-03,9000\n'
        text += 'AIRBNB,csv-2,2,CANCELLED,,,,,\n'
        rows = parse_channel_csv(text)
        self.assertEqual(rows[0].guest_name, "Guest, Name")
        self.assertIsNone(rows[1].room_id)

    def test_csv_rejects_ambiguous_and_oversized_batches(self):
        for text in (
            'provider,external_id,revision,property_id\nAIRBNB,x,1,foreign',
            'provider,external_id,revision,revision\nAIRBNB,x,1,2',
            'provider,external_id,revision,status\nAIRBNB,x,1,CANCELLED,extra',
            'provider,external_id,revision,status\nAIRBNB,x,1',
            'provider,external_id,revision,status\n',
            'provider,external_id,revision,status\nAIRBNB,x,1,CANCELLED\nAIRBNB,x,2,CANCELLED',
            'provider,external_id,revision,status\n' + ''.join(f'AIRBNB,{i},1,CANCELLED\n' for i in range(101)),
        ):
            with self.subTest(text=text[:80]), self.assertRaises(ValueError):
                parse_channel_csv(text)

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
