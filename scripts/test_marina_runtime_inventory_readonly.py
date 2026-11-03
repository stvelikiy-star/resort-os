"""Unit checks for the safe MARINA runtime inventory collector (no Docker required)."""
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from marina_runtime_inventory_readonly import inventory

class RuntimeInventoryTests(TestCase):
    def test_absent_host_is_unknown_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            with patch("marina_runtime_inventory_readonly.command", return_value=None):
                result = inventory(base / "missing-repo", base / "missing-backups")
        self.assertIsNone(result["repo"]["head"])
        self.assertFalse(result["docker"]["available"])
        self.assertFalse(result["backups"]["integrity_checked"])

    def test_only_marina_containers_and_named_backup_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            backups = base / "backups"
            backups.mkdir()
            (backups / "marina-before-release.dump").write_bytes(b"fake")
            (backups / "unrelated.dump").write_bytes(b"fake")
            output = '\n'.join([
                '{"Names":"marina-hotel01-api-1","Image":"marina-api:test","State":"running","Status":"Up"}',
                '{"Names":"kol-platform-1","Image":"other","State":"running","Status":"Up"}'
            ])
            with patch("marina_runtime_inventory_readonly.command", return_value=output):
                result = inventory(base / "missing-repo", backups)
        self.assertEqual([x["name"] for x in result["docker"]["containers"]], ["marina-hotel01-api-1"])
        self.assertEqual([x["filename"] for x in result["backups"]["files"]], ["marina-before-release.dump"])
        self.assertFalse(result["backups"]["integrity_checked"])
