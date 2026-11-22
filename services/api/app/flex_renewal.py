"""MARINA FLEX: read-only, bank-gated renewal decision.

Receipts from a CI simulator may verify arithmetic but NEVER authorize live
subscription extension. No HTTP route, DB writes, entitlements or PMS changes.
"""
from __future__ import annotations

import uuid
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from .flex_foundation import money

TRUSTED_SOURCES = frozenset({"CI_SIGNED_FIXTURE_NOT_BANK", "VERIFIED_BANK_SETTLED"})
ACTIVE_STATES = frozenset({"ACTIVE", "PAYMENT_DUE", "GRACE", "SUSPENDED"})
LOCKED_STATES = frozenset({"CANCELLED", "GRANDFATHERED"})


@dataclass(frozen=True)
class RenewalLedgerEvidence:
    subscription_id: str
    hotel_id: str
    invoice_id: str
    invoice_hotel_id: str
    agreement_version_id: str
    invoice_agreement_version_id: str
    current_state: str
    current_period_end: date
    invoice_period_start: date
    invoice_period_end: date
    invoice_total_kg: Decimal
    refunded_net_allocated_kg: Decimal
    outstanding_kg: Decimal
    settlement_source: str
    last_confirmed_payment_id: str | None
    settlement_confirmed_at: datetime | None
    agreement_signed: bool
    hotel_link_verified: bool
    invoice_finalized: bool


@dataclass(frozen=True)
class RenewalDecision:
    can_prepare: bool
    bank_authorized: bool
    hotel_id: str
    subscription_id: str
    invoice_id: str
    new_period_start: date | None
    new_period_end: date | None
    reason: str
    execution_state: str = "PROPOSAL_ONLY_NO_MUTATION"


def _uuid(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid trusted identifier")
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise ValueError("Invalid trusted identifier") from None


def decide_renewal(e: RenewalLedgerEvidence, *, now: datetime) -> RenewalDecision:
    """Inputs MUST originate in a trusted, consistent DB snapshot."""
    if now.tzinfo is None:
        raise ValueError("Current time must be timezone-aware")
    subscription, hotel, invoice = _uuid(e.subscription_id), _uuid(e.hotel_id), _uuid(e.invoice_id)
    if _uuid(e.invoice_hotel_id) != hotel:
        raise ValueError("Cross-hotel invoice")
    agreement = _uuid(e.agreement_version_id)
    if _uuid(e.invoice_agreement_version_id) != agreement:
        raise ValueError("Cross-contract invoice")
    if e.settlement_source not in TRUSTED_SOURCES:
        raise ValueError("Untrusted source of payment evidence")
    if e.current_state not in ACTIVE_STATES | LOCKED_STATES:
        raise ValueError("Unknown subscription state")
    if any(type(d) is not date for d in (
        e.current_period_end, e.invoice_period_start, e.invoice_period_end
    )):
        raise ValueError("Invalid billing date")
    if (
        e.current_period_end + timedelta(days=1) != e.invoice_period_start
        or e.invoice_period_start.day != 1
        or e.invoice_period_end != date(
            e.invoice_period_start.year, e.invoice_period_start.month,
            monthrange(e.invoice_period_start.year, e.invoice_period_start.month)[1]
        )
    ):
        raise ValueError("Invoice must cover the exact next billing month")

    total, paid, due = (money(e.invoice_total_kg),
                        money(e.refunded_net_allocated_kg), money(e.outstanding_kg))
    if min(total, paid, due) < 0 or paid > total or money(total-paid) != due:
        raise ValueError("Commercial ledger is not reconciled")
    base = dict(hotel_id=hotel, subscription_id=subscription, invoice_id=invoice,
                new_period_start=None, new_period_end=None)
    if e.current_state in LOCKED_STATES:
        return RenewalDecision(False, False, reason="CANCELLED_OR_GRANDFATHERED", **base)
    if not e.hotel_link_verified or not e.agreement_signed or not e.invoice_finalized:
        return RenewalDecision(False, False, reason="UNVERIFIED_HOTEL_OR_AGREEMENT", **base)
    if total <= 0 or due > 0:
        return RenewalDecision(False, False, reason="INVOICE_UNPAID_OR_REFUNDED", **base)
    if not e.last_confirmed_payment_id or e.settlement_confirmed_at is None:
        return RenewalDecision(False, False, reason="MISSING_CONFIRMED_PAYMENT", **base)
    _uuid(e.last_confirmed_payment_id)
    if e.settlement_confirmed_at.tzinfo is None or e.settlement_confirmed_at > now:
        raise ValueError("Invalid settlement timestamp")
    verified_bank = e.settlement_source == "VERIFIED_BANK_SETTLED"
    return RenewalDecision(
        can_prepare=True, bank_authorized=verified_bank,
        hotel_id=hotel, subscription_id=subscription, invoice_id=invoice,
        new_period_start=e.invoice_period_start, new_period_end=e.invoice_period_end,
        reason=("AWAIT_APPROVED_BANK_RENEWAL_WRITER" if verified_bank
                else "CI_ONLY_NEVER_RENEW_PRODUCTION"),
    )
