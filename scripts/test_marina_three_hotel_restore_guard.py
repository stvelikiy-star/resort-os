"""Protect the full three-hotel logical restore from any customer/remote target."""
import os
from unittest.mock import patch
import unittest

from marina_shared_three_hotel_restore_ci import (
    verify_restore_urls,CONFIRM,DEST_NAME,
)
SOURCE="postgresql://marina_ci:synthetic-ci-database-only@127.0.0.1:5432/marina_shared_browser_ci?schema=public"
DEST="postgresql://marina_ci:synthetic-ci-database-only@127.0.0.1:5432/"+DEST_NAME+"?schema=public"
ENV={
    "MARINA_SHARED_THREE_RESTORE_CONFIRM":CONFIRM,
    "MARINA_SHARED_BROWSER_CI_CONFIRM":"DISPOSABLE_TWO_HOTEL_BROWSER_CI",
    "MARINA_SHARED_THIRD_HOTEL_CONFIRM":"DISPOSABLE_THIRD_HOTEL_ADDITIVE_CI_ONLY",
    "APP_ENV":"staging",
    "MARINA_TENANT_CONTEXT_ENABLED":"true",
    "MARINA_SHARED_AUTH_PREVIEW_ENABLED":"true",
    "COOKIE_SECURE":"true",
}


class ThreeHotelRestoreGuard(unittest.TestCase):
    def test_only_confirmed_exact_local_disposable_source_target_allowed(self):
        with patch.dict(os.environ,ENV,clear=True):
            self.assertEqual(verify_restore_urls(SOURCE,DEST),(SOURCE.split("?")[0],DEST.split("?")[0]))

    def test_wrong_environment_fail_closed(self):
        for key in ENV:
            with self.subTest(key=key),patch.dict(os.environ,{**ENV,key:"production"},clear=True):
                with self.assertRaises(RuntimeError):
                    verify_restore_urls(SOURCE,DEST)

    def test_unsafe_source_or_destination_denied(self):
        for bad in (
            DEST.replace(DEST_NAME,"marina_production"),
            DEST.replace("127.0.0.1","db.example.com"),
            DEST.replace(":5432",":5433"),
            DEST.replace("marina_ci","postgres"),
            DEST.replace("?schema=public","?sslmode=disable"),
            DEST.replace("?schema=public","?schema=other"),
            DEST+"#fragment",
            SOURCE,
        ):
            with self.subTest(bad=bad),patch.dict(os.environ,ENV,clear=True):
                with self.assertRaises(RuntimeError):
                    verify_restore_urls(SOURCE,bad)
        with patch.dict(os.environ,ENV,clear=True):
            with self.assertRaises(RuntimeError):
                verify_restore_urls(DEST,DEST)


if __name__=="__main__":
    unittest.main()
