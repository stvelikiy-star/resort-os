#!/usr/bin/env python3
"""Offline authorization and data integrity contract for optional resort navigation."""
import ast
from pathlib import Path
import unittest

root=Path(__file__).resolve().parents[1]
api=(root/"services/api/app/room_wayfinding.py").read_text()
migration=(root/"packages/database/prisma/migrations/zz111_marina_room_wayfinding_20261022/migration.sql").read_text()
room=(root/"apps/admin/components/RoomDetailModal.tsx").read_text()
guest=(root/"apps/web/components/GuestRoomDirections.tsx").read_text()
page=(root/"apps/web/app/g/[token]/page.tsx").read_text()
entry=(root/"services/api/app/app_entry.py").read_text()

class WayfindingContract(unittest.TestCase):
    def test_routes_compile_and_require_existing_authorization(self):
        ast.parse(api)
        self.assertIn('Depends(manager_access)',api)
        self.assertIn('trusted_property_id(conn, user)',api)
        self.assertIn('authorized_context(conn, token, tc_guest_session)',api)
        self.assertIn('app.include_router(room_wayfinding_router)',entry)
        self.assertIn('app.include_router(guest_wayfinding_router)',entry)

    def test_strict_property_and_room_id(self):
        self.assertIn('WHERE "propertyId"=$1 AND "roomId"=$2',api)
        self.assertIn('WHERE id=$1 AND "propertyId"=$2',api)
        self.assertIn('WHERE room_wayfinding."propertyId"=EXCLUDED."propertyId"',api)
        self.assertIn('UNIQUE("roomId")',migration)
        for check in ["coordinates_pair_check","latitude_range_check","longitude_range_check"]:
            self.assertIn(check,migration)

    def test_only_safe_public_navigation(self):
        self.assertIn('Only public HTTPS video links are allowed',api)
        self.assertIn('www.google.com/maps/search/',api)
        self.assertIn('GuestRoomDirections token={token}',page)
        self.assertIn('marina:guest-session-updated',guest)
        self.assertIn('credentials:"include"',guest)
        self.assertIn('RoomWayfindingPanel roomId={roomId}',room)
        self.assertNotIn('lock_pin',api.lower())
        self.assertNotIn('guest_id',migration.lower())

if __name__=="__main__":
    unittest.main()
