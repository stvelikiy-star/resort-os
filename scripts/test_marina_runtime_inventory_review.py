"""Fail-closed unit tests for MARINA metadata review."""
import unittest
from marina_runtime_inventory_review import review

class InventoryReviewTests(unittest.TestCase):
    def test_missing_evidence_never_approves_release(self):
        result = review({})
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertFalse(result["release_approved"])
        self.assertFalse(result["backup_restored"])
        self.assertTrue(result["findings"])

    def test_complete_metadata_is_still_not_production_acceptance(self):
        result = review({
            "schema": "marina-runtime-inventory-v1",
            "read_only": True,
            "repo": {"head": "a" * 40, "dirty_tracked": False},
            "docker": {"available": True, "containers": [{
                "name": "marina-hotel01-api-1",
                "image_id": "sha256:" + "b" * 64,
                "state": "running",
            }]},
            "backups": {"directory_present": True, "files": [{"filename": "marina-test.dump", "custom_archive_listing_ok": True}]},
        })
        self.assertEqual(result["status"], "INVENTORY_METADATA_COLLECTED")
        self.assertFalse(result["release_approved"])
        self.assertFalse(result["pms_accepted"])
        self.assertFalse(result["backup_restored"])

    def test_invalid_archive_does_not_pass_inventory_review(self):
        source = {
            "schema": "marina-runtime-inventory-v1", "read_only": True,
            "repo": {"head": "a" * 40, "dirty_tracked": False},
            "docker": {"available": True, "containers": [
                {"name": "marina-hotel01-api-1", "state": "running", "image_id": "sha256:" + "b" * 64}
            ]},
            "backups": {"directory_present": True, "files": [
                {"filename": "marina-broken.dump", "custom_archive_listing_ok": False}
            ]},
        }
        result = review(source)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("readable archive" in f for f in result["findings"]))

    def test_stopped_container_and_dirty_worktree_block_inventory(self):
        result = review({
            "schema": "marina-runtime-inventory-v1", "read_only": True,
            "repo": {"head": "a" * 40, "dirty_tracked": True},
            "docker": {"available": True, "containers": [
                {"name": "marina-hotel01-api-1", "state": "exited", "image_id": None}
            ]},
            "backups": {"directory_present": True, "files": []},
        })
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(any("Tracked files" in x for x in result["findings"]))
        self.assertTrue(any("not reported running" in x for x in result["findings"]))

if __name__ == "__main__":
    unittest.main()
