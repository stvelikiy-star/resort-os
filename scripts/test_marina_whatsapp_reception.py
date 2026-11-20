#!/usr/bin/env python3
"""No-DB source contract + behavior checks for reception WhatsApp isolation."""
import ast
import asyncio
import pathlib
import unittest
import uuid
from typing import Any

SRC = pathlib.Path(__file__).resolve().parents[1] / "services/api/app/inbox.py"
code = SRC.read_text()
tree = ast.parse(code)
functions = {n.name: n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)}


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code


isolated = compile(ast.Module(body=[functions["check_reception_whatsapp"]], type_ignores=[]), str(SRC), "exec")
context = {"uuid": uuid, "Any": Any, "HTTPException": HTTPException}
exec(isolated, context)
check = context["check_reception_whatsapp"]


class StubConnection:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def fetchval(self, query, *args):
        self.calls.append((query, args))
        return self.result


class ReceptionWhatsAppTests(unittest.TestCase):
    def test_reception_can_access_only_own_whatsapp(self):
        hotel = uuid.uuid4()
        dialog = uuid.uuid4()
        conn = StubConnection("WHATSAPP")
        asyncio.run(check(conn, hotel, dialog, {"role": "RECEPTION"}))
        self.assertEqual(len(conn.calls), 1)
        query, args = conn.calls[0]
        self.assertIn('c."propertyId"=$2', query)
        self.assertIn("ch.kind::text", query)
        self.assertEqual(args, (dialog, hotel))

    def test_reception_denied_other_channels_and_unowned_dialog(self):
        for kind in ("TELEGRAM", "INSTAGRAM", "WEBSITE", None):
            with self.subTest(kind=kind):
                conn = StubConnection(kind)
                with self.assertRaises(HTTPException) as err:
                    asyncio.run(check(conn, uuid.uuid4(), uuid.uuid4(), {"role": "RECEPTION"}))
                self.assertEqual(err.exception.status_code, 404)

    def test_owner_remains_unchanged(self):
        conn = StubConnection(None)
        asyncio.run(check(conn, uuid.uuid4(), uuid.uuid4(), {"role": "OWNER"}))
        self.assertEqual(conn.calls, [])

    def test_only_selected_routes_use_reception_dependency(self):
        allowed = {
            "list_conversations", "get_conversation", "set_conversation_status",
            "claim_conversation", "create_internal_note",
        }
        manager_only = {"assign_conversation", "link_reservation_request"}
        for name in allowed | manager_only:
            function = functions[name]
            source = ast.get_source_segment(code, function)
            dependency = "Depends(inbox_access)" if name in allowed else "Depends(manager_access)"
            self.assertIn(dependency, source, name)
        for name in {"set_conversation_status", "claim_conversation", "create_internal_note"}:
            source = ast.get_source_segment(code, functions[name])
            self.assertIn("await check_reception_whatsapp(", source, name)
        listing = ast.get_source_segment(code, functions["list_conversations"])
        self.assertIn("ch.kind::text='WHATSAPP'", listing)
        self.assertIn('user["role"] == "RECEPTION"', listing)
        detail = ast.get_source_segment(code, functions["get_conversation"])
        self.assertIn('row["channel_kind"] != "WHATSAPP"', detail)


if __name__ == "__main__":
    unittest.main()
