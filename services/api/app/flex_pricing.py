"""MARINA FLEX monthly commercial quote engine (pure, no database or payments).

A quote is not an invoice or evidence of payment. Every input must first be
resolved from trusted versioned catalog/contract data in the FLEX control plane;
never accept client-supplied prices. Prices are KGS pre-tax placeholders until
tax rules and the customer's individual agreement are approved.
"""

from __future__ import annotations

import hashlib
import json
import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .flex_foundation import money

SKU_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
MAX_MONEY = Decimal("9999999999999999.99")


@dataclass(frozen=True)
class PriceItem:
    sku: str
    price_version: int
    monthly_price: Decimal
    quantity: int = 1
    enabled_from: date | None = None
    discount_bps: int = 0
    currency: str = "KGS"
    product_status: str = "AVAILABLE"
    pricing_source: str = "CATALOG"  # CATALOG, CONTRACT, LEGACY


@dataclass(frozen=True)
class QuoteLine:
    sku: str
    price_version: int
    quantity: int
    discount_bps: int
    enabled_from: date
    unit_monthly_price: Decimal
    active_days: int
    period_days: int
    gross: Decimal
    discount: Decimal
    subtotal: Decimal
    renewal_monthly: Decimal
    pricing_source: str


@dataclass(frozen=True)
class CommercialQuote:
    hotel_id: str
    period_start: date
    period_end: date
    currency: str
    lines: tuple[QuoteLine, ...]
    subtotal: Decimal
    renewal_monthly: Decimal
    quote_fingerprint: str
    tax_status: str = "NOT_CALCULATED"


def _verified_month(first: date) -> date:
    if type(first) is not date or first.day != 1:
        raise ValueError("Billing month must begin on the 1st")
    return date(first.year, first.month, monthrange(first.year, first.month)[1])


def _safe_money(value: Decimal) -> Decimal:
    rounded = money(value)
    if rounded < 0 or rounded > MAX_MONEY:
        raise ValueError("Amount outside allowed financial range")
    return rounded


def quote_month(
    *,
    hotel_id: str,
    period_start: date,
    catalog_items: tuple[PriceItem, ...],
) -> CommercialQuote:
    """Create an auditable price snapshot without side effects.

    - period is the hotel's contractual *calendar month* in its configured TZ
    - every SKU can be billed once; bundles must resolve to SKU entitlements first
    - price, discount and source are validated against a contract by the caller
    - taxes and provider fees require a separate final-invoice calculation
    """
    try:
        hotel_id = str(__import__("uuid").UUID(hotel_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid trusted hotel identifier") from None
    period_end = _verified_month(period_start)
    period_days = period_end.day
    if not isinstance(catalog_items, tuple) or not catalog_items:
        raise ValueError("At least one contracted product is required")

    seen: set[str] = set()
    lines: list[QuoteLine] = []
    for item in sorted(catalog_items, key=lambda row: row.sku):
        if not SKU_PATTERN.fullmatch(item.sku):
            raise ValueError("Invalid SKU")
        if item.sku in seen:
            raise ValueError("Duplicate billable SKU is forbidden")
        seen.add(item.sku)
        if item.product_status != "AVAILABLE":
            raise ValueError("Unreleased/retired product cannot be billed")
        if item.currency != "KGS":
            raise ValueError("Unsupported currency: explicit FX model required")
        if not isinstance(item.price_version, int) or isinstance(item.price_version, bool) or item.price_version < 1:
            raise ValueError("Invalid price version")
        if not isinstance(item.quantity, int) or isinstance(item.quantity, bool) or not (1 <= item.quantity <= 10000):
            raise ValueError("Invalid licensed quantity")
        if not isinstance(item.discount_bps, int) or isinstance(item.discount_bps, bool) or not (0 <= item.discount_bps <= 10000):
            raise ValueError("Invalid contractual discount")
        if item.pricing_source not in {"CATALOG", "CONTRACT", "LEGACY"}:
            raise ValueError("Unknown pricing source")
        unit = _safe_money(item.monthly_price)
        first_active = item.enabled_from or period_start
        if type(first_active) is not date:
            raise ValueError("Invalid activation date")
        days = max(0, (period_end - max(first_active, period_start)).days + 1)
        days = min(days, period_days)
        gross = _safe_money(unit * Decimal(item.quantity) * Decimal(days) / Decimal(period_days))
        discount = _safe_money(gross * Decimal(item.discount_bps) / Decimal(10000))
        full = _safe_money(unit * Decimal(item.quantity))
        full_discount = _safe_money(full * Decimal(item.discount_bps) / Decimal(10000))
        lines.append(QuoteLine(
            sku=item.sku, price_version=item.price_version,
            quantity=item.quantity, discount_bps=item.discount_bps,
            enabled_from=first_active, unit_monthly_price=unit,
            active_days=days, period_days=period_days,
            gross=gross, discount=discount, subtotal=gross-discount,
            renewal_monthly=full-full_discount,
            pricing_source=item.pricing_source,
        ))

    total = _safe_money(sum((item.subtotal for item in lines), Decimal("0")))
    renewal = _safe_money(sum((item.renewal_monthly for item in lines), Decimal("0")))
    stamp = {
        "hotel_id": hotel_id, "period_start": period_start.isoformat(),
        "currency": "KGS",
        "lines": [
            {
                "sku": line.sku, "version": line.price_version,
                "quantity": line.quantity, "unit_price": str(line.unit_monthly_price),
                "discount_bps": line.discount_bps,
                "enabled_from": line.enabled_from.isoformat(),
                "active_days": line.active_days, "period_days": line.period_days,
                "discount": str(line.discount), "subtotal": str(line.subtotal),
                "source": line.pricing_source,
            }
            for line in lines
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(stamp, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return CommercialQuote(
        hotel_id=hotel_id, period_start=period_start, period_end=period_end,
        currency="KGS", lines=tuple(lines), subtotal=total,
        renewal_monthly=renewal, quote_fingerprint=fingerprint,
    )
