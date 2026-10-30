"""Static safety contract for MARINA SMART Ubuntu read-only launch inventory."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "marina_target_readonly_inventory.sh"


class TargetInventorySafety(unittest.TestCase):
    def test_script_is_non_destructive(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertTrue(script.startswith("#!/usr/bin/env bash"))
        for forbidden in ("docker compose up", "docker compose down", "docker rm ", "docker volume rm",
                          "prisma migrate deploy", "pg_restore ", "DROP DATABASE", "docker exec ",
                          "source .env", "cat .env", "printenv", "env |"):
            self.assertNotIn(forbidden, script, forbidden)
        self.assertIn("INVENTORY ONLY", script)
        self.assertIn("docker ps -a", script)
        self.assertIn("docker volume ls", script)
        self.assertIn("df -h", script)

    def test_production_demo_isolation_and_restore_are_explicit(self):
        script = SCRIPT.read_text(encoding="utf-8")
        for term in ("production DB+media backup", "isolated disposable DB",
                     "rollback", "demo compose projects", "identical reviewed commit"):
            self.assertIn(term, script)


if __name__ == "__main__":
    unittest.main()
