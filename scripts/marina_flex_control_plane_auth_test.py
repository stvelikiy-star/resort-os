#!/usr/bin/env python3
"""FLEX read-only identity tests: no network, real JWT signatures, no PMS DB."""
from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_control_plane import _flex_dsn, _reader_for, verify_platform_token  # noqa: E402
from app.flex_foundation import PlatformPrincipal  # noqa: E402


class SignedPlatformIdentity(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        public_pem = self.private_key.public_key().public_bytes(
            encoding=Encoding.PEM, format=PublicFormat.SubjectPublicKeyInfo
        ).decode()
        self.env = patch.dict(os.environ, {
            "FLEX_AUTH_PUBLIC_KEYS_JSON": json.dumps({"ci-2026": public_pem}),
            "FLEX_AUTH_ISSUER": "marina-flex-ci-issuer",
            "FLEX_AUTH_AUDIENCE": "marina-flex-ci",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def claims(self):
        now = int(time.time())
        return {
            "sub": "verified-owner-01", "iss": "marina-flex-ci-issuer",
            "aud": "marina-flex-ci", "iat": now, "nbf": now - 1,
            "exp": now + 600, "jti": "ci-token-001", "amr": ["pwd", "mfa"],
            # Deliberately injected roles/scopes do NOT become database grants.
            "role": "SUPER_ADMIN", "hotel_ids": ["a-hotel-i-do-not-own"],
        }

    def sign(self, claims=None, *, key=None, algorithm="EdDSA", kid="ci-2026"):
        return jwt.encode(
            claims or self.claims(), key or self.private_key,
            algorithm=algorithm, headers={"kid": kid},
        )

    def assert_denied(self, token):
        with self.assertRaises(HTTPException) as err:
            verify_platform_token("Bearer " + token)
        self.assertEqual(err.exception.status_code, 401)

    def test_valid_signature_only_exposes_subject_and_mfa(self):
        self.assertEqual(
            verify_platform_token("Bearer " + self.sign()),
            ("verified-owner-01", True),
        )

    def test_no_mfa_not_promoted(self):
        claims = self.claims()
        claims["amr"] = ["pwd"]
        self.assertEqual(verify_platform_token("Bearer " + self.sign(claims))[1], False)

    def test_expired_wrong_issuer_audience_and_overlong_tokens(self):
        modifications = (
            {"exp": int(time.time()) - 40, "iat": int(time.time()) - 500},
            {"aud": "attacker-api"},
            {"iss": "not-the-issuer"},
            {"exp": int(time.time()) + 3600},
            {"sub": "x"},
            {"sub": "user with spaces"},
            {"jti": ""},
        )
        for mod in modifications:
            with self.subTest(mod=mod):
                claims = self.claims()
                claims.update(mod)
                self.assert_denied(self.sign(claims))

    def test_wrong_key_id_and_forged_role(self):
        self.assert_denied(self.sign(kid="attacker-key"))
        forged = self.claims()
        self.assert_denied(self.sign(forged, key=Ed25519PrivateKey.generate()))

    def test_algorithm_confusion_is_denied(self):
        forged = jwt.encode(
            self.claims(), "attacker-secret", algorithm="HS256",
            headers={"kid": "ci-2026"},
        )
        self.assert_denied(forged)

    def test_invalid_bearer_and_unconfigured_issuer(self):
        for token in (None, "", "Basic something", "Bearer ", "Bearer a b"):
            with self.subTest(token=token):
                with self.assertRaises(HTTPException):
                    verify_platform_token(token)
        with patch.dict(os.environ, {"FLEX_AUTH_PUBLIC_KEYS_JSON": ""}):
            with self.assertRaises(HTTPException) as err:
                verify_platform_token("Bearer " + self.sign())
            self.assertEqual(err.exception.status_code, 503)


class SeparateDatabaseAndScopes(unittest.TestCase):
    def test_refuse_missing_and_same_hotel_database(self):
        with patch.dict(os.environ, {"FLEX_DATABASE_URL": "", "DATABASE_URL": ""}):
            with self.assertRaises(RuntimeError):
                _flex_dsn()
        with patch.dict(os.environ, {
            "FLEX_DATABASE_URL": "postgresql://flex:secret@db.test:5432/resort?sslmode=require",
            "DATABASE_URL": "postgresql://hotel:secret@db.test:5432/resort?schema=public",
        }):
            with self.assertRaises(RuntimeError):
                _flex_dsn()

    def test_distinct_flex_database_accepted(self):
        with patch.dict(os.environ, {
            "FLEX_DATABASE_URL": "postgresql://flex:secret@db.test:5432/flex?schema=public",
            "DATABASE_URL": "postgresql://hotel:secret@db.test:5432/resort",
        }):
            self.assertEqual(_flex_dsn(), "postgresql://flex:secret@db.test:5432/flex")

    def test_qa_preview_password_reader_never_works_outside_isolated_preview(self):
        from app.flex_control_plane import qa_password_read_allowed
        principal = PlatformPrincipal("test-admin", "SUPER_ADMIN", mfa_verified=False)
        with patch.dict(os.environ, {
            "FLEX_ENVIRONMENT": "qa", "VERCEL_ENV": "preview",
            "FLEX_QA_PASSWORD_LOGIN": "true",
        }):
            self.assertTrue(qa_password_read_allowed(principal))
            self.assertEqual(_reader_for(principal), "flex_platform_admin_reader")
        for overrides in (
            {"FLEX_ENVIRONMENT": "production", "VERCEL_ENV": "preview", "FLEX_QA_PASSWORD_LOGIN": "true"},
            {"FLEX_ENVIRONMENT": "qa", "VERCEL_ENV": "production", "FLEX_QA_PASSWORD_LOGIN": "true"},
            {"FLEX_ENVIRONMENT": "qa", "VERCEL_ENV": "preview", "FLEX_QA_PASSWORD_LOGIN": "false"},
        ):
            with patch.dict(os.environ, overrides):
                self.assertFalse(qa_password_read_allowed(principal))
                with self.assertRaises(HTTPException):
                    _reader_for(principal)

    def test_admin_reader_needs_mfa(self):
        with self.assertRaises(HTTPException):
            _reader_for(PlatformPrincipal("root", "SUPER_ADMIN", mfa_verified=False))
        self.assertEqual(
            _reader_for(PlatformPrincipal("root", "SUPER_ADMIN", mfa_verified=True)),
            "flex_platform_admin_reader",
        )
        self.assertEqual(
            _reader_for(PlatformPrincipal("hotel", "HOTEL_OWNER", hotel_ids=frozenset({"a"}))),
            "flex_hotel_reader",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
