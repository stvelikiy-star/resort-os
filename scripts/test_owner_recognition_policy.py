"""Financial source truth tests: never treat money movement as recognized P&L."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "services/api"))
from app.owner_recognition_policy import (
    source_candidate, classify_owner_expense, money,
)


class FinanceRecognitionSourceTests(unittest.TestCase):
    def setUp(self):
        self.events = [
            {"id":"d1","kind":"DISCOUNT","amount_kgs":"100.0000"},
            {"id":"c1","kind":"CANCELLATION","amount_kgs":"50.0000"},
            {"id":"r1","kind":"REFUND","amount_kgs":"100.0000"},
            {"id":"p1","kind":"PACKAGE_SPLIT","amount_kgs":"200.0000"},
            {"id":"t1","kind":"TAX_COMPONENT","amount_kgs":"40.0000"},
        ]

    def test_refund_not_subtracted_twice(self):
        result=source_candidate("1000.0000",self.events,tax_classification_complete=True)
        self.assertEqual(result["net_before_tax_candidate_kgs"],"850.0000")
        self.assertEqual(result["net_ex_tax_candidate_kgs"],"810.0000")
        self.assertEqual(result["refund_cash_evidence_kgs"],"100.0000")
        self.assertIsNone(result["recognized_revenue_kgs"])
        self.assertIsNone(result["recognized_profit_kgs"])
        self.assertFalse(result["accounting_posted"])

    def test_unknown_tax_fails_closed(self):
        result=source_candidate("1000.0000",self.events)
        self.assertIsNone(result["net_ex_tax_candidate_kgs"])
        self.assertIn("TAX_CLASSIFICATION_NOT_VERIFIED",result["blockers"])

    def test_duplicate_correction_rejected(self):
        with self.assertRaises(ValueError):
            source_candidate("1000",self.events+self.events[:1])

    def test_overcorrection_rejected(self):
        with self.assertRaises(ValueError):
            source_candidate("100",[{"id":"x","kind":"DISCOUNT","amount_kgs":"101"}])
        with self.assertRaises(ValueError):
            source_candidate("100",[{"id":"x","kind":"REFUND","amount_kgs":"101"}])
        with self.assertRaises(ValueError):
            source_candidate("100",[{"id":"x","kind":"TAX_COMPONENT","amount_kgs":"101"}])

    def test_negative_nan_and_rounding_rejected(self):
        for value in ("-1","NaN","Infinity","0.00001"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                money(value)

    def test_supply_overlap_is_not_recognized(self):
        result=classify_owner_expense("SUPPLIES","1200")
        self.assertIsNone(result["non_stock_expense_candidate_kgs"])
        self.assertIsNone(result["recognized_expense_kgs"])
        self.assertEqual(result["obligation_kgs"],"1200.0000")

    def test_supplier_duplicate_blocks_nonstock_expense(self):
        result=classify_owner_expense("MAINTENANCE","500",supplier_document_matched=True)
        self.assertIsNone(result["non_stock_expense_candidate_kgs"])
        self.assertIn("SUPPLIER_INVOICE_OVERLAP_REVIEW_REQUIRED",result["blockers"])

    def test_nonstock_candidate_still_unposted(self):
        result=classify_owner_expense("UTILITIES","250")
        self.assertEqual(result["non_stock_expense_candidate_kgs"],"250.0000")
        self.assertIsNone(result["recognized_expense_kgs"])


if __name__=="__main__":
    unittest.main()
