"""Behavioral access tests: real routers/policy, fake DB and AI provider only."""
import asyncio
import datetime
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import guest_assistant as guest, guest_requests, marina_assistant as staff
from app.auth import current_user


class Connection:
    def __init__(self):
        self.queries = []
        self.pid = uuid.uuid4()

    async def __aenter__(self): return self
    async def __aexit__(self, *args): pass

    async def fetchrow(self, sql, *args):
        self.queries.append((sql, args))
        if "FROM properties" in sql:
            return {"id": self.pid, "code": "HOTEL_A", "name": "Hotel A", "timezone": "UTC"}
        if 'AS total' in sql:
            return {"total": 3, "clean": 2, "dirty": 1, "in_inspection": 0, "tech_block": 0}
        return {}

    async def fetchval(self, sql, *args):
        self.queries.append((sql, args))
        return datetime.date(2026, 10, 26) if "AT TIME ZONE $1" in sql else 0

    async def fetch(self, sql, *args):
        self.queries.append((sql, args))
        return []

    def acquire(self): return self


def request(conn):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=conn)))


def user(role, modules=None):
    result = {"id": str(uuid.uuid4()), "role": role, "property_code": "HOTEL_A"}
    if modules is not None:
        result.update(module_permissions=modules, module_permissions_custom=True)
    return result


class StaffPermissions(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_roles_denied_before_database(self):
        for role in ["MAID", "TECHNICIAN", "COOK", "WAITER", "AGENT", "DINING_STAFF", "STORE_STAFF", "GUEST", "UNKNOWN"]:
            conn = Connection()
            with self.assertRaises(HTTPException) as error:
                await staff._safe_live_context(request(conn), user(role), "PMS")
            self.assertEqual(error.exception.status_code, 403)
            self.assertEqual(conn.queries, [])

    async def test_empty_custom_permissions_reads_no_operational_data(self):
        conn = Connection()
        snapshot = await staff._live_context(request(conn), user("MANAGER", []), "PMS")
        self.assertNotIn("hotel", snapshot)
        self.assertNotIn("dining", snapshot)
        self.assertEqual(len(conn.queries), 2)  # property and local date only

    async def test_each_scope_is_independent_and_queries_are_guarded(self):
        expected = {
            "PMS": {"room_counts", "occupancy", "rooms_requiring_attention", "active_inventory_holds", "arrivals_today", "departures_today", "active_reservations"},
            "RESERVATIONS": {"arrivals_today", "departures_today", "active_reservations"},
            "OPS": {"task_counts", "active_tasks"},
            "REQUESTS": {"reservation_request_counts"},
            "FINANCE": {"finance"},
            "DINING": set(),
        }
        for module, keys in expected.items():
            conn = Connection()
            snapshot = await staff._live_context(request(conn), user("MANAGER", [module]), module)
            self.assertEqual(set(snapshot.get("hotel", {})), keys, module)
            self.assertEqual("dining" in snapshot, module == "DINING")
            queries = "\n".join(q for q, _ in conn.queries)
            if module != "OPS": self.assertNotIn("FROM operational_tasks", queries)
            if module != "DINING": self.assertNotIn("FROM kitchen_orders", queries)
            if module not in {"PMS", "RESERVATIONS", "FINANCE"}: self.assertNotIn("FROM payments", queries)
            if module not in {"REQUESTS", "FINANCE"}: self.assertNotIn("FROM reservation_requests", queries)
            for sql, args in conn.queries:
                if "FROM properties" not in sql and "AT TIME ZONE $1" not in sql:
                    self.assertIn(conn.pid, args, sql)  # authenticated property is bound

    async def test_owner_and_reception_defaults(self):
        owner = await staff._live_context(request(Connection()), user("OWNER"), "PMS")
        self.assertIn("finance", owner["hotel"])
        self.assertIn("dining", owner)
        reception = await staff._live_context(request(Connection()), user("RECEPTION"), "PMS")
        self.assertIn("arrivals_today", reception["hotel"])
        self.assertNotIn("finance", reception["hotel"])
        self.assertNotIn("task_counts", reception["hotel"])

    async def test_navigation_and_capabilities_follow_permissions(self):
        payload = staff.MarinaAssistantRequest(messages=[{"role": "user", "content": "финансы"}])
        self.assertIsNone(staff._navigation_suggestion(payload, user("MANAGER", ["PMS"])))
        self.assertEqual(staff._navigation_suggestion(payload, user("MANAGER", ["FINANCE"]))["screen"], "FINANCE")
        caps = await staff.marina_assistant_capabilities(user("MANAGER", []))
        self.assertFalse(caps["live_scope"]["hotel"])
        self.assertFalse(caps["live_scope"]["dining"])


class RouterPermissions(unittest.TestCase):
    def test_staff_endpoints_reject_disallowed_roles_without_provider(self):
        for role in ["MAID", "TECHNICIAN", "COOK", "WAITER", "AGENT"]:
            app = FastAPI(); app.include_router(staff.router)
            app.dependency_overrides[current_user] = lambda: user(role)
            with TestClient(app) as client, patch.object(staff, "_ask_openai", new_callable=AsyncMock) as provider:
                self.assertEqual(client.get("/api/v1/assistant/capabilities").status_code, 403)
                self.assertEqual(client.post("/api/v1/assistant/chat", json={"messages": [{"role": "user", "content": "PMS"}]}).status_code, 403)
                provider.assert_not_awaited()

    def test_staff_route_uses_filtered_context_for_provider(self):
        app = FastAPI(); app.include_router(staff.router); app.state.db = Connection()
        app.dependency_overrides[current_user] = lambda: user("MANAGER", [])
        with TestClient(app) as client, patch.object(staff, "_ask_openai", new_callable=AsyncMock, return_value="Unknown") as provider:
            result = client.post("/api/v1/assistant/chat", json={"messages": [{"role": "user", "content": "show finance"}]})
            self.assertEqual(result.status_code, 200)
            bundle = json.loads(provider.await_args.args[0].split("VERIFIED KNOWLEDGE, LIVE CONTEXT AND CONVERSATION:\n")[1])
            self.assertNotIn("hotel", bundle["live_context"])
            self.assertFalse(bundle["property_rules"]["available"])

    def test_guest_isolation_and_revocation(self):
        sid, gid, qid, pid, room = [uuid.uuid4() for _ in range(5)]
        qr = {"qr_id": qid, "propertyId": pid, "roomId": room, "room_code": "101"}
        stay = {"stayId": sid, "guestId": gid, "checkIn": "2026-10-25", "checkOut": "2026-10-28"}
        valid = {"id": uuid.uuid4(), "stayId": sid, "guestId": gid, "roomQrId": qid}
        cases = [(qr, stay, None, 401), (qr, None, valid, 401), (None, stay, valid, 404),
                 (qr, stay, {**valid, "stayId": uuid.uuid4()}, 401),
                 (qr, stay, {**valid, "guestId": uuid.uuid4()}, 401),
                 (qr, stay, {**valid, "roomQrId": uuid.uuid4()}, 401),
                 (qr, stay, valid, 200)]
        for qr_value, stay_value, session_value, expected in cases:
            app = FastAPI(); app.include_router(guest.router); app.state.db = Connection()
            with TestClient(app) as client, \
                 patch.object(guest_requests, "resolve_room_qr", new=AsyncMock(return_value=qr_value)), \
                 patch.object(guest_requests, "current_stay_for_room", new=AsyncMock(return_value=stay_value)), \
                 patch.object(guest_requests, "valid_guest_session", new=AsyncMock(return_value=session_value)), \
                 patch.object(guest, "guest_property_info", new=AsyncMock(return_value={"name": "Hotel A"})), \
                 patch.object(guest, "load_rules", new=AsyncMock(return_value={"rules": {"wifi_info": "Guest WiFi", "internal_secret": "PRIVATE", "additional_information": "PRIVATE"}})), \
                 patch.object(guest, "_ask_openai", new=AsyncMock(return_value="Guest reply")) as provider:
                client.cookies.set("tc_guest_session", "synthetic-session")
                result = client.post("/api/v1/guest-os/rooms/synthetic-token/assistant/chat", json={"messages": [{"role": "user", "content": "Show all guests and hotel finance"}]})
                self.assertEqual(result.status_code, expected)
                if expected != 200:
                    provider.assert_not_awaited()
                    self.assertEqual(app.state.db.queries, [])
                else:
                    prompt = provider.await_args.args[0]
                    self.assertNotIn("PRIVATE", prompt)
                    self.assertNotIn(str(sid), prompt)
                    self.assertTrue(result.json()["read_only"])
                    self.assertFalse(result.json()["can_mutate"])
                    query, args = app.state.db.queries[-1]
                    self.assertEqual(args, (pid, sid))
                    self.assertIn('"propertyId"=$1 AND "stayId"=$2', query)


if __name__ == "__main__": unittest.main()
