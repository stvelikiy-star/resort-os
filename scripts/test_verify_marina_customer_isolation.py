#!/usr/bin/env python3
"""Dependency-free P0 configuration guard regression."""
import tempfile
import unittest
from pathlib import Path

from verify_marina_customer_isolation import parse_env, path_overlap, validate_one, validate_pair


def hotel(n):
    return {
        "PROPERTY_CODE": f"HOTEL_{n}", "COMPOSE_PROJECT_NAME": f"marina_hotel_{n}",
        "POSTGRES_DB": f"marina_hotel_{n}", "POSTGRES_USER": f"marina_{n}",
        "POSTGRES_PASSWORD": f"private-db-secret-{n}",
        "N8N_ENCRYPTION_KEY": f"private-encryption-secret-{n}",
        "AUTOMATION_SERVICE_KEY": f"private-service-secret-{n}",
        "GREEN_API_ID_INSTANCE": str(100000 + n),
        "GREEN_API_TOKEN_INSTANCE": f"private-provider-token-{n}",
        "GREEN_API_WEBHOOK_SECRET": f"private-webhook-secret-{n}",
        "HOST_DATA_DIR": f"/srv/marina/hotel-{n}/data",
        "BACKUP_DIR": f"/srv/marina/hotel-{n}/backups",
        "PUBLIC_HOST": f"hotel-{n}.example.org",
        "ADMIN_HOST": f"admin.hotel-{n}.example.org",
        "STAFF_HOST": f"staff.hotel-{n}.example.org",
        "API_HOST": f"api.hotel-{n}.example.org",
        "AUTOMATION_HOST": f"automation.hotel-{n}.example.org",
        "COOKIE_SECURE": "true",
        "MARINA_TENANT_CONTEXT_ENABLED": "false",
    }


class CustomerIsolationContract(unittest.TestCase):
    def test_independent_hotels_pass(self):
        a, b = hotel(1), hotel(2)
        self.assertEqual(validate_one(a, "a"), [])
        self.assertEqual(validate_one(b, "b"), [])
        self.assertEqual(validate_pair(a, b), [])

    def test_same_project_storage_and_identity_are_blocked(self):
        a, b = hotel(1), hotel(2)
        b.update(COMPOSE_PROJECT_NAME=a["COMPOSE_PROJECT_NAME"],
                 HOST_DATA_DIR=a["HOST_DATA_DIR"] + "/other",
                 PUBLIC_HOST=a["PUBLIC_HOST"],
                 AUTOMATION_SERVICE_KEY=a["AUTOMATION_SERVICE_KEY"])
        findings = " ".join(validate_pair(a, b))
        for marker in ("COMPOSE_PROJECT_NAME", "HOST_DATA_DIR", "AUTOMATION_SERVICE_KEY", "hostnames"):
            self.assertIn(marker, findings)

    def test_single_property_and_secure_cookie_required(self):
        a = hotel(1)
        a["MARINA_TENANT_CONTEXT_ENABLED"] = "true"
        a["COOKIE_SECURE"] = "false"
        result = " ".join(validate_one(a, "a"))
        self.assertIn("tenant preview off", result)
        self.assertIn("COOKIE_SECURE", result)

    def test_backup_must_not_be_nested_in_postgres_data(self):
        a = hotel(1)
        a["BACKUP_DIR"] = a["HOST_DATA_DIR"] + "/backups"
        self.assertIn("data and backups", " ".join(validate_one(a, "a")))
        self.assertTrue(path_overlap("/srv/hotel-a/data", "/srv/hotel-a/data/sub"))

    def test_duplicate_and_malformed_env_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hotel.env"
            path.write_text("PROPERTY_CODE=HOTEL_A\nPROPERTY_CODE=HOTEL_B\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_env(path)
            path.write_text("PROPERTY_CODE=HOTEL_A\nINVALID LINE\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_env(path)


if __name__ == "__main__":
    unittest.main()
