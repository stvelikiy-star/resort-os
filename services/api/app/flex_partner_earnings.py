"""MARINA FLEX agent/investor earnings calculations — side-effect-free.

These are LIABILITY PROPOSALS, NOT BANK PAYOUTS. Inputs must be reconstructed
from trusted, tenant-scoped allocation and reversal records, approved agent
rules, and legally signed investor contracts. Synthetic CI receipts may only
generate QA estimates. Never accept rates or source verification from a client.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

KGS_CENT = Decimal("0.01")
MAX_MONEY = Decimal("9999999999999999.99")
ELIGIBLE_SOURCES = frozenset({"BANK_RECONCILED", "CI_SIGNED_FIXTURE_NOT_BANK"})


def _money(value: Decimal) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("Use finite Decimal, never floating point")
    rounded = value.quantize(KGS_CENT, rounding=ROUND_HALF_UP)
    if rounded < 0 or rounded > MAX_MONEY:
        raise ValueError("Invalid KGS amount")
    return rounded


def _uuid(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid identifier")
    try:
        normalized = str(uuid.UUID(value))
    except ValueError:
        raise ValueError("Invalid identifier") from None
    if normalized != value:
        raise ValueError("Noncanonical identifier")
    return normalized


def _rate(value: int) -> int:
    if type(value) is not int or not 0 <= value <= 10000:
        raise ValueError("Rate must be explicit signed contract basis points")
    return value


@dataclass(frozen=True)
class CashAllocationEvidence:
    allocation_id: str
    hotel_id: str
    invoice_line_id: str
    currency: str
    gross_allocated: Decimal
    net_tax_excluded_eligible: Decimal
    refund_allocation_total: Decimal
    source: str
    settled_at: datetime
    active_agreement: bool


@dataclass(frozen=True)
class EarningsRule:
    party_id: str
    rule_version_id: str
    scope_hotel_id: str
    scope_sku: str
    rate_bps: int
    effective_on: date
    expires_after: date | None = None


@dataclass(frozen=True)
class EarningsProposal:
    allocation_id: str
    hotel_id: str
    agent_id: str | None
    investor_id: str | None
    agent_amount: Decimal
    investor_amount: Decimal
    eligible_base: Decimal
    bank_validated: bool
    status: str = "CALCULATION_ONLY_NO_PAYOUT"


def calculate_earnings_proposal(
    *,
    cash: CashAllocationEvidence,
    sku: str,
    agent_rule: EarningsRule | None,
    investor_rule: EarningsRule | None,
) -> EarningsProposal:
    """One allocation + zero/one approved agent/investor rule.

    Contract writers must independently prohibit parallel overlapping rules
    and check cumulative liabilities across all scoped contracts. This function
    caps only the input pair; it does not authorize an accrual database INSERT.
    """
    allocation = _uuid(cash.allocation_id)
    hotel = _uuid(cash.hotel_id)
    _uuid(cash.invoice_line_id)
    if not isinstance(sku, str) or not sku or len(sku) > 80:
        raise ValueError("Invalid SKU")
    if cash.currency != "KGS" or cash.source not in ELIGIBLE_SOURCES:
        raise ValueError("Unknown cash origin or currency")
    if not cash.active_agreement:
        raise ValueError("Unsigned commercial contract or missing approval")
    if cash.settled_at.tzinfo is None:
        raise ValueError("Settlement timestamp must be timezone-aware")

    gross = _money(cash.gross_allocated)
    net = _money(cash.net_tax_excluded_eligible)
    reversed_total = _money(cash.refund_allocation_total)
    if reversed_total > gross or net > gross:
        raise ValueError("Refund or pre-tax base exceeds paid invoice allocation")
    # Caller supplies the entire original allocation's tax-excluded amount.
    # Reverse eligibility in proportion to actually refunded gross allocation,
    # then cap to the original eligible portion to prevent a negative balance.
    refundable_net = (
        min(net, (net * reversed_total / gross).quantize(KGS_CENT, rounding=ROUND_HALF_UP))
        if gross else Decimal("0.00")
    )
    eligible = _money(net - refundable_net)
    if gross == 0 and (net or reversed_total):
        raise ValueError("Zero paid allocation cannot support earnings")

    def earning(rule: EarningsRule | None) -> Decimal:
        if rule is None:
            return Decimal("0.00")
        _uuid(rule.party_id)
        _uuid(rule.rule_version_id)
        if _uuid(rule.scope_hotel_id) != hotel or rule.scope_sku != sku:
            raise ValueError("Rule scope does not match receipt")
        if (rule.effective_on > cash.settled_at.date()
                or (rule.expires_after and cash.settled_at.date() > rule.expires_after)):
            raise ValueError("Rule not effective at settlement")
        return (eligible * Decimal(_rate(rule.rate_bps)) / Decimal(10000)).quantize(
            KGS_CENT, rounding=ROUND_HALF_UP
        )

    agent = earning(agent_rule)
    investor = earning(investor_rule)
    if agent + investor > eligible:
        raise ValueError("Overcommitted eligible revenue")
    return EarningsProposal(
        allocation_id=allocation,
        hotel_id=hotel,
        agent_id=agent_rule.party_id if agent_rule else None,
        investor_id=investor_rule.party_id if investor_rule else None,
        agent_amount=agent,
        investor_amount=investor,
        eligible_base=eligible,
        bank_validated=(cash.source == "BANK_RECONCILED"),
    )


@dataclass(frozen=True)
class InvestorRepaymentSnapshot:
    """Principal completion is governed by actual approved cash payouts."""
    original_principal: Decimal
    principal_cash_paid_out: Decimal
    principal_accrued: Decimal
    repaid_at: date | None
    bonus_months: int


def investor_phase(snapshot: InvestorRepaymentSnapshot, *, on: date) -> str:
    principal = _money(snapshot.original_principal)
    cash_paid = _money(snapshot.principal_cash_paid_out)
    accrued = _money(snapshot.principal_accrued)
    if type(snapshot.bonus_months) is not int or snapshot.bonus_months < 0 or snapshot.bonus_months > 36:
        raise ValueError("Invalid bonus duration")
    if principal <= 0 or cash_paid > principal:
        raise ValueError("Invalid principal/payout terms")
    if cash_paid < principal:
        if snapshot.repaid_at is not None:
            raise ValueError("Principal not actually repaid")
        return "RETURN"
    if snapshot.repaid_at is None or type(snapshot.repaid_at) is not date:
        raise ValueError("Verified principal repayment date required")
    if snapshot.repaid_at > on:
        raise ValueError("Bonus period cannot precede cash repayment")
    # Six calendar months etc., rather than treating a 30-day duration as a month.
    start = snapshot.repaid_at
    absolute_month = start.year * 12 + start.month - 1 + snapshot.bonus_months
    end_year, end_month = divmod(absolute_month, 12)
    # end_month is zero-based; match end-exclusive day when month shorter.
    from calendar import monthrange
    end_date = date(end_year, end_month + 1,
                    min(start.day, monthrange(end_year, end_month + 1)[1]))
    return "BONUS" if on < end_date else "ENDED"


@dataclass(frozen=True)
class EarningsEntry:
    credited_at: datetime
    positive_accrual: Decimal = Decimal("0.00")
    reversal: Decimal = Decimal("0.00")
    bank_payout: Decimal = Decimal("0.00")


def summarize_earnings(
    entries: tuple[EarningsEntry, ...],
    *,
    start: date,
    end: date,
    timezone_name: str = "Asia/Bishkek",
) -> dict[str, str]:
    """Local-day summary for dashboard, no access to identities or guest data."""
    if start > end or (end - start).days > 366:
        raise ValueError("Invalid dashboard period")
    tz = ZoneInfo(timezone_name)
    accrued = reversed_total = paid = Decimal("0.00")
    for entry in entries:
        if entry.credited_at.tzinfo is None:
            raise ValueError("Ledger event lacks a timezone")
        local_day = entry.credited_at.astimezone(tz).date()
        if start <= local_day <= end:
            accrued += _money(entry.positive_accrual)
            reversed_total += _money(entry.reversal)
            paid += _money(entry.bank_payout)
    net = (accrued - reversed_total).quantize(KGS_CENT, rounding=ROUND_HALF_UP)
    if abs(net) > MAX_MONEY:
        raise ValueError("Dashboard net accrual exceeds financial range")
    return {
        "accrued_gross": f"{_money(accrued):.2f}",
        "reversed": f"{_money(reversed_total):.2f}",
        "net_accrued_in_period": f"{net:.2f}",
        "actual_paid_in_period": f"{_money(paid):.2f}",
        "currency": "KGS",
    }
