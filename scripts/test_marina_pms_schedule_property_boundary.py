"""Dependency-free regression for PMS schedule's authenticated hotel boundary."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'services/api/app/pms_chessboard.py').read_text()
MODULE=ast.parse(SOURCE)

def function(name):
    return next(n for n in MODULE.body if isinstance(n,ast.AsyncFunctionDef) and n.name==name)

def body(name):
    return ast.get_source_segment(SOURCE,function(name))

class PmsSchedulePropertyBoundary(unittest.TestCase):
    def test_property_resolution_uses_authenticated_id_not_display_code(self):
        fn=body('_property')
        self.assertIn('trusted_property_id(conn, user)',fn)
        self.assertIn('WHERE id=$1',fn)
        self.assertNotIn('WHERE code=$1',fn)
        self.assertNotIn('property_code',fn)

    def test_preview_commit_both_use_user_scope(self):
        for name in ('preview_schedule','commit_schedule'):
            with self.subTest(name=name):
                fn=body(name)
                self.assertIn('await _property(conn, user)',fn)
                self.assertNotIn('user["property_code"]',fn)
                self.assertIn('await _reservation(conn, reservation_id, prop["id"]',fn)
                self.assertIn('async with conn.transaction():',fn)

    def test_expired_holds_scoped_within_transaction(self):
        for name in ('preview_schedule','commit_schedule'):
            with self.subTest(name=name):
                fn=body(name)
                self.assertIn('if MARINA_SHARED_AUTH_PREVIEW_ENABLED:',fn)
                self.assertIn('await expire_holds(conn, prop["id"])',fn)
                self.assertLess(fn.index('async with conn.transaction():'),fn.index('await expire_holds(conn, prop["id"])'))
                self.assertLess(fn.index('await expire_holds(conn, prop["id"])'),fn.index('await _reservation(conn, reservation_id, prop["id"]'))

    def test_checkin_rejects_room_with_open_stay_before_activation(self):
        stays_source = (ROOT / 'services/api/app/stays.py').read_text()
        stays_module = ast.parse(stays_source)
        checkin = next(
            node for node in stays_module.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == 'check_in'
        )
        source = ast.get_source_segment(stays_source, checkin)
        self.assertIn('FROM room_assignments', source)
        self.assertIn('"endedAt" IS NULL', source)
        self.assertIn('CHECK_IN_ROOM_OCCUPIED', source)
        self.assertIn('CHECK_OUT_CURRENT_STAY_FIRST', source)
        self.assertIn('status_code=409', source)
        self.assertLess(
            source.index('FROM room_assignments'),
            source.index('await activate_stay('),
        )


if __name__=='__main__':
    unittest.main()
