#!/usr/bin/env python3
"""Two-hotel authenticated HTTP smoke test against ephemeral FLEX CI database.

PostgreSQL fixture lives in scripts/marina_flex_rls_isolation_contract.sql.
Requires a disposable non-superuser FLEX_DATABASE_URL, no PMS URL.
"""
from __future__ import annotations

import json
import os
import time
import unittest
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_control_plane import app  # noqa: E402

HOTEL_A = "00000000-0000-0000-0000-00000000000a"
HOTEL_B = "00000000-0000-0000-0000-00000000000b"


class RealHTTPIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("FLEX_DATABASE_URL"):
            raise RuntimeError("HTTP CI requires disposable FLEX_DATABASE_URL")
        cls.private = Ed25519PrivateKey.generate()
        public = cls.private.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode()
        cls.old_config = {key: os.environ.get(key) for key in (
            "FLEX_AUTH_PUBLIC_KEYS_JSON", "FLEX_AUTH_ISSUER", "FLEX_AUTH_AUDIENCE",
        )}
        os.environ.update({
            "FLEX_AUTH_PUBLIC_KEYS_JSON": json.dumps({"ci-key": public}),
            "FLEX_AUTH_ISSUER": "marina-flex-ci-http",
            "FLEX_AUTH_AUDIENCE": "marina-flex-http",
        })
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        for key, value in cls.old_config.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def token(self, subject, *, mfa=False, extra=None):
        now = int(time.time())
        data = {
            "sub": subject, "iss": "marina-flex-ci-http", "aud": "marina-flex-http",
            "iat": now, "nbf": now - 1, "exp": now + 300,
            "jti": str(uuid.uuid4()), "amr": ["mfa"] if mfa else ["pwd"],
        }
        if extra:
            data.update(extra)
        return jwt.encode(data, self.private, algorithm="EdDSA", headers={"kid": "ci-key"})

    def get(self, path, sub, *, mfa=False):
        return self.client.get(
            path, headers={"Authorization": "Bearer " + self.token(sub, mfa=mfa)}
        )

    def test_anonymous_and_unknown_subject_rejected(self):
        self.assertEqual(self.client.get("/v1/me").status_code, 401)
        self.assertEqual(self.get("/v1/me", "unknown-user").status_code, 403)
        self.assertEqual(self.get("/v1/me", "disabled-owner").status_code, 403)

    def test_owner_cannot_see_other_hotel(self):
        for subject, allowed, denied, expected in (
            ("owner-a", HOTEL_A, HOTEL_B, "100.00"),
            ("owner-b", HOTEL_B, HOTEL_A, "200.00"),
        ):
            with self.subTest(subject=subject):
                p = self.get("/v1/me", subject)
                self.assertEqual(p.status_code, 200, p.text)
                self.assertEqual(p.json()["hotels"], [allowed])
                self.assertEqual(self.get(f"/v1/hotels/{denied}/invoices", subject).status_code, 404)
                self.assertEqual(self.get(f"/v1/hotels/{denied}/subscription", subject).status_code, 404)
                response = self.get(f"/v1/hotels/{allowed}/invoices", subject)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(response.json()), 1)
                self.assertEqual(response.json()[0]["total"], expected)
                subscription = self.get(f"/v1/hotels/{allowed}/subscription", subject)
                self.assertEqual(subscription.status_code, 200, subscription.text)
                self.assertEqual(subscription.json()["enforcement"], "OFF")
                self.assertEqual(self.get("/v1/hotels", subject).status_code, 403)

    def test_admin_requires_mfa_and_sees_registry(self):
        self.assertEqual(self.get("/v1/hotels", "administrator").status_code, 403)
        response = self.get("/v1/hotels", "administrator", mfa=True)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({i["id"] for i in response.json()}, {HOTEL_A, HOTEL_B})
        own = self.get(f"/v1/hotels/{HOTEL_B}/invoices", "administrator", mfa=True)
        self.assertEqual(own.status_code, 200, own.text)

    def test_available_catalog_only_no_future_or_planned_price(self):
        owner = self.get("/v1/catalog", "owner-a")
        self.assertEqual(owner.status_code, 200, owner.text)
        self.assertEqual(
            {p["sku"]: p["monthly_list_price"] for p in owner.json()},
            {"AI_ASSISTANT": "4000.00", "BASE_PMS": "10000.00"},
        )
        admin_without_mfa = self.get("/v1/catalog", "administrator")
        self.assertEqual(admin_without_mfa.status_code, 403)
        admin = self.get("/v1/catalog", "administrator", mfa=True)
        self.assertEqual(admin.status_code, 200, admin.text)
        self.assertEqual(len(admin.json()), 2)
        self.assertEqual(self.get("/v1/catalog", "unknown-user").status_code, 403)

    def test_agent_and_investor_are_not_hotel_owners(self):
        for subject, role, identity_key in (
            ("sales-1", "SALES_AGENT", "agent_id"),
            ("investor-1", "INVESTOR", "investor_id"),
        ):
            with self.subTest(subject=subject):
                profile = self.get("/v1/me", subject)
                self.assertEqual(profile.status_code, 200, profile.text)
                self.assertEqual(profile.json()["role"], role)
                self.assertTrue(profile.json()[identity_key])
                self.assertEqual(profile.json()["hotels"], [])
                self.assertEqual(self.get("/v1/hotels", subject).status_code, 403)
                self.assertEqual(self.get("/v1/catalog", subject).status_code, 403)
                self.assertEqual(
                    self.get(f"/v1/hotels/{HOTEL_A}/invoices", subject).status_code, 404
                )

    def test_token_supplied_role_or_hotel_scope_is_ignored(self):
        token = self.token("owner-a", mfa=True, extra={
            "role": "SUPER_ADMIN", "hotel_ids": [HOTEL_B],
        })
        header = {"Authorization": "Bearer " + token}
        self.assertEqual(self.client.get("/v1/hotels", headers=header).status_code, 403)
        self.assertEqual(
            self.client.get(f"/v1/hotels/{HOTEL_B}/invoices", headers=header).status_code,
            404,
        )

    def test_control_api_remains_read_only(self):
        for path in ("/v1/hotels", f"/v1/hotels/{HOTEL_A}/subscription"):
            r = self.client.post(path, headers={
                "Authorization": "Bearer " + self.token("administrator", mfa=True)
            }, json={"status": "ACTIVE"})
            self.assertEqual(r.status_code, 405, r.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
