import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'services/api'))
from app import auth
from pydantic import ValidationError
from marina_demo_set_access import configuration


class DemoCredentialsTests(unittest.TestCase):
    def validate(self, prop, stage, username='demo', password='demo01', tenant=False):
        with patch.object(auth, 'PROPERTY_CODE', prop), patch.object(auth, 'MARINA_TENANT_CONTEXT_ENABLED', tenant), patch.dict(os.environ, APP_ENV=stage):
            return auth.LoginPayload(username=username, password=password)

    def test_requested_demo_login(self):
        self.assertEqual(self.validate('MARINA_DEMO', 'staging').username, 'demo')

    def test_exception_cannot_apply_to_other_accounts_or_hotels(self):
        for prop, stage, username, tenant in [
            ('MARINA_DEMO', 'production', 'demo', False),
            ('BANZAI', 'staging', 'demo', False),
            ('ASKA_TASH', 'production', 'demo', False),
            ('MARINA_DEMO', 'staging', 'employee', False),
            ('MARINA_DEMO', 'staging', 'demo', True),
        ]:
            with self.subTest(prop=prop, stage=stage, username=username, tenant=tenant):
                with self.assertRaises(ValidationError):
                    self.validate(prop, stage, username=username, tenant=tenant)

    def test_demo_still_rejects_five_characters(self):
        with self.assertRaises(ValidationError):
            self.validate('MARINA_DEMO', 'staging', password='short')

    def test_change_refuses_other_runtime_or_database(self):
        base = dict(APP_ENV='staging', PROPERTY_CODE='MARINA_DEMO', MARINA_TENANT_CONTEXT_ENABLED='false',
                    DATABASE_URL='postgresql://marina_demo:synthetic@postgres:5432/marina_demo?schema=public',
                    MARINA_DEMO_NEW_USERNAME='demo', MARINA_DEMO_NEW_PASSWORD='demo01')
        with patch.dict(os.environ, base):
            self.assertEqual(configuration()[1:], ('demo', 'demo01'))
        for change in [dict(APP_ENV='production'), dict(PROPERTY_CODE='MARINA_HOTEL01'),
                       dict(DATABASE_URL='postgresql://marina_demo:synthetic@postgres:5432/hotel01'),
                       dict(MARINA_TENANT_CONTEXT_ENABLED='true')]:
            with self.subTest(change=change), patch.dict(os.environ, {**base, **change}):
                with self.assertRaises(RuntimeError):
                    configuration()


if __name__ == '__main__':
    unittest.main()
