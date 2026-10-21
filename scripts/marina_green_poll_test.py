#!/usr/bin/env python3
"""Synthetic, offline tests: no Green-API account, credentials or real guest data."""
import asyncio
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).with_name("marina_green_poll.py")
spec = importlib.util.spec_from_file_location("marina_green_poll", SCRIPT)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

GOOD = {
    "receiptId": 71,
    "body": {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {"idInstance": 1234567890},
        "idMessage": "AABBCCDDEE",
        "senderData": {"chatId": "996700000000@c.us", "senderName": "Demo"},
        "messageData": {"typeMessage": "textMessage",
                        "textMessageData": {"textMessage": "Есть свободный номер?"}},
    },
}
CFG = {"base": "https://api.green-api.com", "instance": "1234567890",
       "token": "synthetic-token", "key": "x"*40, "property": "MARINA_HOTEL01",
       "core": "http://127.0.0.1:8000"}


class Response:
    def __init__(self, code, data=None):
        self.status_code, self.data = code, data
    def json(self):
        return self.data
    def raise_for_status(self):
        if not 200 <= self.status_code < 300:
            raise RuntimeError("synthetic provider error")


class Client:
    def __init__(self, inbox_code=201, item=GOOD):
        self.inbox_code, self.item = inbox_code, item
        self.calls = []
    async def get(self, url, **kw):
        self.calls.append(("receive", url))
        return Response(200, self.item)
    async def post(self, url, **kw):
        self.calls.append(("inbox", url, kw["json"]))
        return Response(self.inbox_code, {})
    async def delete(self, url):
        self.calls.append(("ack", url))
        return Response(200, {})


class GreenAdapterTests(unittest.TestCase):
    def test_route_one_hotel_and_ack_after_storage(self):
        c = Client()
        self.assertEqual(asyncio.run(adapter.process_one(c, CFG)), "INGESTED")
        self.assertEqual([x[0] for x in c.calls], ["receive", "inbox", "ack"])
        payload = c.calls[1][2]
        self.assertEqual(payload["channel_code"], "GREEN_1234567890")
        self.assertEqual(payload["idempotency_key"], "green:1234567890:AABBCCDDEE")
        self.assertEqual(payload["external_conversation_id"], "996700000000@c.us")
        self.assertNotIn("password", payload)

    def test_core_failure_does_not_ack(self):
        c = Client(inbox_code=503)
        with self.assertRaises(adapter.AdapterError):
            asyncio.run(adapter.process_one(c, CFG))
        self.assertEqual([x[0] for x in c.calls], ["receive", "inbox"])

    def test_other_hotel_does_not_ack(self):
        other = {**GOOD, "body": {**GOOD["body"], "instanceData": {"idInstance": 9999999999}}}
        c = Client(item=other)
        with self.assertRaises(adapter.AdapterError):
            asyncio.run(adapter.process_one(c, CFG))
        self.assertEqual([x[0] for x in c.calls], ["receive"])

    def test_skips_groups_without_ingesting(self):
        other = {**GOOD, "body": {**GOOD["body"], "senderData": {"chatId": "12345-123@g.us"}}}
        c = Client(item=other)
        self.assertEqual(asyncio.run(adapter.process_one(c, CFG)), "SKIPPED_UNSUPPORTED")
        self.assertEqual([x[0] for x in c.calls], ["receive", "ack"])

    def test_no_received_item(self):
        c = Client(item=None)
        self.assertEqual(asyncio.run(adapter.process_one(c, CFG)), "EMPTY")
        self.assertEqual([x[0] for x in c.calls], ["receive"])

    def test_fail_closed_configuration(self):
        with self.assertRaises(adapter.AdapterError):
            adapter.configuration({})
        with self.assertRaises(adapter.AdapterError):
            adapter.configuration({"GREEN_API_URL": "http://bad", "GREEN_API_ID_INSTANCE": "1234567890",
                                   "GREEN_API_TOKEN_INSTANCE": "abc", "AUTOMATION_SERVICE_KEY": "a"*32,
                                   "PROPERTY_CODE": "MARINA_HOTEL01"})


if __name__ == "__main__":
    unittest.main()
