"""Fail-closed safety checks for adding a hotel to populated shared staging."""
import os
from unittest.mock import patch
import unittest

from marina_shared_add_hotel import (
    staged_configuration, validate_hotel, NewHotel,
    CI_CONFIRMATION, EXISTING_CONFIRMATION,
)
from marina_shared_third_hotel_ci import compare_additive

GOOD_ENV={
    "APP_ENV":"staging",
    "PROPERTY_CODE":"MARINA_BROWSER_CI",
    "MARINA_TENANT_CONTEXT_ENABLED":"true",
    "MARINA_SHARED_AUTH_PREVIEW_ENABLED":"true",
    "COOKIE_SECURE":"true",
    "MARINA_SHARED_BROWSER_CI_CONFIRM":EXISTING_CONFIRMATION,
    "MARINA_SHARED_THIRD_HOTEL_CONFIRM":CI_CONFIRMATION,
    "DATABASE_URL":"postgresql://marina_ci:synthetic-ci-database-only@127.0.0.1:5432/marina_shared_browser_ci?schema=public",
    "MARINA_SHARED_BROWSER_CI_PASSWORD":"synthetic-ci-only-browser-two-hotels-2026",
}


class SharedAddHotelSafety(unittest.TestCase):
    def test_exact_ci_profile_required(self):
        with patch.dict(os.environ,GOOD_ENV,clear=True):
            dsn,hotel=staged_configuration()
        self.assertTrue(dsn.endswith("/marina_shared_browser_ci"))
        self.assertEqual(hotel.property_code,"HOTEL_C")
        self.assertEqual(hotel.tenant_code,"tenant_c")
        validate_hotel(hotel)

    def test_refuse_wrong_environment_even_if_url_is_local(self):
        for key in ("APP_ENV","PROPERTY_CODE","MARINA_TENANT_CONTEXT_ENABLED",
                    "MARINA_SHARED_AUTH_PREVIEW_ENABLED","COOKIE_SECURE",
                    "MARINA_SHARED_BROWSER_CI_CONFIRM","MARINA_SHARED_THIRD_HOTEL_CONFIRM"):
            with self.subTest(key=key),patch.dict(os.environ,{**GOOD_ENV,key:"production"},clear=True):
                with self.assertRaises(RuntimeError):
                    staged_configuration()

    def test_refuse_other_databases_and_remote_connections(self):
        url=GOOD_ENV["DATABASE_URL"]
        variants=[
            url.replace("127.0.0.1","customer-db.example.org"),
            url.replace("marina_shared_browser_ci","marina_shared"),
            url.replace("marina_shared_browser_ci","marina_shared_browser_restore_ci"),
            url.replace("marina_ci:","postgres:"),
            url.replace("synthetic-ci-database-only","different-password"),
            url.replace(":5432",":5433"),
            url.replace("?schema=public","?sslmode=disable"),
            url.replace("?schema=public","?schema=custom"),
            url+"#fragment",
        ]
        for candidate in variants:
            with self.subTest(candidate=candidate),patch.dict(
                os.environ,{**GOOD_ENV,"DATABASE_URL":candidate},clear=True
            ):
                with self.assertRaises(RuntimeError):
                    staged_configuration()

    def test_input_validation_rejects_credentials_and_path_ambiguity(self):
        with patch.dict(os.environ,GOOD_ENV,clear=True):
            _,original=staged_configuration()
        for changes in (
            {"tenant_code":"../tenant"},
            {"property_code":"../../HOTEL_C"},
            {"rate_plan_code":"bad code"},
            {"owner_password":"short"},
            {"owner_username":"x"},
            {"timezone":"Invalid/Synthetic"},
            {"currency":"KGS;"},
            {"name":""},
        ):
            with self.subTest(changes=changes):
                hotel=NewHotel(**{**original.__dict__,**changes})
                with self.assertRaises(ValueError):
                    validate_hotel(hotel)

    def test_additive_receipt_rejects_mutation_of_old_rows(self):
        old={"tables":{"audit_logs":{"count":1,"sha256":"old"},
                       "reservations":{"count":2,"sha256":"same"}},
             "constraints":[{"conname":"x","definition":"CHECK (TRUE)"}]}
        newer={"tables":{"audit_logs":{"count":2,"sha256":"new"},
                         "reservations":{"count":2,"sha256":"same"}},
               "constraints":old["constraints"]}
        before_rows={"audit_logs":{"old-id":"unaltered"}}
        after_rows={"audit_logs":{"old-id":"tampered","new-id":"new row"}}
        with self.assertRaises(AssertionError):
            compare_additive(old,newer,before_rows,after_rows,{"audit":"new-id"})


if __name__=="__main__":
    unittest.main()
