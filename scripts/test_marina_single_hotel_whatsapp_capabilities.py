#!/usr/bin/env python3
"""Fail-closed single-property WhatsApp mobile capabilities (provider not live)."""
import asyncio
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services"/"api"))
from fastapi import HTTPException
from app import channel_outbound as mod

class SingleHotelOutboundCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.assertFalse(mod.MARINA_SHARED_AUTH_PREVIEW_ENABLED)
        self.assertNotEqual(os.environ.get("MARINA_SHARED_GREEN_RC8_ENABLED"),"true")

    def test_reception_may_read_disconnected_whatsapp_status_without_telegram_grant(self):
        with patch.object(mod,"telegram_sales_inbound_configured",return_value=True),\
             patch.object(mod,"telegram_sales_outbound_configured",return_value=True):
            result=asyncio.run(mod.outbound_capabilities({"role":"RECEPTION"}))
        self.assertEqual(result["telegram"]["outbound_configured"],False)
        self.assertEqual(result["telegram"]["inbound_configured"],False)
        self.assertEqual(result["whatsapp"]["configured"],False)
        self.assertEqual(result["whatsapp"]["human_only"],True)
        self.assertEqual(result["whatsapp"]["queued_only"],True)
        self.assertEqual(result["whatsapp"]["max_text_length"],4096)

    def test_owner_can_read_legacy_telegram_status_but_whatsapp_remains_disconnected(self):
        with patch.object(mod,"telegram_sales_inbound_configured",return_value=True),\
             patch.object(mod,"telegram_sales_outbound_configured",return_value=True):
            result=asyncio.run(mod.outbound_capabilities({"role":"OWNER"}))
        self.assertTrue(result["telegram"]["outbound_configured"])
        self.assertFalse(result["whatsapp"]["configured"])
        self.assertTrue(result["whatsapp"]["human_only"])

    def test_reception_still_cannot_send_without_approved_green_adapter(self):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(mod.send_text_message(
                uuid.uuid4(),mod.OutboundTextCreate(text="Synthetic only"),
                object(),"synthetic-idempotency-unique",{"role":"RECEPTION"},
            ))
        self.assertEqual(caught.exception.status_code,403)

if __name__=="__main__":
    unittest.main()