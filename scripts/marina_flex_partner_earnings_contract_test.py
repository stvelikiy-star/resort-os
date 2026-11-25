#!/usr/bin/env python3
"""MARINA FLEX referral/investor cash-share math, no database or money movement."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.flex_partner_earnings import (
    CashAllocationEvidence, EarningsRule, EarningsEntry,
    InvestorRepaymentSnapshot, calculate_earnings_proposal,
    investor_phase, summarize_earnings, quote_agent_month,
    investor_full_calendar_bonus_window, investor_principal_accrual, allocate_annual_subscription,
)

HOTEL_A="00000000-0000-0000-0000-00000000000a"
HOTEL_B="00000000-0000-0000-0000-00000000000b"
ALLOC="00000000-0000-0000-0000-00000000000c"
LINE="00000000-0000-0000-0000-00000000000d"
AGENT="00000000-0000-0000-0000-00000000000e"
INVESTOR="00000000-0000-0000-0000-00000000000f"
AGENT_RULE="00000000-0000-0000-0000-000000000010"
INVESTOR_RULE="00000000-0000-0000-0000-000000000011"
AT=datetime(2026,11,22,14,0,tzinfo=timezone.utc)


class EarnedCommissionAndInvestorRevenue(unittest.TestCase):
    def cash(self,source="CI_SIGNED_FIXTURE_NOT_BANK"):
        return CashAllocationEvidence(
            allocation_id=ALLOC, hotel_id=HOTEL_A, invoice_line_id=LINE,
            currency="KGS", gross_allocated=Decimal("1000.00"),
            net_tax_excluded_eligible=Decimal("900.00"),
            refund_allocation_total=Decimal("0.00"),
            source=source, settled_at=AT, active_agreement=True,
        )

    def agent(self):
        return EarningsRule(AGENT,AGENT_RULE,HOTEL_A,"BASE_PMS",1500,date(2026,1,1))

    def investor(self):
        return EarningsRule(INVESTOR,INVESTOR_RULE,HOTEL_A,"BASE_PMS",3000,date(2026,1,1))

    def quote(self, cash=None, agent=None, investor=None):
        return calculate_earnings_proposal(
            cash=cash or self.cash(), sku="BASE_PMS",
            agent_rule=self.agent() if agent is None else agent,
            investor_rule=self.investor() if investor is None else investor,
        )

    def test_commissions_use_tax_excluded_cash_not_billed_revenue(self):
        result=self.quote()
        self.assertEqual(result.eligible_base,Decimal("900.00"))
        self.assertEqual(result.agent_amount,Decimal("135.00"))
        self.assertEqual(result.investor_amount,Decimal("270.00"))
        self.assertFalse(result.bank_validated)
        self.assertEqual(result.status,"CALCULATION_ONLY_NO_PAYOUT")

    def test_bank_evidence_not_also_a_bank_payout(self):
        result=self.quote(cash=self.cash(source="BANK_RECONCILED"))
        self.assertTrue(result.bank_validated)
        self.assertEqual(result.status,"CALCULATION_ONLY_NO_PAYOUT")

    def test_refund_reverses_eligible_cash_shares(self):
        full=self.quote()
        half=self.quote(cash=replace(self.cash(),refund_allocation_total=Decimal("500.00")))
        self.assertEqual(half.eligible_base,Decimal("450.00"))
        self.assertEqual(half.agent_amount,Decimal("67.50"))
        self.assertEqual(half.investor_amount,Decimal("135.00"))
        self.assertEqual(full.agent_amount-half.agent_amount,Decimal("67.50"))

    def test_full_refund_erases_commission(self):
        all_back=self.quote(cash=replace(self.cash(),refund_allocation_total=Decimal("1000")))
        self.assertEqual(all_back.eligible_base,Decimal("0.00"))
        self.assertEqual(all_back.agent_amount,Decimal("0.00"))
        self.assertEqual(all_back.investor_amount,Decimal("0.00"))

    def test_rule_scope_wrong_hotel_or_sku_never_passes(self):
        for invalid in (
            replace(self.agent(),scope_hotel_id=HOTEL_B),
            replace(self.agent(),scope_sku="ADDON"),
            replace(self.agent(),effective_on=date(2027,1,1)),
            replace(self.agent(),expires_after=date(2026,1,1)),
        ):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                self.quote(agent=invalid)

    def test_untrusted_receipt_and_currency_rejected(self):
        for changes in (
            {"source":"UPLOADED_SCREENSHOT"},
            {"source":"FINIK_UNVERIFIED_WEBHOOK"},
            {"currency":"USD"},
            {"active_agreement":False},
            {"net_tax_excluded_eligible":Decimal("1100")},
            {"refund_allocation_total":Decimal("1200")},
            {"refund_allocation_total":Decimal("-1")},
        ):
            with self.subTest(change=changes),self.assertRaises(ValueError):
                self.quote(cash=replace(self.cash(),**changes))

    def test_cannot_commit_more_than_receipt_net_base(self):
        with self.assertRaises(ValueError):
            self.quote(agent=replace(self.agent(),rate_bps=8000),
                       investor=replace(self.investor(),rate_bps=6000))
        with self.assertRaises(ValueError):
            self.quote(agent=replace(self.agent(),rate_bps=10001))

    def test_no_floats_or_nonfinite_amounts(self):
        for amount in (1.0, Decimal("NaN"),Decimal("Infinity")):
            with self.subTest(amount=amount),self.assertRaises(ValueError):
                self.quote(cash=replace(self.cash(),gross_allocated=amount))


class CashRepaidInvestorPhases(unittest.TestCase):
    def contract(self, paid="0", accrued="0", repaid=None, months=6):
        return InvestorRepaymentSnapshot(
            original_principal=Decimal("150000"), principal_cash_paid_out=Decimal(paid),
            principal_accrued=Decimal(accrued),
            repaid_at=repaid, bonus_months=months,
        )

    def test_accrual_does_not_advance_return_phase(self):
        s=self.contract(paid="0",accrued="200000")
        self.assertEqual(investor_phase(s,on=date(2026,11,22)),"RETURN")
        paid_partial=self.contract(paid="149999.99",accrued="250000")
        self.assertEqual(investor_phase(paid_partial,on=date(2026,11,22)),"RETURN")

    def test_bonus_begins_at_actual_final_payout(self):
        s=self.contract(paid="150000",accrued="300000",repaid=date(2026,11,22))
        self.assertEqual(investor_phase(s,on=date(2026,11,22)),"BONUS")
        self.assertEqual(investor_phase(s,on=date(2027,5,21)),"BONUS")
        self.assertEqual(investor_phase(s,on=date(2027,5,22)),"ENDED")

    def test_monthend_leap_year_bonus(self):
        s=self.contract(paid="150000",repaid=date(2027,8,31))
        self.assertEqual(investor_phase(s,on=date(2028,2,28)),"BONUS")
        self.assertEqual(investor_phase(s,on=date(2028,2,29)),"ENDED")

    def test_no_bonus_without_cash_proof(self):
        with self.assertRaises(ValueError):
            investor_phase(self.contract(paid="150000",repaid=None),on=date(2026,11,22))
        with self.assertRaises(ValueError):
            investor_phase(self.contract(paid="500",repaid=date(2026,11,22)),on=date(2026,11,22))
        with self.assertRaises(ValueError):
            investor_phase(self.contract(paid="150001",repaid=date(2026,11,22)),on=date(2026,11,22))
        with self.assertRaises(ValueError):
            investor_phase(self.contract(paid="150000",repaid=date(2026,11,23)),on=date(2026,11,22))


class PeriodicEarningsDashboard(unittest.TestCase):
    def test_daily_weekly_monthly_and_refund_can_be_negative(self):
        # UTC+6 makes 18:30 UTC 00:30 local on following day.
        entries=(
            EarningsEntry(datetime(2026,11,21,18,30,tzinfo=timezone.utc),
                          positive_accrual=Decimal("100.00")),
            EarningsEntry(datetime(2026,11,22,10,tzinfo=timezone.utc),
                          reversal=Decimal("160.00")),
            EarningsEntry(datetime(2026,11,22,10,tzinfo=timezone.utc),
                          bank_payout=Decimal("20.00")),
            EarningsEntry(datetime(2026,11,20,10,tzinfo=timezone.utc),
                          positive_accrual=Decimal("1000.00")),
        )
        day=summarize_earnings(entries,start=date(2026,11,22),end=date(2026,11,22))
        self.assertEqual(day["accrued_gross"],"100.00")
        self.assertEqual(day["reversed"],"160.00")
        self.assertEqual(day["net_accrued_in_period"],"-60.00")
        self.assertEqual(day["actual_paid_in_period"],"20.00")
        week=summarize_earnings(entries,start=date(2026,11,16),end=date(2026,11,22))
        self.assertEqual(week["accrued_gross"],"1100.00")
        self.assertEqual(week["net_accrued_in_period"],"940.00")
        self.assertEqual(week["currency"],"KGS")

    def test_missing_timezone_rejected(self):
        with self.assertRaises(ValueError):
            summarize_earnings(
                (EarningsEntry(datetime(2026,11,22,10),positive_accrual=Decimal("1")),),
                start=date(2026,11,22),end=date(2026,11,22),
            )



class ApprovedCommercialTerms(unittest.TestCase):
    def test_agent_fixed_compensation_and_termination(self):
        q = quote_agent_month(employed_full_month=True,
            new_paid_hotel_ids=(HOTEL_A, HOTEL_B),
            paid_addon_keys=((HOTEL_A,"QR_ZONE"),(HOTEL_B,"QR_ZONE")))
        self.assertEqual(q.total, Decimal("25000"))
        self.assertEqual(q.sales_target, 7)
        self.assertEqual(quote_agent_month(employed_full_month=False,
            new_paid_hotel_ids=(), paid_addon_keys=()).total, Decimal(0))
        with self.assertRaises(ValueError):
            quote_agent_month(employed_full_month=False,
                new_paid_hotel_ids=(HOTEL_A,), paid_addon_keys=())
        with self.assertRaises(ValueError):
            quote_agent_month(employed_full_month=True,
                new_paid_hotel_ids=(HOTEL_A,HOTEL_A), paid_addon_keys=())

    def test_investor_full_months_and_principal_cap(self):
        self.assertEqual(investor_full_calendar_bonus_window(date(2026,11,25)),
            (date(2026,12,1),date(2027,3,1)))
        self.assertEqual(investor_principal_accrual(
            eligible_subscription=Decimal("200000"), rate_bps=3500,
            original_principal=Decimal("250000"), principal_paid=Decimal("210000"),
            principal_unpaid_accrued=Decimal("10000")), Decimal("30000"))

    def test_annual_payment_exact_reconciliation(self):
        shares = allocate_annual_subscription(Decimal("108000.01"))
        self.assertEqual(len(shares),12)
        self.assertEqual(sum(shares),Decimal("108000.01"))
        self.assertEqual(shares[0],Decimal("9000.01"))
        self.assertEqual(shares[-1],Decimal("9000"))


if __name__=="__main__":
    unittest.main(verbosity=2)
