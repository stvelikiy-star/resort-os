#!/usr/bin/env python3
"""Authenticated and idempotent MARINA FLEX hotel onboarding, disposable DB only.

The source PMS cannot be modified. Hotels remain PENDING without entitlements.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import unittest
import uuid
from pathlib import Path

import asyncpg
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_onboarding import app as write_app  # noqa: E402
from app.flex_control_plane import app as read_app  # noqa: E402


class CommercialHotelRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.getenv("FLEX_DATABASE_URL"):
            raise RuntimeError("FLEX hotel onboarding tests require isolated CI database")
        cls.private = Ed25519PrivateKey.generate()
        public = cls.private.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode()
        cls.previous = {k: os.environ.get(k) for k in (
            "FLEX_AUTH_PUBLIC_KEYS_JSON", "FLEX_AUTH_ISSUER", "FLEX_AUTH_AUDIENCE"
        )}
        os.environ.update({
            "FLEX_AUTH_PUBLIC_KEYS_JSON": json.dumps({"ci-hotels": public}),
            "FLEX_AUTH_ISSUER": "marina-flex-hotel-ci",
            "FLEX_AUTH_AUDIENCE": "marina-flex-commercial",
        })
        # CI-only pre-enrolment of one trusted PMS deployment, no live API.
        cls.deployment_private = Ed25519PrivateKey.generate()
        deployment_public = cls.deployment_private.public_key().public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode()
        cls.deployment_id = "marina-ci-deployment-01"
        async def enroll_ci_deployment():
            dsn = os.getenv("FLEX_TEST_DB_OWNER_URL")
            if not dsn:
                raise RuntimeError("Ephemeral CI DB owner URL is required for fixture")
            conn = await asyncpg.connect(dsn)
            try:
                await conn.execute(
                    "INSERT INTO flex_trusted_deployments("
                    "deployment_id,public_key_pem,key_fingerprint_sha256,enrolled_by"
                    ") VALUES($1,$2,$3,'CI_FIXTURE')",
                    cls.deployment_id, deployment_public,
                    hashlib.sha256(deployment_public.encode()).hexdigest(),
                )
            finally:
                await conn.close()
        asyncio.run(enroll_ci_deployment())
        cls.writer_ctx = TestClient(write_app)
        cls.writer = cls.writer_ctx.__enter__()
        cls.reader_ctx = TestClient(read_app)
        cls.reader = cls.reader_ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.reader_ctx.__exit__(None, None, None)
        cls.writer_ctx.__exit__(None, None, None)
        for k, previous in cls.previous.items():
            if previous is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = previous

    @classmethod
    def auth(cls, subject: str, mfa: bool = False):
        now = int(time.time())
        data = {
            "sub": subject, "iss": "marina-flex-hotel-ci",
            "aud": "marina-flex-commercial", "iat": now, "nbf": now-1,
            "exp": now+300, "jti": str(uuid.uuid4()), "amr": ["mfa"] if mfa else ["pwd"],
        }
        token = jwt.encode(data, cls.private, algorithm="EdDSA", headers={"kid":"ci-hotels"})
        return "Bearer " + token

    def post(self, *, subject="administrator", mfa=True,
             key="flex-create-unique-0001", name="New Independent Hotel", extra=None):
        data = {"display_name": name, "currency": "KGS"}
        if extra: data.update(extra)
        return self.writer.post(
            "/v1/onboarding/hotels", json=data,
            headers={
                "Authorization": self.auth(subject, mfa=mfa),
                "Idempotency-Key": key,
            },
        )

    def test_01_only_signed_mfa_platform_admin_creates_pending(self):
        self.assertEqual(
            self.post(subject="owner-a", key="flex-unauthorized-owner-0001").status_code, 403
        )
        self.assertEqual(
            self.post(subject="sales-1", key="flex-unauthorized-sales-0001").status_code, 403
        )
        self.assertEqual(
            self.post(subject="investor-1", key="flex-unauthorized-investor-0001").status_code, 403
        )
        self.assertEqual(
            self.post(mfa=False, key="flex-unauthorized-no-mfa-0001").status_code, 403
        )
        self.assertEqual(self.writer.post(
            "/v1/onboarding/hotels",
            headers={"Idempotency-Key": "flex-anonymous-0001"},
            json={"display_name": "Untrusted Hotel"},
        ).status_code, 401)

        response = self.post()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["status"], "PENDING")
        self.assertFalse(body["billable"])
        self.assertFalse(body["idempotent_replay"])
        self.assertIsInstance(uuid.UUID(body["hotel_id"]), uuid.UUID)
        self.__class__.created_hotel = body["hotel_id"]

    def test_02_retries_do_not_create_more_hotels(self):
        replay = self.post()
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertTrue(replay.json()["idempotent_replay"])
        self.assertEqual(replay.json()["hotel_id"], self.created_hotel)
        different = self.post(name="Malicious changed name")
        self.assertEqual(different.status_code, 409, different.text)

    def test_03_strict_payload_and_key_validation(self):
        self.assertEqual(
            self.post(key="tiny").status_code, 422
        )
        self.assertEqual(
            self.post(key="invalid/idempotency/key").status_code, 422
        )
        self.assertEqual(
            self.post(key="flex-unknown-field-0001", extra={"status":"ACTIVE"}).status_code, 422
        )
        self.assertEqual(
            self.post(key="flex-wrong-currency-0001", extra={"currency":"USD"}).status_code, 422
        )

    def test_04_new_hotel_is_visible_to_admin_not_existing_owners(self):
        admin = self.reader.get(
            "/v1/hotels", headers={"Authorization": self.auth("administrator", mfa=True)}
        )
        self.assertEqual(admin.status_code, 200, admin.text)
        new = [h for h in admin.json() if h["id"] == self.created_hotel]
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["status"], "PENDING")
        self.assertEqual(
            self.reader.get(
                f"/v1/hotels/{self.created_hotel}/invoices",
                headers={"Authorization": self.auth("owner-a")},
            ).status_code, 404
        )
        self.assertEqual(
            self.reader.get(
                f"/v1/hotels/{self.created_hotel}/subscription",
                headers={"Authorization": self.auth("administrator", mfa=True)},
            ).status_code, 404
        )

    def test_05a_edit_hotel_name_without_changing_status(self):
        url = f"/v1/onboarding/hotels/{self.created_hotel}/name"
        payload = {"display_name": "Renamed Independent Hotel", "expected_name": "New Independent Hotel"}
        admin = {"Authorization": self.auth("administrator", mfa=True)}
        self.assertEqual(self.writer.post(url, json=payload, headers={"Authorization": self.auth("owner-a")}).status_code, 403)
        self.assertEqual(self.writer.post(url, json={**payload, "status": "ACTIVE"}, headers=admin).status_code, 422)
        result = self.writer.post(url, json=payload, headers=admin)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["status"], "PENDING")
        self.assertEqual(self.writer.post(url, json=payload, headers=admin).status_code, 409)
        rows = self.reader.get("/v1/hotels", headers=admin).json()
        self.assertEqual(next(h for h in rows if h["id"] == self.created_hotel)["name"], payload["display_name"])

    def test_06_signed_deployment_proof_and_single_use(self):
        headers = {"Authorization": self.auth("administrator", mfa=True)}
        url = f"/v1/onboarding/hotels/{self.created_hotel}/challenge"
        payload = {
            "deployment_id": self.deployment_id,
            "property_external_id": "ci-hotel-property-a",
        }
        self.assertEqual(self.writer.post(
            url, headers=headers,
            json={**payload, "deployment_id": "nonexistent-issuer"},
        ).status_code, 404)
        self.assertEqual(self.writer.post(
            url, headers={"Authorization": self.auth("owner-a")}, json=payload
        ).status_code, 403)
        response = self.writer.post(url, headers=headers, json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        challenge = response.json()
        self.assertIn("MARINA-FLEX-PMS-LINK-V1", challenge["signed_message"])
        confirm = "/v1/onboarding/challenges/" + challenge["challenge_id"] + "/confirm"
        forged = base64.urlsafe_b64encode(
            Ed25519PrivateKey.generate().sign(challenge["signed_message"].encode())
        ).decode()
        self.assertEqual(self.writer.post(
            confirm, headers=headers, json={"signature_b64": forged}
        ).status_code, 403)
        signature = base64.urlsafe_b64encode(
            self.deployment_private.sign(challenge["signed_message"].encode())
        ).decode()
        good = self.writer.post(
            confirm, headers=headers, json={"signature_b64": signature},
        )
        self.assertEqual(good.status_code, 200, good.text)
        self.assertEqual(good.json()["link_status"], "VERIFIED")
        self.assertFalse(good.json()["subscription_activated"])
        self.assertEqual(self.writer.post(
            confirm, headers=headers, json={"signature_b64": signature}
        ).status_code, 409)

        async def verify_database():
            conn = await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                links = await conn.fetchval(
                    "SELECT count(*) FROM flex_hotel_links "
                    "WHERE deployment_id=$1 AND property_external_id=$2",
                    self.deployment_id, payload["property_external_id"],
                )
                subscriptions = await conn.fetchval(
                    "SELECT count(*) FROM flex_subscriptions WHERE hotel_id=$1",
                    uuid.UUID(self.created_hotel),
                )
                audits = await conn.fetchval(
                    "SELECT count(*) FROM flex_audit_events "
                    "WHERE action='HOTEL_PMS_LINK_VERIFIED' AND resource_id=$1",
                    self.created_hotel,
                )
                self.assertEqual(links, 1)
                self.assertEqual(subscriptions, 0)
                self.assertEqual(audits, 1)
            finally:
                await conn.close()
        asyncio.run(verify_database())

    def test_07_other_hotel_cannot_claim_same_pms_property(self):
        created = self.post(key="flex-create-different-hotel-0002", name="Another Hotel")
        self.assertEqual(created.status_code, 201, created.text)
        admin_headers = {"Authorization": self.auth("administrator", mfa=True)}
        challenge_response = self.writer.post(
            f"/v1/onboarding/hotels/{created.json()['hotel_id']}/challenge",
            headers=admin_headers,
            json={
                "deployment_id": self.deployment_id,
                "property_external_id": "ci-hotel-property-a",
            },
        )
        self.assertEqual(challenge_response.status_code, 201, challenge_response.text)
        challenge = challenge_response.json()
        signature = base64.urlsafe_b64encode(
            self.deployment_private.sign(challenge["signed_message"].encode())
        ).decode()
        refused = self.writer.post(
            "/v1/onboarding/challenges/" + challenge["challenge_id"] + "/confirm",
            headers=admin_headers, json={"signature_b64": signature},
        )
        self.assertEqual(refused.status_code, 409, refused.text)

    def test_05_onboarding_cannot_mutate_or_activate_hotel(self):
        for method,path in (
            ("patch", f"/v1/onboarding/hotels/{self.created_hotel}"),
            ("delete", f"/v1/onboarding/hotels/{self.created_hotel}"),
            ("post", f"/v1/onboarding/hotels/{self.created_hotel}/activate"),
        ):
            response = getattr(self.writer, method)(
                path, headers={"Authorization": self.auth("administrator", mfa=True)}
            )
            self.assertIn(response.status_code, (404,405), response.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
