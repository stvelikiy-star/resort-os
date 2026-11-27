"""Worker safety unit tests; database/provider effects are mocked."""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app import whatsapp_ai_worker as w


class WhatsAppWorkerTests(unittest.TestCase):
    def test_disabled_no_database_or_provider(self):
        app = SimpleNamespace()
        with patch.dict(os.environ, {}, clear=True), patch.object(w, "ai_sales_configured") as provider:
            self.assertEqual(asyncio.run(w.run_once(app)), "disabled")
            provider.assert_not_called()

    def test_unconfigured_provider_never_reads_database(self):
        with patch.dict(os.environ, {"ENABLE_GREEN_API_AI_DRAFT_WORKER":"true"}, clear=True), patch.object(w, "ai_sales_configured", return_value=False), patch.object(w, "single_property_binding") as binding:
            self.assertEqual(asyncio.run(w.run_once(SimpleNamespace())), "provider_not_configured")
            binding.assert_not_called()

    def test_busy_worker_does_not_claim(self):
        lane = SimpleNamespace(fetchval=AsyncMock(return_value=False), fetchrow=AsyncMock(), execute=AsyncMock())
        manager = MagicMock()
        manager.__aenter__ = AsyncMock(return_value=lane)
        manager.__aexit__ = AsyncMock(return_value=False)
        app = SimpleNamespace(state=SimpleNamespace(db=SimpleNamespace(acquire=lambda: manager)))
        with patch.dict(os.environ, {"ENABLE_GREEN_API_AI_DRAFT_WORKER":"true"}, clear=True), patch.object(w, "ai_sales_configured", return_value=True), patch.object(w, "single_property_binding", return_value={"bound_property_id":"12345678-1234-4234-8234-123456789abc"}):
            self.assertEqual(asyncio.run(w.run_once(app)), "busy")
        lane.fetchrow.assert_not_awaited()
        lane.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
