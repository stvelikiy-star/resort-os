"""Invariant acceptance for strict MARINA OWNER ledger policy."""
import sys
import unittest
import os
from unittest.mock import patch
from fastapi import HTTPException
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/api"))
from app.owner_ledger_policy import validate_posting,posted_totals
from app.owner_accounting_postings import posting_guard


class OwnerLedgerPolicyTests(unittest.TestCase):
    revenue=[{"account_code":"1100","side":"DEBIT","amount_kgs":"700.0000"},
             {"account_code":"4200","side":"CREDIT","amount_kgs":"650.0000"},
             {"account_code":"2100","side":"CREDIT","amount_kgs":"50.0000"}]
    def test_valid_net_of_tax(self):
        self.assertEqual(validate_posting(self.revenue,source_type="REVENUE_SOURCE",
                         evidence_complete=True,source_amount="700"),"700.0000")
    def test_missing_tax_confirmation_blocks(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_INCOMPLETE"):
            validate_posting(self.revenue,source_type="REVENUE_SOURCE",
                             evidence_complete=False,source_amount="700")
    def test_unknown_account_blocks(self):
        with self.assertRaisesRegex(ValueError,"ACCOUNT_OR_SIDE"):
            validate_posting([{**self.revenue[0],"account_code":"9999"},*self.revenue[1:]],
                             source_type="REVENUE_SOURCE",evidence_complete=True,source_amount="700")
    def test_unbalanced_and_mismatched_block(self):
        with self.assertRaisesRegex(ValueError,"UNBALANCED"):
            validate_posting(self.revenue[:-1],source_type="REVENUE_SOURCE",
                             evidence_complete=True,source_amount="700")
        with self.assertRaisesRegex(ValueError,"SOURCE_AMOUNT"):
            validate_posting(self.revenue,source_type="REVENUE_SOURCE",
                             evidence_complete=True,source_amount="800")
    def test_operating_expense(self):
        lines=[{"account_code":"5200","side":"DEBIT","amount_kgs":"1200"},
               {"account_code":"2200","side":"CREDIT","amount_kgs":"1200"}]
        self.assertEqual(validate_posting(lines,source_type="OPERATING_EXPENSE",
                         evidence_complete=True,source_amount="1200"),"1200.0000")
    def test_supplier_cash_not_period_expense(self):
        lines=[{"account_code":"2200","side":"DEBIT","amount_kgs":"1200"},
               {"account_code":"1000","side":"CREDIT","amount_kgs":"1200"}]
        with self.assertRaisesRegex(ValueError,"SOURCE_ACCOUNT"):
            validate_posting(lines,source_type="OPERATING_EXPENSE",
                             evidence_complete=True,source_amount="1200")
        value=posted_totals(lines,completeness_verified=True)
        self.assertEqual(value["recognized_profit_kgs"],"0.0000")
    def test_served_food_cost(self):
        lines=[{"account_code":"5100","side":"DEBIT","amount_kgs":"84.0000"},
               {"account_code":"1300","side":"CREDIT","amount_kgs":"84.0000"}]
        self.assertEqual(validate_posting(lines,source_type="STOCK_CONSUMPTION",
                         evidence_complete=True,source_amount="84"),"84.0000")
    def test_incomplete_period_remains_null(self):
        r=posted_totals(self.revenue,completeness_verified=False)
        self.assertEqual(r["status"],"NOT_READY")
        self.assertIsNone(r["recognized_profit_kgs"])
    def test_complete_period_profit_and_reversal(self):
        records=self.revenue+[{"account_code":"5100","side":"DEBIT","amount_kgs":"84"},
                             {"account_code":"1300","side":"CREDIT","amount_kgs":"84"}]
        actual=posted_totals(records,completeness_verified=True)
        self.assertEqual(actual["recognized_profit_kgs"],"566.0000")
        reversed_lines=[{**entry,"side":"CREDIT" if entry["side"]=="DEBIT" else "DEBIT"} for entry in records]
        final=posted_totals(records+reversed_lines,completeness_verified=True)
        self.assertEqual(final["recognized_profit_kgs"],"0.0000")
    def test_overprecision_and_nan_rejected(self):
        for v in ["NaN","-1","0.00001","Infinity"]:
            with self.subTest(v=v),self.assertRaises(ValueError):
                validate_posting([{**self.revenue[0],"amount_kgs":v},*self.revenue[1:]],
                    source_type="REVENUE_SOURCE",evidence_complete=True,source_amount="700")

    def test_posting_feature_off_by_default(self):
        with patch.dict(os.environ,{"APP_ENV":"staging",
              "MARINA_ACCOUNTING_POSTING_ENABLED":"false",
              "MARINA_SHARED_AUTH_PREVIEW_ENABLED":"false"}):
            with self.assertRaises(HTTPException) as ctx:
                posting_guard()
            self.assertEqual(ctx.exception.status_code,503)

    def test_posting_never_enabled_in_production_or_shared_preview(self):
        for env,shared in (("production","false"),("staging","true")):
            with patch.dict(os.environ,{"APP_ENV":env,
                  "MARINA_ACCOUNTING_POSTING_ENABLED":"true",
                  "MARINA_SHARED_AUTH_PREVIEW_ENABLED":shared}):
                with self.assertRaises(HTTPException) as ctx:
                    posting_guard()
                self.assertEqual(ctx.exception.status_code,503)

    def test_staging_requires_explicit_opt_in(self):
        with patch.dict(os.environ,{"APP_ENV":"staging",
              "MARINA_ACCOUNTING_POSTING_ENABLED":"true",
              "MARINA_SHARED_AUTH_PREVIEW_ENABLED":"false"}):
            self.assertIsNone(posting_guard())


if __name__=="__main__":
    unittest.main()
