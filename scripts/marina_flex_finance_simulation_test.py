"""Synthetic finance exercise only; no production database."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.flex_finance_simulation import simulate_cash


def pay(key,amount):
    return {"kind":"PAYMENT","event_id":key,"amount":amount}


def refund(key,amount,original):
    return {"kind":"REFUND","event_id":key,"amount":amount,"payment_id":original}


class FinanceSimulation(unittest.TestCase):
    def test_launch_package_partial_overpayment_and_refund(self):
        result=simulate_cash("36000","25000",[
            pay("p1","20000"),pay("p2","45000"),refund("r1","9000","p2")])
        self.assertEqual(result["amount_before_unresolved_taxes"],"61000.00")
        self.assertEqual(result["history"][0]["outstanding"],"41000.00")
        self.assertEqual(result["history"][1]["credit"],"4000.00")
        self.assertEqual(result["net_simulated_cash"],"56000.00")
        self.assertEqual(result["outstanding"],"5000.00")
        self.assertEqual(result["credit"],"0.00")
        self.assertEqual(result["subscription_outstanding"],"0.00")
        self.assertEqual(result["discrepancy"],"0.00")
        for field in ("payments_enabled","subscription_activated","launch_offer_finalized"):
            self.assertFalse(result[field])

    def test_invalid_reversal_and_duplicate(self):
        for events in ([refund("r","1","missing")],
            [pay("p","10"),refund("r","11","p")],
            [pay("p","10"),pay("p","10")],
            [pay("p","0.001")],[pay("p","0")],
            [pay("p","10"),refund("r","8","p"),refund("r2","3","p")]):
            with self.subTest(events=events),self.assertRaises(ValueError):
                simulate_cash("100","0",events)

    def test_no_events_and_full_refund(self):
        self.assertEqual(simulate_cash("100","50",[])["outstanding"],"150.00")
        r=simulate_cash("100","50",[pay("p","200"),refund("r","200","p")])
        self.assertEqual((r["net_simulated_cash"],r["outstanding"],r["credit"]),("0.00","150.00","0.00"))


if __name__=="__main__":
    unittest.main(verbosity=2)
