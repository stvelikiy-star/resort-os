import json
import unittest
from pathlib import Path
from marina_rc3_additive_gate import ROOT, RC2_FILE, RC3_FILE, validate_additive
from marina_rc3_source_gate import validate, git_blob_sha

class AdditiveRC3SourceGateTests(unittest.TestCase):
    def test_39_pinned_sql_and_zz115_accepted_without_production_claims(self):
        self.assertEqual(validate_additive(), [])
        self.assertIs(json.loads((ROOT/RC3_FILE).read_text())["production_cutover_authorized"], False)

    def test_historical_source_gate_git_blob_unchanged(self):
        manifest=json.loads((ROOT/RC3_FILE).read_text())
        pin=manifest["critical_git_blobs"]["scripts/marina_rc3_source_gate.py"]
        self.assertEqual(git_blob_sha((ROOT/"scripts/marina_rc3_source_gate.py").read_bytes()),pin)

    def test_fail_closed_for_unsafe_rc3_status_flags(self):
        original=json.loads((ROOT/RC3_FILE).read_text())
        for field in ("production_cutover_authorized","production_deployed",
                      "real_whatsapp_ai_verified","mobile_live_e2e_verified"):
            with self.subTest(field=field):
                changed={**original,field:True}
                self.assertTrue(validate(changed,ROOT))

    def test_39_original_migration_hashes_unchanged(self):
        import hashlib
        rc2=json.loads((ROOT/RC2_FILE).read_text())
        base=ROOT/"packages/database/prisma/migrations"
        for name,pin in rc2["migration_sha256"].items():
            with self.subTest(migration=name):
                self.assertEqual(hashlib.sha256((base/name/"migration.sql").read_bytes()).hexdigest(),pin)
        self.assertEqual(len(rc2["migration_sha256"]),39)

if __name__=="__main__":
    unittest.main()
