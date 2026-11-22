"""MARINA SMART FLEX commercial domain primitives (no I/O or side effects).

This module is deliberately NOT wired to existing PMS routes or databases.
A billing control plane and verified hotel identity are required before
enforcement. Existing hotel access is therefore unchanged by importing it.

All money is Decimal, in the invoice currency's minor units (KGS = 0.01).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from calendar import monthrange
from typing import Iterable

KGS_MINOR_UNIT = Decimal("0.01")
ENFORCEMENT_MODES = frozenset({"OFF", "SHADOW", "ENFORCE"})
FEATURE_STATES = frozenset({"ON", "GRACE", "READ_ONLY", "OFF"})
SAFE_LIFECYCLE_OPERATIONS = frozenset({
    "PAY_SUBSCRIPTION", "READ_BILLING", "EXPORT_DATA", "AUDIT_READ",
    "FINISH_ACTIVE_STAY", "SETTLE_EXISTING_PAYMENT", "PROCESS_REFUND",
})


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    would_deny: bool
    reason: str
    enforcement: str


def decide_feature_access(
    *,
    enforcement: str,
    feature_state: str | None,
    operation: str,
    is_core: bool = False,
    valid_until: datetime | None = None,
    now: datetime | None = None,
) -> AccessDecision:
    """Evaluate a commercial entitlement ONLY, never staff RBAC.

    A caller must independently authorize the authenticated user, hotel scope,
    business operation and deployment capability BEFORE using this decision.
    OFF and SHADOW never deny. Core and safety operations are never paywalled.
    """
    if enforcement not in ENFORCEMENT_MODES:
        raise ValueError("Unknown enforcement mode")
    if operation not in {"READ", "WRITE"} | SAFE_LIFECYCLE_OPERATIONS:
        raise ValueError("Unknown operation")
    if valid_until is not None:
        if valid_until.tzinfo is None or now is None or now.tzinfo is None:
            raise ValueError("Expiry and now must be timezone-aware")
    if is_core or operation in SAFE_LIFECYCLE_OPERATIONS:
        return AccessDecision(True, False, "CORE_OR_SAFETY_EXEMPT", enforcement)
    if enforcement == "OFF":
        return AccessDecision(True, False, "ENFORCEMENT_OFF", enforcement)

    state = feature_state if feature_state in FEATURE_STATES else "OFF"
    if state == "GRACE" and (valid_until is None or now is None or now >= valid_until):
        state = "READ_ONLY"
    authorized = state in {"ON", "GRACE"} or (state == "READ_ONLY" and operation == "READ")
    reason = "ENTITLED" if authorized else ("READ_ONLY" if state == "READ_ONLY" else "NOT_ENTITLED")
    if enforcement == "SHADOW":
        return AccessDecision(True, not authorized, reason, enforcement)
    return AccessDecision(authorized, not authorized, reason, enforcement)


def money(value: Decimal | int | str) -> Decimal:
    """Validate a finite amount in som; floats are forbidden."""
    if isinstance(value, float) or isinstance(value, bool):
        raise TypeError("Use Decimal, int or a decimal string, not float/bool")
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not amount.is_finite():
        raise ValueError("Amount must be finite")
    return amount.quantize(KGS_MINOR_UNIT, rounding=ROUND_HALF_UP)


def percent_of(amount: Decimal | int | str, basis_points: int) -> Decimal:
    """Calculate a commission/share from a CONFIRMED payment allocation."""
    if not isinstance(basis_points, int) or isinstance(basis_points, bool) or not (0 <= basis_points <= 10000):
        raise ValueError("basis_points must be an integer 0..10000")
    base = money(amount)
    if base < 0:
        raise ValueError("Use a separate reversal event for refunds")
    return money(base * Decimal(basis_points) / Decimal(10000))


def prorate_calendar_month(
    monthly_price: Decimal | int | str, *, active_from: date, period_start: date, period_end: date,
) -> Decimal:
    """Draft daily-proration option; period must be exactly a calendar month.

    Business must approve this pricing convention before use in live billing.
    active_from is inclusive. All dates use the property's contracted time zone.
    """
    monthly = money(monthly_price)
    if monthly < 0:
        raise ValueError("Negative monthly price")
    if period_start.day != 1 or period_end != date(
        period_start.year, period_start.month, monthrange(period_start.year, period_start.month)[1]
    ):
        raise ValueError("Billing period must be a single complete calendar month")
    if active_from <= period_start:
        return monthly
    if active_from > period_end:
        return Decimal("0.00")
    days = period_end.day
    active_days = (period_end - active_from).days + 1
    return money(monthly * Decimal(active_days) / Decimal(days))


@dataclass(frozen=True)
class InvoiceBalance:
    line_id: str
    unpaid: Decimal


@dataclass(frozen=True)
class PaymentAllocation:
    line_id: str
    amount: Decimal


@dataclass(frozen=True)
class AllocationResult:
    allocations: tuple[PaymentAllocation, ...]
    unallocated_credit: Decimal


def allocate_confirmed_payment(
    amount: Decimal | int | str,
    lines: Iterable[InvoiceBalance],
) -> AllocationResult:
    """Deterministic invoice-line allocation, in the supplied invoice-line order.

    Only call after external payment confirmation and currency/invoice checks.
    Idempotency and concurrent allocation are *database* responsibilities.
    Excess payment remains an explicit credit, not phantom feature revenue.
    """
    remaining = money(amount)
    if remaining <= 0:
        raise ValueError("Payment amount must be positive")
    allocations: list[PaymentAllocation] = []
    seen: set[str] = set()
    for line in lines:
        if not line.line_id or line.line_id in seen:
            raise ValueError("Invoice line IDs must be nonempty and unique")
        seen.add(line.line_id)
        due = money(line.unpaid)
        if due < 0:
            raise ValueError("Outstanding invoice balance cannot be negative")
        allocated = min(remaining, due)
        if allocated:
            allocations.append(PaymentAllocation(line.line_id, allocated))
        remaining -= allocated
    return AllocationResult(tuple(allocations), remaining)
