"""Guard invariants for the destructive-risk shared PostgreSQL restore rehearsal."""
import os
from unittest.mock import patch
import unittest

from marina_shared_release_restore_ci import validate_restore_urls, SOURCE_NAME, TARGET_NAME

SOURCE = f"postgresql://ci:synthetic-only@127.0.0.1:5432/{SOURCE_NAME}?schema=public"
TARGET = f"postgresql://ci:synthetic-only@127.0.0.1:5432/{TARGET_NAME}?schema=public"
ENV = {
    "MARINA_SHARED_BROWSER_CI_CONFIRM": "DISPOSABLE_TWO_HOTEL_BROWSER_CI",
    "MARINA_SHARED_RESTORE_CI_CONFIRM": "ISOLATED_SHARED_TWO_HOTEL_RESTORE_ONLY",
    "APP_ENV": "staging",
    "MARINA_TENANT_CONTEXT_ENABLED": "true",
    "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "true",
    "PROPERTY_CODE": "MARINA_BROWSER_CI",
}


class RestoreSafety(unittest.TestCase):
    def test_only_explicit_ci_localhost_urls_accepted(self):
        with patch.dict(os.environ, ENV, clear=False):
            self.assertEqual(validate_restore_urls(SOURCE, TARGET),
                             (SOURCE.split("?")[0], TARGET.split("?")[0]))

    def test_reject_non_disposable_targets_and_query_injection(self):
        invalid = [
            TARGET.replace("127.0.0.1", "db.hotel.example"),
            TARGET.replace(TARGET_NAME, SOURCE_NAME),
            TARGET.replace(TARGET_NAME, "marina_smart"),
            TARGET.replace("schema=public", "host=remote.example"),
            TARGET.replace("schema=public", "schema=private"),
            TARGET.replace("schema=public", "sslmode=disable"),
            TARGET.replace("127.0.0.1", "localhost"),
            TARGET.replace(":5432", ":5444"),
            TARGET.replace("postgresql:", "https:"),
            TARGET+"#fragment",
        ]
        with patch.dict(os.environ, ENV, clear=False):
            for candidate in invalid:
                with self.subTest(candidate=candidate), self.assertRaises(RuntimeError):
                    validate_restore_urls(SOURCE, candidate)

    def test_fail_closed_without_both_confirmations_and_shared_flags(self):
        for key in ENV:
            if key == "MARINA_SHARED_BROWSER_CI_CONFIRM" or key == "MARINA_SHARED_RESTORE_CI_CONFIRM":
                wrong = "not-approved"
            else:
                wrong = "false"
            with self.subTest(key=key), patch.dict(os.environ, {**ENV,key:wrong}):
                with self.assertRaises(RuntimeError):
                    validate_restore_urls(SOURCE,TARGET)


if __name__=="__main__":
    unittest.main()
