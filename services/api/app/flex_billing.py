"""MARINA FLEX invoice arithmetic and verified-payment reconciliation planning.

Pure commercial-domain primitives. No tax assumptions, invoices, payment provider
credentials, bank claims, mutations or hotel enforcement in this module.

Important: callers MUST derive contract, tax policy, invoice and confirmed
payment records from verified commercial DB transactions, NOT request payloads.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from .flex_foundation import (
    InvoiceBalance, PaymentAllocation, allocate_confirmed_payment, money,
)
from .flex_pricing import CommercialQuote

MAX_KGS = Decimal("9999999999999999.99")


def _id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Expected trusted UUID identifier") from None


@dataclass(frozen=True)
class ApprovedTaxRule:
    """An externally approved tax rule. Rate here is test fixture, NOT local law."""
    version_id: str
    treatment: str  # ADDED / EXEMPT; INCLUSIVE needs a separate reviewed algorithm
    rate_bps: int
    approval_reference: str


@dataclass(frozen=True)
class IssuanceLine:
    sku: str
    price_version: int
    base_amount: Decimal
    tax_amount: Decimal
    payable_amount: Decimal


@dataclass(frozen=True)
class InvoiceIssuancePlan:
    hotel_id: str
    agreement_version_id: str
    tax_policy_version_id: str
    quote_fingerprint: str
    period_start: str
    period_end: str
    currency: str
    lines: tuple[IssuanceLine, ...]
    net_amount: Decimal
    tax_amount: Decimal
    payable_amount: Decimal
    issuance_digest: str
    status: str = "PREPARED_NOT_ISSUED"


def plan_invoice_issuance(
    *,
    quote: CommercialQuote,
    agreement_version_id: str,
    contract_signed: bool,
    pms_link_verified: bool,
    tax_policy: ApprovedTaxRule,
) -> InvoiceIssuancePlan:
    """Calculate frozen line totals with explicit approved tax treatment.

    This is a PLAN, not a bank instruction, invoice or tax-compliance judgment.
    A separate database transaction must verify its contract/version and store
    the final tax-compliant invoice under restrictive permissions.
    """
    hotel = _id(quote.hotel_id)
    agreement = _id(agreement_version_id)
    policy_id = _id(tax_policy.version_id)
    if not contract_signed or not pms_link_verified:
        raise ValueError("Signed agreement and verified hotel link required")
    if quote.currency != "KGS" or quote.tax_status != "NOT_CALCULATED":
        raise ValueError("Unsupported or already taxed commercial quote")
    if not tax_policy.approval_reference.strip():
        raise ValueError("Tax policy must have explicit approval reference")
    if tax_policy.treatment not in {"EXEMPT", "ADDED"}:
        raise ValueError("Unreviewed tax calculation mode")
    if (
        not isinstance(tax_policy.rate_bps, int)
        or isinstance(tax_policy.rate_bps, bool)
        or not 0 <= tax_policy.rate_bps <= 10000
        or (tax_policy.treatment == "EXEMPT" and tax_policy.rate_bps != 0)
    ):
        raise ValueError("Invalid tax policy rate")
    if not quote.lines:
        raise ValueError("Invoice must contain at least one contracted line")

    result: list[IssuanceLine] = []
    for q in quote.lines:
        base = money(q.subtotal)
        if base < 0:
            raise ValueError("Credit notes need a separate reversal process")
        tax = (
            money(base * Decimal(tax_policy.rate_bps) / Decimal(10000))
            if tax_policy.treatment == "ADDED"
            else Decimal("0.00")
        )
        payable = money(base + tax)
        if payable > MAX_KGS:
            raise ValueError("Invoice line exceeds the supported KGS range")
        result.append(IssuanceLine(q.sku, q.price_version, base, tax, payable))
    net = money(sum((x.base_amount for x in result), Decimal("0")))
    tax = money(sum((x.tax_amount for x in result), Decimal("0")))
    total = money(sum((x.payable_amount for x in result), Decimal("0")))
    if net != quote.subtotal or total != net + tax or total > MAX_KGS:
        raise ValueError("Financial components do not balance")

    snapshot = {
        "hotel_id": hotel, "agreement_version_id": agreement,
        "tax_policy_version_id": policy_id,
        "tax_approval_reference": tax_policy.approval_reference,
        "tax_treatment": tax_policy.treatment,
        "tax_bps": tax_policy.rate_bps,
        "quote_fingerprint": quote.quote_fingerprint,
        "period": [quote.period_start.isoformat(), quote.period_end.isoformat()],
        "lines": [
            (line.sku, line.price_version,
             str(line.base_amount), str(line.tax_amount), str(line.payable_amount))
            for line in result
        ],
    }
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return InvoiceIssuancePlan(
        hotel_id=hotel, agreement_version_id=agreement,
        tax_policy_version_id=policy_id, quote_fingerprint=quote.quote_fingerprint,
        period_start=quote.period_start.isoformat(),
        period_end=quote.period_end.isoformat(), currency="KGS",
        lines=tuple(result), net_amount=net, tax_amount=tax,
        payable_amount=total, issuance_digest=digest,
    )


@dataclass(frozen=True)
class PaymentEvidence:
    """Already authenticated and reconciled bank event from trusted provider."""
    confirmed_payment_id: str
    invoice_id: str
    amount: Decimal
    currency: str
    provider_confirmed: bool


@dataclass(frozen=True)
class PaymentApplicationPlan:
    confirmed_payment_id: str
    invoice_id: str
    allocations: tuple[PaymentAllocation, ...]
    unapplied_credit: Decimal
    total_allocated: Decimal
    would_fully_pay: bool


def plan_payment_application(
    *,
    payment: PaymentEvidence,
    invoice_id: str,
    line_balances: tuple[InvoiceBalance, ...],
) -> PaymentApplicationPlan:
    """Deterministic plan. Does NOT authorize bank confirmation or DB insertion.

    DB must lock payment+invoice+line balances and execute idempotently; prior
    allocations/reversals must already be reflected in the supplied balances.
    """
    payment_id = _id(payment.confirmed_payment_id)
    invoice = _id(invoice_id)
    if _id(payment.invoice_id) != invoice or payment.currency != "KGS":
        raise ValueError("Foreign invoice or currency mismatch")
    if not payment.provider_confirmed:
        raise ValueError("Unconfirmed QR, receipt or notification is not cash")
    gross = money(payment.amount)
    if gross <= 0:
        raise ValueError("Confirmed payment amount must be positive")
    if not line_balances:
        raise ValueError("No invoice lines to allocate")
    allocation = allocate_confirmed_payment(gross, line_balances)
    allocated = money(sum((v.amount for v in allocation.allocations), Decimal("0")))
    if allocated + allocation.unallocated_credit != gross:
        raise ValueError("Payment allocation conservation failed")
    open_balance = money(sum((money(v.unpaid) for v in line_balances), Decimal("0")))
    return PaymentApplicationPlan(
        confirmed_payment_id=payment_id,
        invoice_id=invoice,
        allocations=allocation.allocations,
        unapplied_credit=allocation.unallocated_credit,
        total_allocated=allocated,
        would_fully_pay=(open_balance > 0 and allocated == open_balance),
    )
