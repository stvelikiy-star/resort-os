"""Guest hotel identity must come from the QR's hotel, never demo constants."""
import asyncio
import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.guest_os import guest_property_info, generic_room_context
from fastapi import HTTPException


class HotelConnection:
    def __init__(self, hotels):
        self.hotels = hotels

    async def fetchrow(self, query, property_id):
        assert 'WHERE p.id=$1' in query
        assert 's."propertyId"=p.id' in query
        assert 'r."propertyId"=p.id' in query
        assert 'c."propertyId"=p.id' in query
        assert '"publishedJson"' in query and '"draftJson"' not in query
        return self.hotels.get(property_id)


class GuestPropertyTest(unittest.IsolatedAsyncioTestCase):
    async def test_two_hotels_keep_their_own_identity_contacts_and_checkout(self):
        first, second = uuid.uuid4(), uuid.uuid4()
        conn = HotelConnection({
            first: {"name": "Synthetic First", "check_out_time": "10:30",
                    "policy": json.dumps({"official_contact": "+996700000001", "wifi_info": "PRIVATE_WIFI"}),
                    "site_content": None},
            second: {"name": "Synthetic Second", "check_out_time": "12:00", "policy": {},
                     "site_content": {"contacts": {"phone": "+996700000002", "whatsapp": "996700000003"}}},
        })
        a, b = await guest_property_info(conn, first), await guest_property_info(conn, second)
        self.assertEqual(a["name"], "Synthetic First")
        self.assertEqual(a["check_out_time"], "10:30")
        self.assertEqual(a["official_contact"], "+996700000001")
        self.assertEqual(a["whatsapp"], "")
        self.assertEqual(b["name"], "Synthetic Second")
        self.assertEqual(b["official_contact"], "+996700000002")
        self.assertEqual(b["whatsapp"], "996700000003")
        self.assertNotIn("PRIVATE_WIFI", json.dumps(a))

    async def test_unknown_settings_do_not_invent_contacts(self):
        property_id = uuid.uuid4()
        info = await guest_property_info(HotelConnection({property_id: {
            "name": "Synthetic Empty", "check_out_time": None,
            "policy": None, "site_content": None,
        }}), property_id)
        self.assertIsNone(info["check_out_time"])
        self.assertEqual(info["official_contact"], "")
        self.assertEqual(info["whatsapp"], "")

    async def test_missing_hotel_fails_closed(self):
        with self.assertRaises(HTTPException) as error:
            await guest_property_info(HotelConnection({}), uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)

    async def test_before_pin_only_hotel_name_is_returned(self):
        qr = {"room_code": "101", "room_name": "Synthetic Room", "room_type_name": "Standard",
              "buildingOrZone": None, "floorLabel": None}
        body = generic_room_context(qr, True, {"name": "Synthetic Hotel", "official_contact": "private"})
        self.assertEqual(body["property"], {"name": "Synthetic Hotel"})
        self.assertFalse(body["authenticated"])
        self.assertIsNone(body["guest"])
        self.assertIsNone(body["stay"])


if __name__ == "__main__":
    unittest.main()
