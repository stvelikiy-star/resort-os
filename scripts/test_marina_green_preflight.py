"""Offline synthetic acceptance for the ASKA GREEN-API preflight."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

import marina_green_preflight as p

ENV = {
    "PROPERTY_CODE": "HOTEL_TEST",
    "GREEN_API_PROPERTY_CODE": "HOTEL_TEST",
    "GREEN_API_URL": "https://7103.api.greenapi.com",
    "GREEN_API_ID_INSTANCE": "7103000000",
    "GREEN_API_TOKEN_INSTANCE": "fake_provider_token_123456",
    "GREEN_API_EXPECTED_PHONE": "+996555000000",
    "GREEN_API_EXPECTED_WEBHOOK_URL": "https://hotel.example.test/api/v1/automation/green-api/webhook",
    "GREEN_API_WEBHOOK_TOKEN": "fake_callback_token_12345678901234567890",
}
STATE = {"stateInstance": "authorized"}
SETTINGS = {
    "wid": "996555000000@c.us",
    "webhookUrl": ENV["GREEN_API_EXPECTED_WEBHOOK_URL"],
    "webhookUrlToken": "Bearer " + ENV["GREEN_API_WEBHOOK_TOKEN"],
    "incomingWebhook": "yes",
    "outgoingWebhook": "yes",
}


class PreflightTests(unittest.TestCase):
    def test_healthy_configuration_does_not_claim_messaging(self):
        result = p.evaluate(p.configuration(ENV), STATE, SETTINGS)
        for key in ("authorized", "expected_phone_matches", "webhook_url_matches",
                    "webhook_credential_matches", "incoming_enabled", "delivery_status_enabled"):
            self.assertTrue(result[key], key)
        self.assertFalse(result["messaging_verified"])
        self.assertFalse(result["ai_auto_send_verified"])

    def test_reject_wrong_property_and_credentials(self):
        for changes in (
            {"GREEN_API_PROPERTY_CODE": "OTHER"},
            {"PROPERTY_CODE": "MARINA_DEMO", "GREEN_API_PROPERTY_CODE": "MARINA_DEMO"},
            {"MARINA_TENANT_CONTEXT_ENABLED": "true"},
            {"GREEN_API_URL": "https://api.greenapi.com.evil.test"},
            {"GREEN_API_URL": "http://api.greenapi.com"},
            {"GREEN_API_URL": "https://user@api.greenapi.com"},
            {"GREEN_API_EXPECTED_PHONE": "996555000000"},
            {"GREEN_API_EXPECTED_WEBHOOK_URL": "http://hotel.example.test/api/v1/automation/green-api/webhook"},
            {"GREEN_API_EXPECTED_WEBHOOK_URL": "https://hotel.example.test/another-path"},
            {"GREEN_API_WEBHOOK_TOKEN": "x"},
            {"GREEN_API_TOKEN_INSTANCE": ENV["GREEN_API_WEBHOOK_TOKEN"]},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                p.configuration({**ENV, **changes})

    def test_wrong_number_webhook_or_flags(self):
        for field, value, key in (
            ("wid", "996555000001@c.us", "expected_phone_matches"),
            ("webhookUrl", "", "webhook_url_matches"),
            ("webhookUrlToken", "wrong", "webhook_credential_matches"),
            ("webhookUrlToken", "неверный", "webhook_credential_matches"),
            ("incomingWebhook", "no", "incoming_enabled"),
            ("outgoingWebhook", "no", "delivery_status_enabled"),
        ):
            with self.subTest(field=field):
                self.assertFalse(p.evaluate(p.configuration(ENV), STATE, {**SETTINGS, field:value})[key])

    def test_restricted_account_not_ready(self):
        for state in ("notAuthorized", "blocked", "suspended", "starting", "yellowCard", "sleepMode"):
            self.assertFalse(p.evaluate(p.configuration(ENV), {"stateInstance": state}, SETTINGS)["authorized"])

    def test_read_only_method_allowlist(self):
        for method in ("sendMessage", "setSettings", "logout", "qr"):
            with self.assertRaises(ValueError):
                p.read_provider(p.configuration(ENV), method)

    def test_cli_secret_safe_and_correct_exit(self):
        for state, expected in ((STATE, 0), ({"stateInstance": "suspended"}, 2)):
            out = io.StringIO()
            with patch.dict(os.environ, ENV, clear=True), patch.object(p, "read_provider", side_effect=[state, SETTINGS]) as read, contextlib.redirect_stdout(out):
                self.assertEqual(p.main(), expected)
            self.assertEqual([call.args[1] for call in read.call_args_list], ["getStateInstance", "getSettings"])
            self.assertEqual(json.loads(out.getvalue())["provider_configuration_matches"], expected == 0)
            for key in ("GREEN_API_TOKEN_INSTANCE", "GREEN_API_WEBHOOK_TOKEN", "GREEN_API_EXPECTED_PHONE"):
                self.assertNotIn(ENV[key], out.getvalue())

    def test_provider_exception_does_not_leak_token(self):
        out = io.StringIO()
        with patch.dict(os.environ, ENV, clear=True), patch.object(p, "read_provider", side_effect=RuntimeError(ENV["GREEN_API_TOKEN_INSTANCE"])), contextlib.redirect_stdout(out):
            self.assertEqual(p.main(), 2)
        self.assertNotIn(ENV["GREEN_API_TOKEN_INSTANCE"], out.getvalue())

if __name__ == "__main__":
    unittest.main()
