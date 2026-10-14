"""Reject any non-disposable target before the E2E can write fixtures."""
import unittest

from marina_two_property_restore_e2e import validate_ci_dsn


class RestoreSafetyTests(unittest.TestCase):
    def test_accept_only_disposable_local_databases(self):
        for host in ("localhost", "127.0.0.1", "[::1]"):
            value = f"postgresql://synthetic:synthetic@{host}:5432/marina_isolation_source?schema=public"
            self.assertNotIn("schema=", validate_ci_dsn(value))

    def test_reject_external_or_real_targets(self):
        for value in (
            "postgresql://synthetic:synthetic@hotel.example/marina_isolation_source",
            "postgresql://synthetic:synthetic@localhost/marina_production",
            "postgresql://synthetic:synthetic@localhost/postgres",
            "postgresql://synthetic:synthetic@localhost/marina_isolation_a%2Fb",
            "https://localhost/marina_isolation_source",
        ):
            with self.subTest(target=value), self.assertRaises(RuntimeError):
                validate_ci_dsn(value)


if __name__ == "__main__":
    unittest.main()
