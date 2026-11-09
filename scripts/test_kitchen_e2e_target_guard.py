import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from kitchen_e2e_target_guard import validate_target

local=dict(base="http://127.0.0.1:8000",
    database_url="postgresql://resort:resort@localhost:5432/resort_os?schema=public",
    property_code="THREE_CROWNS",cookie_secure=False,rc426_confirm=None)
staging=dict(base="https://divine-gap-asking-manufacture.trycloudflare.com",
    database_url="postgresql://marina:generated@postgres:5432/marina_rc426_accept?schema=public",
    property_code="MARINA_FULL_CI",cookie_secure=True,
    rc426_confirm="ISOLATED_RC426_KITCHEN_E2E")

class KitchenE2ETargetGateTests(unittest.TestCase):
    def test_legacy_disposable_ci(self):
        validate_target(**local)
    def test_explicit_rc426_secure_https(self):
        validate_target(**staging)
    def test_reject_insecure_secure_cookie(self):
        with self.assertRaisesRegex(RuntimeError,"HTTPS"):
            validate_target(**{**staging,"base":"http://127.0.0.1:8000"})
    def test_reject_wrong_property(self):
        with self.assertRaisesRegex(RuntimeError,"non-synthetic"):
            validate_target(**{**staging,"property_code":"MARINA_HOTEL01"})
    def test_reject_real_database(self):
        with self.assertRaisesRegex(RuntimeError,"disposable"):
            validate_target(**{**staging,"database_url":"postgresql://marina:secret@postgres:5432/marina_production"})
    def test_reject_confirmation_missing(self):
        with self.assertRaisesRegex(RuntimeError,"confirmation"):
            validate_target(**{**staging,"rc426_confirm":None})
    def test_reject_passing_credentials_in_url(self):
        with self.assertRaisesRegex(RuntimeError,"credentials"):
            validate_target(**{**staging,"base":"https://u:pw@proxy.trycloudflare.com"})
    def test_reject_legacy_external_api(self):
        with self.assertRaisesRegex(RuntimeError,"localhost API"):
            validate_target(**{**local,"base":"https://external.example.com"})
    def test_reject_wrong_staging_hostname(self):
        with self.assertRaisesRegex(RuntimeError,"test HTTPS tunnel"):
            validate_target(**{**staging,"base":"https://example.com"})
    def test_reject_secure_cookie_disabled(self):
        with self.assertRaisesRegex(RuntimeError,"Secure"):
            validate_target(**{**staging,"cookie_secure":False})
if __name__=="__main__":
    unittest.main()