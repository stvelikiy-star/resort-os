"""Fail closed when RC3 source/migrations/rollout claims differ from reviewed truth."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from marina_rc3_source_gate import ROOT, RC3_FILE, check_files, git_blob_sha, validate


class RC3SourceLockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / RC3_FILE).read_text())

    def test_exact_current_source_is_accepted_without_claiming_deployment(self):
        self.assertEqual(validate(self.manifest, ROOT), [])
        self.assertIs(self.manifest["production_cutover_authorized"], False)

    def test_outdated_or_invalid_source_lock_is_rejected(self):
        for changed in (
            {"state": "PRODUCTION_READY"},
            {"migration_count": 38},
            {"external_staging_verified": True},
            {"ubuntu_restore_verified": True},
            {"production_deployed": True},
            {"mobile_live_e2e_verified": True},
            {"production_cutover_authorized": True},
            {"required_workflows": []},
            {"source_branch": "main"},
        ):
            with self.subTest(changed=changed):
                manifest = {**self.manifest, **changed}
                self.assertTrue(validate(manifest, ROOT))

    def test_one_modified_critical_source_blob_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        first = sorted(manifest["critical_git_blobs"])[0]
        manifest["critical_git_blobs"][first] = "0" * 40
        self.assertIn("reviewed critical source changed: " + first, check_files(manifest, ROOT))

    def test_git_blob_sha_tracks_real_bytes(self):
        self.assertEqual(git_blob_sha(b"test\\n"),
                         __import__("hashlib").sha1(b"blob 5\\0test\\n").hexdigest())


if __name__ == "__main__":
    unittest.main()
