"""Pure Decimal/flag tests for OWNER inventory valuation without production writes."""
import unittest
import uuid
from decimal import Decimal

from services.api.app.owner_kitchen_reconciliation import summarize_stock, kgs


class OwnerReconciliationContracts(unittest.TestCase):
    def test_weighted_ledger_value_is_not_catalog_estimate(self):
        rows=[
            {"id":uuid.uuid4(),"isSample":False,
             "costPerUnitKgs":Decimal("100.0000"),
             "balance":Decimal("8.000000"),
             "book_value":Decimal("893.8267")},
            {"id":uuid.uuid4(),"isSample":True,
             "costPerUnitKgs":Decimal("1.0000"),
             "balance":Decimal("4.000000"),
             "book_value":Decimal("0.0000")},
        ]
        actual=summarize_stock(rows)
        self.assertEqual(actual["real_book_inventory_value_kgs"],"893.8267")
        self.assertEqual(actual["real_catalog_estimate_kgs"],"800.0000")
        self.assertEqual(actual["sample_book_inventory_value_kgs"],"0.0000")
        self.assertEqual(actual["sample_catalog_estimate_kgs"],"4.0000")
        self.assertEqual(actual["valuation_status"],"MOVEMENT_BASED")

    def test_legacy_negative_and_nonzero_zero_balance_are_marked_unavailable(self):
        for balance,value in [("-1.000000","10.0000"),("2.000000","-1.0000"),
                              ("0.000000","0.0500")]:
            with self.subTest(balance=balance,value=value):
                row={"id":uuid.uuid4(),"isSample":False,
                     "costPerUnitKgs":Decimal("100"),
                     "balance":Decimal(balance),"book_value":Decimal(value)}
                r=summarize_stock([row])
                self.assertEqual(r["invalid_item_count"],1)
                self.assertEqual(r["valuation_status"],"RECONCILIATION_REQUIRED")
                self.assertIsNone(r["real_book_inventory_value_kgs"])
                self.assertIsNone(r["sample_book_inventory_value_kgs"])

    def test_zero_stock_and_immaterial_rounding(self):
        row={"id":uuid.uuid4(),"isSample":False,
             "costPerUnitKgs":Decimal("100"),
             "balance":Decimal("0"),"book_value":Decimal("0.005")}
        r=summarize_stock([row])
        self.assertEqual(r["valuation_status"],"MOVEMENT_BASED")
        self.assertEqual(r["real_book_inventory_value_kgs"],"0.0050")

    def test_no_floating_point_som_rounding(self):
        self.assertEqual(kgs(Decimal("140.12345")),"140.1235")
        self.assertEqual(kgs(Decimal("2")*Decimal("111.7284")),"223.4568")


if __name__=="__main__":
    unittest.main()
