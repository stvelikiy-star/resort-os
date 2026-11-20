"""Exercise isolation-gate failure paths without a server or real hotel data."""
import unittest

import httpx

from verify_marina_multitenant_isolation import expect_denied, login, validate_base_url, verify_account

OWN = "00000000-0000-0000-0000-000000000001"
FOREIGN = "00000000-0000-0000-0000-000000000002"
REQUEST = "00000000-0000-0000-0000-000000000003"
FOREIGN_REQUEST = "00000000-0000-0000-0000-000000000004"


class URLTests(unittest.TestCase):
    def test_allowed_origins(self):
        for value in ("https://staging.example/", "http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"):
            with self.subTest(value=value):
                self.assertEqual(validate_base_url(value), value.rstrip("/"))

    def test_reject_unsafe_or_ambiguous_targets(self):
        for value in ("http://hotel.example", "ftp://localhost", "https:///", "https://user:secret@hotel.example", "https://hotel.example/api", "https://hotel.example?x=1", "https://hotel.example#fragment"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                validate_base_url(value)


class GateTests(unittest.IsolatedAsyncioTestCase):
    async def denial(self, response):
        async with httpx.AsyncClient(base_url="https://staging.example", transport=httpx.MockTransport(lambda _: response)) as client:
            await expect_denied(client, "/foreign", label="probe", expected_detail="Request not found")

    async def test_accept_application_boundary(self):
        await self.denial(httpx.Response(404, json={"detail": "Request not found"}))
        await self.denial(httpx.Response(403, json={"detail": "Insufficient permission"}))

    async def test_reject_false_denials(self):
        responses = (
            httpx.Response(404, json={"detail": "Not Found"}),
            httpx.Response(404, text="<html>proxy 404</html>"),
            httpx.Response(404, json={"detail": "Unknown room type"}),
            httpx.Response(403, json={"detail": "WAF blocked"}),
            httpx.Response(404, json=[]),
            httpx.Response(200, json={}),
            httpx.Response(422, json={"detail": "Unknown room type"}),
            httpx.Response(500, json={}),
            httpx.Response(302, headers={"location": "/login"}),
        )
        for response in responses:
            with self.subTest(status=response.status_code), self.assertRaises(RuntimeError):
                await self.denial(response)

    async def test_auth_context_must_be_valid_uuid(self):
        def handler(request):
            if request.url.path.endswith("/login"):
                return httpx.Response(200, json={})
            return httpx.Response(200, json={"role": "OWNER", "tenant_id": "not-a-uuid", "property_id": OWN, "property_code": "A"})
        async with httpx.AsyncClient(base_url="https://staging.example", transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "must be a UUID"):
                await login(client, "owner", "synthetic-password")

    async def account(self, *, missing_schedule=False, leak_reservation=False, leak_request=False, wrong_detail=False):
        visited = []
        def handler(request):
            path = request.url.path
            visited.append(path)
            if path == "/api/v1/pms/grid":
                return httpx.Response(200, json={"property": "A", "rooms": []})
            if path == "/api/v1/admin/reception/reservations":
                ids = [OWN, FOREIGN] if leak_reservation else [OWN]
                return httpx.Response(200, json={"items": [{"id": item} for item in ids]})
            if path == "/api/v1/admin/booking/requests":
                ids = [REQUEST, FOREIGN_REQUEST] if leak_request else [REQUEST]
                return httpx.Response(200, json={"items": [{"id": item} for item in ids]})
            if OWN in path:
                if missing_schedule and path.endswith("/schedule"):
                    return httpx.Response(404, json={"detail": "Not Found"})
                return httpx.Response(200, json={"reservation": {"id": FOREIGN if wrong_detail else OWN}})
            detail = "Request not found" if path.endswith("/quote") else "Reservation not found"
            return httpx.Response(404, json={"detail": detail})
        async with httpx.AsyncClient(base_url="https://staging.example", transport=httpx.MockTransport(handler)) as client:
            await verify_account(client, {"property_code": "A"}, "A", OWN, REQUEST, FOREIGN, FOREIGN_REQUEST, "2026-10-14", "2026-10-15")
        return visited

    async def test_complete_account_probe(self):
        visited = await self.account()
        self.assertIn(f"/api/v1/admin/pms/reservations/{OWN}/schedule", visited)
        self.assertIn(f"/api/v1/admin/booking/requests/{FOREIGN_REQUEST}/quote", visited)

    async def test_missing_route_cannot_pass(self):
        with self.assertRaises(RuntimeError):
            await self.account(missing_schedule=True)

    async def test_foreign_reservation_leak_fails(self):
        with self.assertRaisesRegex(RuntimeError, "foreign reservation"):
            await self.account(leak_reservation=True)

    async def test_foreign_request_leak_fails(self):
        with self.assertRaisesRegex(RuntimeError, "foreign request"):
            await self.account(leak_request=True)

    async def test_wrong_own_detail_fails(self):
        with self.assertRaisesRegex(RuntimeError, "detail mismatch"):
            await self.account(wrong_detail=True)


if __name__ == "__main__":
    unittest.main()
