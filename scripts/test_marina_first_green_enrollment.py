"""A shared MARINA deployment may start with one real WhatsApp enrollment."""
import json
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app import auth
from app.shared_green_rc6_config import shared_green_rc6_config
from app.green_api_webhook import _webhook_bindings, _bearer_identity

TENANT = "11111111-1111-4111-8111-111111111111"
PROPERTY = "22222222-2222-4222-8222-222222222222"
PROVIDER = dict(tenant_id=TENANT,property_id=PROPERTY,property_code="HOTEL_A",provider_origin="https://7107.api.greenapi.com",instance="10000001",token="P"*48)
ADAPTER = dict(tenant_code="tenant_a",property_code="HOTEL_A",channel_code="GREEN_10000001",external_account_id="10000001",service_key="S"*48)
WEBHOOK = dict(tenant_code="tenant_a",property_code="HOTEL_A",channel_code="GREEN_10000001",instance="10000001",webhook_token="W"*48)
ENV = dict(APP_ENV="staging",MARINA_SHARED_GUEST_QR_RC4_ENABLED="true",MARINA_SHARED_INBOX_RC5_ENABLED="true",MARINA_SHARED_GREEN_RC6_ENABLED="true",MARINA_SHARED_GREEN_RC6_CONFIRM="REVIEWED_SHARED_GREEN_QR_STAGING_ONLY",MARINA_SHARED_GREEN_RC6_CONFIG_JSON=json.dumps([PROVIDER]),MARINA_SHARED_INBOX_RC5_ADAPTERS_JSON=json.dumps([ADAPTER]),MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON=json.dumps([WEBHOOK]))

class FirstGreenEnrollment(unittest.TestCase):
    def test_owner_binding(self):
        with patch.dict(os.environ,ENV), patch.object(auth,"MARINA_SHARED_AUTH_PREVIEW_ENABLED",True),patch.object(auth,"shared_auth_preview_guard"):
            user=dict(tenant_id=TENANT,property_id=PROPERTY,property_code="HOTEL_A")
            self.assertEqual(shared_green_rc6_config(user),(PROVIDER["provider_origin"],PROVIDER["instance"],PROVIDER["token"]))
            with self.assertRaises(HTTPException):
                shared_green_rc6_config({**user,"property_id":"33333333-3333-4333-8333-333333333333"})
    def test_callback_binding(self):
        with patch.dict(os.environ,ENV):
            self.assertEqual(len(_webhook_bindings()),1)
            self.assertEqual(_bearer_identity("Bearer "+WEBHOOK["webhook_token"])["bound_property_id"],PROPERTY)
            with self.assertRaises(HTTPException):
                _bearer_identity("Bearer "+"X"*48)
    def test_empty_and_wrong_instance(self):
        for rows in ([],[{**WEBHOOK,"instance":"20000002"}]):
            with patch.dict(os.environ,{**ENV,"MARINA_SHARED_GREEN_RC7_WEBHOOKS_JSON":json.dumps(rows)}):
                with self.assertRaises(HTTPException):
                    _webhook_bindings()

if __name__ == "__main__":
    unittest.main()
