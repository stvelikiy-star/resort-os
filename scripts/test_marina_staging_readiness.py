#!/usr/bin/env python3
"""Offline contract tests for the read-only MARINA staging readiness probe."""
import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

import marina_staging_readiness as probe


class ReadinessTests(unittest.TestCase):
    def run_gate(self, arguments, answer):
        output = io.StringIO()
        with patch.object(sys, "argv", ["probe"] + arguments), patch.object(probe, "request", side_effect=answer) as req, contextlib.redirect_stdout(output):
            result = probe.main()
        return result, json.loads(output.getvalue()), req.call_args_list

    def test_all_endpoints_success(self):
        code, body, calls = self.run_gate(
            ["--api", "https://api.example.test", "--web", "https://web.example.test",
             "--admin", "https://admin.example.test", "--staff", "https://staff.example.test"],
            [(200, "{}")] * 5)
        self.assertEqual(code, 0)
        self.assertTrue(body["all_pass"])
        self.assertEqual([c.args[1] for c in calls], ["/health/live", "/health/ready", "/", "/", "/"])

    def test_ready_failure_is_not_live_success(self):
        code, body, _ = self.run_gate(
            ["--api", "https://api.example.test"],
            [(200, "{}"), (503, "not ready")])
        self.assertEqual(code, 1)
        self.assertFalse(body["all_pass"])

    def test_connection_error_fails_closed(self):
        code, body, _ = self.run_gate(
            ["--api", "https://api.example.test"],
            OSError("offline"))
        self.assertEqual(code, 1)
        self.assertEqual(len(body["results"]), 2)
        self.assertTrue(all(not item["pass"] for item in body["results"]))

    def test_no_remote_http(self):
        with patch.object(sys, "argv", ["probe", "--api", "http://public.example.test"]):
            with self.assertRaises(SystemExit):
                probe.main()

    def test_no_embedded_credentials(self):
        with patch.object(sys, "argv", ["probe", "--api", "https://user:password@api.example.test"]):
            with self.assertRaises(SystemExit):
                probe.main()

    def test_no_path_on_origin(self):
        with patch.object(sys, "argv", ["probe", "--api", "https://api.example.test/private"]):
            with self.assertRaises(SystemExit):
                probe.main()


if __name__ == "__main__":
    unittest.main()
