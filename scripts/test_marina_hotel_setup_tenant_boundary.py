"""MARINA tenant boundary regression for hotel settings."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SetupTenantContract(unittest.TestCase):
    def test_all_setup_routes_use_trusted_hotel(self):
        src = (ROOT / "services/api/app/hotel_setup.py").read_text()
        self.assertIn("from .auth import require_roles, trusted_property_id", src)
        self.assertIn("property_id = await trusted_property_id(conn, user)", src)
        self.assertIn("WHERE id=$1", src)
        self.assertEqual(src.count("await _property(conn, user)"), 12)
        self.assertNotIn('_property(conn, user["property_code"])', src)

if __name__ == "__main__":
    unittest.main()
