"""Read-only single-hotel provider readiness: never equate credentials to UAT."""
import unittest

from marina_single_hotel_provider_preflight import readiness

GOOD = {
    "PROPERTY_CODE": "MARINA_HOTEL_A",
    "ENABLE_GREEN_API_CONNECTION": "true",
    "GREEN_API_PROPERTY_CODE": "MARINA_HOTEL_A",
    "GREEN_API_URL": "https://api.green-api.com",
    "GREEN_API_ID_INSTANCE": "7103000000",
    "GREEN_API_TOKEN_INSTANCE": "SYNTHETIC_PROVIDER_TOKEN",
    "AUTOMATION_SERVICE_KEY": "X" * 40,
    "OPENAI_API_KEY": "sk-synthetic-not-real",
    "OPENAI_PUBLIC_ASSISTANT_MODEL": "synthetic-test-model",
    "OPENAI_API_BASE_URL": "https://api.openai.com/v1",
}

class SingleHotelProviderPreflight(unittest.TestCase):
    def test_empty_environment_is_no_go(self):
        result = readiness({})
        self.assertEqual(result["commercial_status"], "NO_GO")
        self.assertEqual(result["whatsapp_config"], "BLOCKED")

    def test_well_formed_credentials_still_not_live_pass(self):
        result = readiness(GOOD)
        self.assertEqual(result["whatsapp_config"], "CONFIGURED_NOT_VERIFIED")
        self.assertEqual(result["marina_ai_config"], "CONFIGURED_NOT_VERIFIED")
        self.assertEqual(result["whatsapp_live_delivery"], "NOT_ACCEPTED")
        self.assertEqual(result["marina_ai_live_handoff"], "NOT_ACCEPTED")
        self.assertEqual(result["commercial_status"], "NO_GO")

    def test_wrong_hotel_never_proceeds(self):
        result = readiness({**GOOD, "GREEN_API_PROPERTY_CODE": "MARINA_HOTEL_B"})
        self.assertEqual(result["whatsapp_config"], "BLOCKED")

    def test_demo_cannot_pass(self):
        result = readiness({**GOOD, "PROPERTY_CODE": "MARINA_DEMO", "GREEN_API_PROPERTY_CODE": "MARINA_DEMO"})
        self.assertEqual(result["commercial_status"], "NO_GO")
        self.assertEqual(result["property_binding"], "BLOCKED")

    def test_provider_hostname_mismatch(self):
        result = readiness({**GOOD, "GREEN_API_URL": "https://api.green-api.com.evil.example"})
        self.assertEqual(result["whatsapp_config"], "BLOCKED")

    def test_no_secret_in_report(self):
        result = readiness(GOOD)
        import json
        string = json.dumps(result)
        self.assertNotIn(GOOD["OPENAI_API_KEY"], string)
        self.assertNotIn(GOOD["GREEN_API_TOKEN_INSTANCE"], string)
        self.assertNotIn(GOOD["AUTOMATION_SERVICE_KEY"], string)

    def test_invalid_ai_url(self):
        result = readiness({**GOOD,"OPENAI_API_BASE_URL":"https://api.openai.com.evil.test/v1"})
        self.assertEqual(result["marina_ai_config"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
