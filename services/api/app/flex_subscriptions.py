"""MARINA FLEX subscription state-machine and non-issuable invoice previews.

Pure functions. NOT integrated with hotel operations or production database.
Booleans/evidence passed here must later be obtained from trusted RLS-scoped
database records, never from client JSON. The module does not issue invoices,
send QR, confirm bank payments, change entitlements or suspend a hotel.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from .flex_foundation import money
from .flex_pricing import CommercialQuote

SubscriptionState = Literal[
    "TRIAL", "ACTIVE", "PAYMENT_DUE", "GRACE",
    "SUSPENDED", "CANCELLED", "GRANDFATHERED",
]
LifecycleEvent = Literal[
    "MARK_PAYMENT_DUE", "ENTER_GRACE", "SUSPEND_EXPIRED", "REACTIVATE_PAID",
]
VALID_STATES = frozenset({
    "TRIAL", "ACTIVE", "PAYMENT_DUE", "GRACE", "SUSPENDED",
    "CANCELLED", "GRANDFATHERED",
})
VALID_EVENTS = frozenset({
    "MARK_PAYMENT_DUE", "ENTER_GRACE", "SUSPEND_EXPIRED", "REACTIVATE_PAID",
})


@dataclass(frozen=True)
class BillingEvidence:
    """Database-derived ledger evidence, not a payment receipt screenshot."""
    invoice_id: str
    outstanding: Decimal
    currency: str
    last_verified_payment_id: str | None = None


@dataclass(frozen=True)
class SubscriptionEvidence:
    """This evidence must come from verified, transactional FLEX records."""
    hotel_link_verified: bool
    agreement_signed: bool
    current_status: str
    payment_due_at: datetime
    grace_until: datetime | None
    billing: BillingEvidence


@dataclass(frozen=True)
class StateDecision:
    previous: str
    next_state: str
    event: str
    reason: str


def decide_subscription_state(
    *,
    event: str,
    evidence: SubscriptionEvidence,
    now: datetime,
) -> StateDecision:
    """Fail closed for unknown state/event, unaudited reconciliation and time."""
    if event not in VALID_EVENTS or evidence.current_status not in VALID_STATES:
        raise ValueError("Unknown subscription transition")
    if now.tzinfo is None or evidence.payment_due_at.tzinfo is None:
        raise ValueError("Dates must be timezone-aware")
    if evidence.grace_until is not None:
        if evidence.grace_until.tzinfo is None:
            raise ValueError("Grace end must be timezone-aware")
        if evidence.grace_until < evidence.payment_due_at:
            raise ValueError("Grace cannot end before payment due time")
    try:
        uuid.UUID(evidence.billing.invoice_id)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Ledger invoice ID is invalid") from None
    if evidence.billing.currency != "KGS":
        raise ValueError("Subscription ledger currency mismatch")
    outstanding = money(evidence.billing.outstanding)
    if outstanding < 0:
        raise ValueError("Negative balance requires a credit or reversal, not a transition")
    if not evidence.hotel_link_verified or not evidence.agreement_signed:
        raise ValueError("Verified hotel link and signed contract required")
    current = evidence.current_status
    if current in {"CANCELLED", "GRANDFATHERED"}:
        raise ValueError("Cannot automatically modify cancelled or grandfathered subscription")

    if event == "MARK_PAYMENT_DUE":
        if current != "ACTIVE" or now < evidence.payment_due_at or outstanding <= 0:
            raise ValueError("ACTIVE invoice must be overdue before PAYMENT_DUE")
        return StateDecision(current, "PAYMENT_DUE", event, "VERIFIED_BALANCE_OVERDUE")

    if event == "ENTER_GRACE":
        if (current != "PAYMENT_DUE" or now < evidence.payment_due_at
                or evidence.grace_until is None or now >= evidence.grace_until
                or outstanding <= 0):
            raise ValueError("Grace requires overdue balance and unexpired contractual window")
        return StateDecision(current, "GRACE", event, "CONTRACTUAL_GRACE")

    if event == "SUSPEND_EXPIRED":
        if (current not in {"PAYMENT_DUE", "GRACE"} or now < evidence.payment_due_at
                or (evidence.grace_until is not None and now < evidence.grace_until)
                or outstanding <= 0):
            raise ValueError("Cannot suspend before grace expiry with unpaid debt")
        return StateDecision(current, "SUSPENDED", event, "OVERDUE_GRACE_EXPIRED")

    if event == "REACTIVATE_PAID":
        if current not in {"SUSPENDED", "GRACE", "PAYMENT_DUE"}:
            raise ValueError("Reactivation requires previously restricted subscription")
        if outstanding != 0 or not evidence.billing.last_verified_payment_id:
            raise ValueError("Confirmed paid ledger balance is required for reactivation")
        try:
            uuid.UUID(evidence.billing.last_verified_payment_id)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Verified payment ID is invalid") from None
        return StateDecision(current, "ACTIVE", event, "CONFIRMED_PAYMENT_RECONCILED")

    raise ValueError("Unsupported transition")


@dataclass(frozen=True)
class InvoicePreview:
    """A draft quote with explicit no-payable/no-QR semantics."""
    hotel_id: str
    agreement_id: str
    period_start: str
    period_end: str
    currency: str
    amount_excluding_unresolved_taxes: Decimal
    quote_fingerprint: str
    preview_id: str
    status: str = "NON_ISSUABLE"
    invoice_number: None = None
    qr_reference: None = None


def prepare_invoice_preview(
    *,
    quote: CommercialQuote,
    agreement_id: str,
    agreement_signed: bool,
    hotel_link_verified: bool,
) -> InvoicePreview:
    """Calculate a reproducible draft, with NO authority to create an invoice.

    The final invoice implementation must resolve taxes, discounts, agreement
    versions, RLS, issuance transaction and provider confirmation separately.
    """
    try:
        agreement_id = str(uuid.UUID(agreement_id))
        hotel = str(uuid.UUID(quote.hotel_id))
    except (TypeError, ValueError, AttributeError):
        raise ValueError("Invalid trusted identifiers") from None
    if not agreement_signed or not hotel_link_verified:
        raise ValueError("Verified hotel agreement and PMS link required")
    if quote.currency != "KGS" or quote.tax_status != "NOT_CALCULATED":
        raise ValueError("Unexpected quote currency or fiscal status")
    amount = money(quote.subtotal)
    if amount < 0:
        raise ValueError("Negative drafts require a separate credit note")
    snapshot = {
        "agreement_id": agreement_id,
        "hotel_id": hotel,
        "period_start": quote.period_start.isoformat(),
        "period_end": quote.period_end.isoformat(),
        "quote_fingerprint": quote.quote_fingerprint,
    }
    preview_id = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return InvoicePreview(
        hotel_id=hotel, agreement_id=agreement_id,
        period_start=quote.period_start.isoformat(),
        period_end=quote.period_end.isoformat(),
        currency="KGS", amount_excluding_unresolved_taxes=amount,
        quote_fingerprint=quote.quote_fingerprint, preview_id=preview_id,
    )
