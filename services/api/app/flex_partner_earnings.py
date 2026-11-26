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


@dataclass(frozen=True)
class AgentMonthQuote:
    salary: Decimal
    connections: Decimal
    modules: Decimal
    total: Decimal
    sales_target: int
    new_hotels: int


def quote_agent_month(*, employed_full_month: bool,
                      new_paid_hotel_ids: tuple[str, ...],
                      paid_addon_keys: tuple[tuple[str, str], ...],
                      salary: Decimal = Decimal("10000"),
                      connection_fee: Decimal = Decimal("7000"),
                      addon_fee: Decimal = Decimal("500"),
                      sales_target: int = 7) -> AgentMonthQuote:
    """Full-month calculation only. Caller verifies distinct first connections,
    paid add-on months, contract scope, refunds and previous accruals.
    Partial employment months require a separate approved calculation.
    """
    if type(employed_full_month) is not bool or type(sales_target) is not int or sales_target < 0:
        raise ValueError("Invalid employment or target")
    for hotel in new_paid_hotel_ids:
        _uuid(hotel)
    for hotel, sku in paid_addon_keys:
        _uuid(hotel)
        if not isinstance(sku, str) or not sku or sku in {"BASE", "BASE_PMS", "PMS"}:
            raise ValueError("Invalid paid additional module")
    if len(set(new_paid_hotel_ids)) != len(new_paid_hotel_ids) or len(set(paid_addon_keys)) != len(paid_addon_keys):
        raise ValueError("Duplicate commission evidence")
    salary, connection_fee, addon_fee = map(_money, (salary, connection_fee, addon_fee))
    if not employed_full_month:
        if new_paid_hotel_ids or paid_addon_keys:
            raise ValueError("Employment eligibility must be resolved before calculation")
        salary = Decimal("0.00")
    connections = _money(connection_fee * len(new_paid_hotel_ids))
    modules = _money(addon_fee * len(paid_addon_keys))
    return AgentMonthQuote(salary, connections, modules, _money(salary + connections + modules),
                           sales_target, len(new_paid_hotel_ids))


def investor_full_calendar_bonus_window(repaid_at: date, months: int = 3) -> tuple[date, date]:
    """Start on the first day of the month AFTER confirmed principal repayment;
    end exclusive after the contracted number of full calendar months.
    """
    if type(repaid_at) is not date or type(months) is not int or not 1 <= months <= 36:
        raise ValueError("Invalid repayment date or duration")
    first = repaid_at.year * 12 + repaid_at.month
    year, month = divmod(first, 12)
    end_year, end_month = divmod(first + months, 12)
    return date(year, month + 1, 1), date(end_year, end_month + 1, 1)


def investor_principal_accrual(*, eligible_subscription: Decimal, rate_bps: int,
                              original_principal: Decimal,
                              principal_paid: Decimal,
                              principal_unpaid_accrued: Decimal) -> Decimal:
    """Cap new principal accrual by remaining uncommitted principal.
    Actual payouts, not accruals, determine transition to bonus.
    """
    principal = _money(original_principal)
    paid = _money(principal_paid)
    accrued = _money(principal_unpaid_accrued)
    if principal <= 0 or paid + accrued > principal:
        raise ValueError("Invalid principal ledger")
    eligible = _money(eligible_subscription)
    return min(principal - paid - accrued,
               _money(eligible * Decimal(_rate(rate_bps)) / Decimal(10000)))


def allocate_annual_subscription(amount: Decimal) -> tuple[Decimal, ...]:
    """Twelve monthly shares, preserving every tiyin exactly."""
    amount = _money(amount)
    cents = int(amount * 100)
    share, remainder = divmod(cents, 12)
    return tuple(Decimal(share + (1 if i < remainder else 0)) / 100 for i in range(12))
