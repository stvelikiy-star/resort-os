"""OWNER accrual-readiness pure Decimal tests, no remote DB or source inference."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/api"))
from app.owner_accrual_readiness import amount, expense_breakdown


class AccrualReadinessTest(unittest.TestCase):
    def test_posted_obligations_separate_stock_ambiguous_and_non_stock(self):
        rows=[
            {"category":"UTILITIES","cost":Decimal(1000),"movement_count":1},
            {"category":"PAYROLL","cost":Decimal(2500),"movement_count":2},
            {"category":"SUPPLIES","cost":Decimal(600),"movement_count":1},
            {"category":"OTHER","cost":Decimal(200),"movement_count":1},
        ]
        r=expense_breakdown(rows)
        self.assertEqual(r["posted_total_kgs"],"4300.0000")
        self.assertEqual(r["non_stock_obligations_candidate_kgs"],"3500.0000")
        self.assertEqual(r["stock_overlap_review_kgs"],"800.0000")
        self.assertEqual(r["status"],"CLASSIFICATION_REQUIRED")
        self.assertEqual(r["posted_count"],5)
        self.assertEqual(r["categories_kgs"]["SUPPLIES"],"600.0000")

    def test_no_candidate_is_automatically_recognized(self):
        r=expense_breakdown([{"category":"RENT","cost":Decimal(1500),
                             "movement_count":1}])
        self.assertEqual(r["status"],"POSTED_NOT_RECOGNIZED")
        self.assertEqual(r["non_stock_obligations_candidate_kgs"],"1500.0000")
        self.assertEqual(r["stock_overlap_review_kgs"],"0.0000")

    def test_missing_invalid_categories_and_negative_values_fail_closed(self):
        for row in ({"category":"UNKNOWN","cost":Decimal(100),"movement_count":1},
                    {"category":"UTILITIES","cost":Decimal(-100),"movement_count":1}):
            with self.subTest(row=row):
                with self.assertRaises(ValueError):
                    expense_breakdown([row])

    def test_decimal_rounding_not_float(self):
        self.assertEqual(amount(Decimal("123.45675")),"123.4568")
        self.assertEqual(amount(Decimal("2")*Decimal("111.7284")),"223.4568")


if __name__=="__main__":
    unittest.main()
