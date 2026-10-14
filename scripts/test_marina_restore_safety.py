"""Reject any non-disposable target before the E2E can write fixtures."""
import unittest
from unittest.mock import AsyncMock, patch

from marina_two_property_restore_e2e import validate_ci_dsn, ensure_empty_source, ensure_empty_target


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
            "postgresql://synthetic:synthetic@localhost/marina_isolation_source?host=hotel.example",
            "postgresql://synthetic:synthetic@localhost/marina_isolation_source?port=9999",
        ):
            with self.subTest(target=value), self.assertRaises(RuntimeError):
                validate_ci_dsn(value)


class PopulatedDatabaseSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_populated_restore_target_is_rejected_and_connection_closed(self):
        conn = AsyncMock()
        conn.fetchval.return_value = 1
        with patch("marina_two_property_restore_e2e.asyncpg.connect", AsyncMock(return_value=conn)):
            with self.assertRaisesRegex(RuntimeError, "target is not empty"):
                await ensure_empty_target("unused-test-target")
        conn.close.assert_awaited_once()

    async def test_existing_tenant_is_rejected_even_without_property(self):
        conn = AsyncMock()
        conn.fetchval.side_effect = [0, 1]
        with patch("marina_two_property_restore_e2e.asyncpg.connect", AsyncMock(return_value=conn)):
            with self.assertRaisesRegex(RuntimeError, "contains tenants"):
                await ensure_empty_source("unused-test-source")
        conn.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
