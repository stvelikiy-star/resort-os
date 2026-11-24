"""Financial source truth tests: never treat money movement as recognized P&L."""
import sys
import asyncio
import uuid
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "services/api"))
from app.owner_recognition_policy import (
    source_candidate, classify_owner_expense, money, reconciliation_snapshot,
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

    def test_property_scoped_snapshot_and_cash_separation(self):
        approved=uuid.uuid4()
        class FakeConn:
            calls=[]
            async def fetch(self,sql,pid,start,end):
                self.calls.append((sql,pid))
                assert '"propertyId"=$1' in sql
                if "FROM owner_revenue_source_events e" in sql and "SELECT e.id" in sql:
                    return [{"id":approved,"face":"1000.0000"}]
                if "FROM owner_revenue_correction_events c" in sql:
                    return [
                        {"id":uuid.uuid4(),"approvalId":approved,"kind":"DISCOUNT","amount":"100.0000"},
                        {"id":uuid.uuid4(),"approvalId":approved,"kind":"REFUND","amount":"100.0000"},
                    ]
                if "FROM owner_expenses e" in sql:
                    return [{"id":uuid.uuid4(),"category":"SUPPLIES",
                             "amountKgs":"1200.0000","supplier_document_matched":False}]
                raise AssertionError("Unexpected finance SQL")
        prop=uuid.uuid4()
        conn=FakeConn()
        result=asyncio.run(reconciliation_snapshot(conn,prop,"2026-11-01","2026-11-30"))
        self.assertEqual(result["gross_approved_source_face_candidate_kgs"],"1000.0000")
        self.assertEqual(result["net_before_tax_source_candidate_kgs"],"900.0000")
        self.assertEqual(result["cash_refund_evidence_kgs"],"100.0000")
        self.assertEqual(result["unclassified_or_supplier_overlap_expense_kgs"],"1200.0000")
        self.assertIsNone(result["recognized_profit_kgs"])
        self.assertFalse(result["accounting_posted"])
        self.assertEqual(len(conn.calls),3)
        self.assertTrue(all(pid==prop for _,pid in conn.calls))


if __name__=="__main__":
    unittest.main()
