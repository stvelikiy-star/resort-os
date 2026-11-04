"""RC4 Guest QR admission is narrow, staging-only and disabled by default.

This unit gate uses no database and does not replace the separate real HTTPS,
two-hotel PostgreSQL + Chromium acceptance.
"""
import os
from unittest import TestCase, main
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import auth, guest_os
from app.guest_requests import router as guest_requests_router
from app.shared_guest_qr_rc4 import (
    SharedGuestQrRc4Boundary, guest_qr_rc4_allowed, guest_qr_rc4_guard,
)


TOKEN = "A" * 43
UUID = "11111111-1111-4111-8111-111111111111"


def fixture_app():
    app = FastAPI()
    app.add_middleware(SharedGuestQrRc4Boundary)

    @app.get(f"/api/v1/guest-os/rooms/{TOKEN}")
    def room():
        return {"guest_os": "canonical"}

    @app.post(f"/api/v1/guest-os/rooms/{TOKEN}/verify")
    def verify():
        return {"pin": "accepted"}

    @app.get("/api/v1/assistant/capabilities")
    def assistant():
        return {"not_reviewed": True}

    @app.get("/api/v1/auth/mode")
    def mode():
        return {"mode": "shared"}

    app.include_router(guest_requests_router)
    return app


class GuestQrRc4AdmissionTests(TestCase):
    def staging(self, **overrides):
        env = {
            "APP_ENV": "staging",
            "MARINA_SHARED_GUEST_QR_RC4_ENABLED": "true",
            "MARINA_SHARED_GUEST_QR_RC4_CONFIRM": "REVIEWED_SHARED_GUEST_QR_STAGING_ONLY",
            "GUEST_OS_PUBLIC_BASE_URL": "https://guest-rc4-ci.invalid",
            "MARINA_SHARED_GUEST_QR_RC4_ORIGIN": "https://guest-rc4-ci.invalid",
        }
        env.update(overrides)
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.dict(os.environ, env))
        stack.enter_context(patch.object(auth, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True))
        stack.enter_context(patch.object(auth, "MARINA_TENANT_CONTEXT_ENABLED", True))
        stack.enter_context(patch.object(auth, "COOKIE_SECURE", True))
        stack.enter_context(patch.object(auth, "PROPERTY_CODE", "MARINA_BROWSER_CI"))
        stack.enter_context(patch.object(guest_os, "MARINA_SHARED_AUTH_PREVIEW_ENABLED", True))
        stack.enter_context(patch.object(guest_os, "COOKIE_SECURE", True))
        return stack

    def test_only_exact_guest_methods_and_paths_are_admitted(self):
        allowed = (
            ("GET", "/api/v1/admin/guest-os/room-qrs"),
            ("POST", f"/api/v1/admin/guest-os/room-qrs/{UUID}/issue"),
            ("POST", f"/api/v1/admin/guest-os/room-qrs/{UUID}/rotate"),
            ("GET", f"/api/v1/guest-os/rooms/{TOKEN}"),
            ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/verify"),
            ("GET", f"/api/v1/guest-os/rooms/{TOKEN}/requests"),
            ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/requests"),
            ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/requests/{UUID}/cancel"),
            ("POST", "/api/v1/guest-os/logout"),
        )
        for method, path in allowed:
            with self.subTest(method=method, path=path):
                self.assertIs(guest_qr_rc4_allowed(method, path), True)
        closed = (
            ("POST", "/api/v1/admin/guest-os/room-qrs/issue-missing"),
            ("POST", "/api/v1/guest-os/rooms/ABC/verify"),
            ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/assistant/chat"),
            ("GET", f"/api/v1/guest-os/rooms/{TOKEN}/service-policy"),
            ("POST", f"/api/v1/guest-os/rooms/{TOKEN}/reviews"),
            ("GET", "/api/v1/admin/inbox/conversations"),
            ("GET", "/api/v1/assistant/capabilities"),
            ("POST", f"/api/v1/admin/guest-os/room-qrs/{UUID}/delete"),
            ("DELETE", f"/api/v1/admin/guest-os/room-qrs/{UUID}/rotate"),
            ("GET", "/api/v1/admin/finance/transactions"),
        )
        for method, path in closed:
            with self.subTest(method=method, path=path):
                self.assertIs(guest_qr_rc4_allowed(method, path), False)

    def test_default_rc3_remains_closed_without_guest_approval(self):
        with self.staging(MARINA_SHARED_GUEST_QR_RC4_ENABLED="false"):
            with TestClient(fixture_app(), base_url="https://guest-rc4-ci.invalid") as client:
                self.assertEqual(
                    client.get(f"/api/v1/guest-os/rooms/{TOKEN}").status_code, 503
                )
                self.assertEqual(client.get("/api/v1/auth/mode").status_code, 200)

    def test_approved_preview_dispatches_only_reviewed_guest_routes(self):
        with self.staging():
            self.assertIsNone(guest_qr_rc4_guard())
            with TestClient(fixture_app(), base_url="https://guest-rc4-ci.invalid") as client:
                self.assertEqual(
                    client.get(f"/api/v1/guest-os/rooms/{TOKEN}").json()["guest_os"],
                    "canonical",
                )
                self.assertEqual(
                    client.post(f"/api/v1/guest-os/rooms/{TOKEN}/verify").status_code,
                    200,
                )
                # Nonfinancial service-only stage: paid room service and
                # providers are closed before even looking up a stay.
                denied = client.post(
                    f"/api/v1/guest-os/rooms/{TOKEN}/requests",
                    json={"request_code": "HOUSEKEEPING"},
                )
                self.assertEqual(denied.status_code, 503)
                self.assertEqual(
                    denied.json()["detail"]["code"], "SHARED_GUEST_SERVICE_NOT_REVIEWED"
                )
                for path in (
                    "/api/v1/assistant/capabilities",
                    f"/api/v1/guest-os/rooms/{TOKEN}/assistant/chat",
                ):
                    self.assertEqual(client.get(path).status_code, 503)

    def test_missing_or_mismatched_guard_values_are_503(self):
        variants = [
            {"APP_ENV": "production"},
            {"MARINA_SHARED_GUEST_QR_RC4_CONFIRM": "wrong"},
            {"MARINA_SHARED_GUEST_QR_RC4_ORIGIN": "https://other.invalid"},
            {"GUEST_OS_PUBLIC_BASE_URL": "http://guest-rc4-ci.invalid"},
            {"GUEST_OS_PUBLIC_BASE_URL": "https://3korony.com",
             "MARINA_SHARED_GUEST_QR_RC4_ORIGIN": "https://3korony.com"},
        ]
        for values in variants:
            with self.subTest(values=values), self.staging(**values):
                with TestClient(fixture_app(), base_url="https://guest-rc4-ci.invalid") as client:
                    response = client.get(f"/api/v1/guest-os/rooms/{TOKEN}")
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(
                        client.get("/api/v1/assistant/capabilities").status_code, 503
                    )

    def test_insecure_cookie_does_not_admit_any_guest_route(self):
        with self.staging(), patch.object(guest_os, "COOKIE_SECURE", False):
            with TestClient(fixture_app(), base_url="https://guest-rc4-ci.invalid") as client:
                self.assertEqual(client.get(f"/api/v1/guest-os/rooms/{TOKEN}").status_code, 503)


if __name__ == "__main__":
    main()
