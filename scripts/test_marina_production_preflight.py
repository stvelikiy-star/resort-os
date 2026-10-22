from __future__ import annotations

import unittest

from marina_production_preflight import CONFIRMATION, validate


def valid_values() -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "MARINA_INSTANCE_SLUG": "ak-bermet-ci",
        "MARINA_HOST_ROOT": "/srv/marina-smart/ak-bermet-ci",
        "MARINA_HOST_DATA_DIR": "/srv/marina-smart/ak-bermet-ci/data",
        "MARINA_RELEASE_SHA": "a" * 40,
        "MARINA_PUBLIC_HOST": "marina-ci.invalid",
        "MARINA_ADMIN_HOST": "admin.marina-ci.invalid",
        "MARINA_STAFF_HOST": "staff.marina-ci.invalid",
        "MARINA_API_HOST": "api.marina-ci.invalid",
        "MARINA_AUTOMATION_HOST": "automation.marina-ci.invalid",
        "TLS_EMAIL": "ops@marina.test",
        "MARINA_POSTGRES_DB": "marina_ak_bermet_ci",
        "MARINA_POSTGRES_PASSWORD": "ci_Marina_Db_Password_1234567890_ABC",
        "PROPERTY_CODE": "MARINA_CI_HOTEL",
        "MARINA_PROPERTY_NAME": "MARINA Synthetic Deployment CI",
        "MARINA_TENANT_CODE": "tenant_ak_bermet_ci",
        "MARINA_TENANT_CONTEXT_ENABLED": "false",
        "MARINA_TIMEZONE": "Asia/Bishkek",
        "MARINA_CURRENCY": "KGS",
        "RATE_PLAN_CODE": "DIRECT",
        "AUTOMATION_SERVICE_KEY": "ci_automation_service_key_1234567890_ABC",
        "N8N_ENCRYPTION_KEY": "ci_n8n_encryption_key_1234567890_ABC",
        "N8N_IMAGE": "n8nio/n8n:2.37.10",
        "MARINA_PROVISION_CONFIRM": CONFIRMATION,
        "MARINA_OWNER_USERNAME": "marina-ci-owner",
        "MARINA_OWNER_PASSWORD": "Only-Synthetic-CI-Owner-Password-2026!",
    }


class MarinaProductionPreflightTest(unittest.TestCase):
    def test_accepts_isolated_ci_profile_and_bootstrap(self):
        self.assertEqual(validate(valid_values(), bootstrap=True, allow_test_hosts=True), [])

    def test_rejects_shared_three_crowns_paths_and_domain(self):
        values = valid_values()
        values["MARINA_HOST_ROOT"] = "/srv/three-crowns"
        values["MARINA_HOST_DATA_DIR"] = "/srv/three-crowns/data"
        values["MARINA_PUBLIC_HOST"] = "3korony.com"
        errors = validate(values, allow_test_hosts=True)
        self.assertTrue(any("MARINA_HOST_ROOT" in error for error in errors))
        self.assertTrue(any("MARINA_HOST_DATA_DIR" in error for error in errors))
        self.assertTrue(any("MARINA_ADMIN_HOST" in error for error in errors))

    def test_rejects_weak_database_secret_and_tenant_sharing(self):
        values = valid_values()
        values["MARINA_POSTGRES_PASSWORD"] = "short"
        values["MARINA_TENANT_CONTEXT_ENABLED"] = "true"
        errors = validate(values)
        self.assertTrue(any("MARINA_POSTGRES_PASSWORD" in error for error in errors))
        self.assertTrue(any("MARINA_TENANT_CONTEXT_ENABLED" in error for error in errors))

    def test_requires_immutable_tested_release_identity(self):
        values = valid_values()
        values["MARINA_RELEASE_SHA"] = "UNSET"
        self.assertTrue(any("MARINA_RELEASE_SHA" in error for error in validate(values)))

    def test_rejects_placeholder_hosts_and_duplicate_secrets(self):
        values = valid_values()
        values["MARINA_PUBLIC_HOST"] = "hotel.example.invalid"
        values["MARINA_ADMIN_HOST"] = "admin.hotel.example.invalid"
        values["MARINA_STAFF_HOST"] = "admin.hotel.example.invalid"
        values["MARINA_API_HOST"] = "api.hotel.example.invalid"
        values["MARINA_AUTOMATION_HOST"] = "automation.hotel.example.invalid"
        values["N8N_ENCRYPTION_KEY"] = values["AUTOMATION_SERVICE_KEY"]
        errors = validate(values)
        self.assertTrue(any("placeholder/test hostname" in error for error in errors))
        self.assertTrue(any("must be unique" in error for error in errors))
        self.assertTrue(any("must differ" in error for error in errors))

    def test_requires_one_shot_confirmation_and_strong_owner_password(self):
        values = valid_values()
        values["MARINA_PROVISION_CONFIRM"] = ""
        values["MARINA_OWNER_PASSWORD"] = "short"
        errors = validate(values, bootstrap=True, allow_test_hosts=True)
        self.assertTrue(any("MARINA_PROVISION_CONFIRM" in error for error in errors))
        self.assertTrue(any("MARINA_OWNER_PASSWORD" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
