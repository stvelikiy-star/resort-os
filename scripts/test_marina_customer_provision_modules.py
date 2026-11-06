"""Bootstrap optional module defaults for a new independent MARINA hotel."""
import importlib
import os
import unittest
from unittest.mock import patch

bootstrap = importlib.import_module("provision_empty_marina_property")


class CustomerProvisionModulesTests(unittest.TestCase):
    def test_customer_site_editor_on_only_for_new_customer(self):
        with patch.dict(os.environ, {"MARINA_CUSTOMER_SITE_SAFE_MODE": "true"}):
            self.assertEqual(bootstrap.bootstrap_enabled_modules(), '["CONTENT"]')

    def test_legacy_bootstrap_default_unchanged(self):
        with patch.dict(os.environ, {"MARINA_CUSTOMER_SITE_SAFE_MODE": "false"}):
            self.assertEqual(bootstrap.bootstrap_enabled_modules(), "[]")

    def test_no_guard_defaults_to_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(bootstrap.bootstrap_enabled_modules(), "[]")

    def test_guard_must_be_exact_boolean_true(self):
        with patch.dict(os.environ, {"MARINA_CUSTOMER_SITE_SAFE_MODE": "preview"}):
            self.assertEqual(bootstrap.bootstrap_enabled_modules(), "[]")


if __name__ == "__main__":
    unittest.main()
