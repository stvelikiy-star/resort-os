import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from marina_rc441_monitor import publish_result


class RCMonitorNotificationTests(unittest.TestCase):
    def test_red_persists_private_state_and_deduplicates_age_updates(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "monitor.json"
            accepted = subprocess.CompletedProcess([], 0, "42\n", "")
            with patch("marina_rc441_monitor.subprocess.run", return_value=accepted) as send:
                self.assertEqual(publish_result(["backup age 30.00h exceeds 24.00h"], state, True, "test"), 2)
                self.assertEqual(publish_result(["backup age 30.08h exceeds 24.00h"], state, True, "test"), 2)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(json.loads(state.read_text())["last_notification"]["id"], "42")
                self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)
                publish_result(["HTTPS unavailable: api"], state, True, "test")
                self.assertEqual(send.call_count, 2)

    def test_failed_notification_remains_red_and_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "monitor.json"
            rejected = subprocess.CompletedProcess([], 1, "", "")
            with patch("marina_rc441_monitor.subprocess.run", return_value=rejected) as send:
                self.assertEqual(publish_result([], state, True, "test"), 2)
                self.assertEqual(json.loads(state.read_text())["status"], "RED")
                self.assertEqual(publish_result([], state, True, "test"), 2)
                self.assertEqual(send.call_count, 2)

    def test_recovery_notifies_once(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "monitor.json"
            accepted = subprocess.CompletedProcess([], 0, "43\n", "")
            with patch("marina_rc441_monitor.subprocess.run", return_value=accepted) as send:
                publish_result(["api unavailable"], state, True, "test")
                self.assertEqual(publish_result([], state, True, "test"), 0)
                self.assertEqual(publish_result([], state, True, "test"), 0)
                self.assertEqual(send.call_count, 2)
                self.assertEqual(json.loads(state.read_text())["status"], "GREEN")

    def test_invalid_previous_state_does_not_suppress_alert(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "monitor.json"
            state.write_text("[]")
            accepted = subprocess.CompletedProcess([], 0, "44\n", "")
            with patch("marina_rc441_monitor.subprocess.run", return_value=accepted) as send:
                self.assertEqual(publish_result(["api unavailable"], state, True, "test"), 2)
                send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
