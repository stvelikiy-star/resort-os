"""MARINA FLEX draft QR-provider boundaries (no network, keys or bank payment).

Initial provider candidate: Finik Web SDK, based on published merchant docs.
The resulting dictionary is NOT wire-ready: Amount is Decimal and must be
serialized with the provider-supported exact-number canonicalizer *before*
RSA signing. Nothing here signs a request, produces a live QR, or verifies a
webhook. Payment must NEVER be marked confirmed from this module alone.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

from .flex_foundation import money

VALID_LANG = frozenset({"ru", "ky", "en"})
PROVIDER_STATUS_SUCCESS = frozenset({"success", "succeeded"})
ACCOUNT_ID = re.compile(r"^[A-Za-z0-9_.:@-]{2,160}$")
NAME_RE = re.compile(r"^[A-Za-z0-9 _.-]{2,100}$")
PROVIDER_EVENT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")


def _verified_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid server-origin payment identifier") from None


def _trusted_https_url(url: str, *, expected_host: str) -> str:
    if not isinstance(url, str) or len(url) > 1024:
        raise ValueError("Expected preconfigured HTTPS URL")
    result = urlparse(url)
    if (
        result.scheme != "https" or result.hostname != expected_host
        or result.username or result.password or result.fragment
        or result.port not in (None, 443) or not result.path.startswith("/")
    ):
        raise ValueError("Untrusted merchant callback/redirect URL")
    if result.query:
        raise ValueError("Callback URLs must not embed free-form query parameters")
    return url


@dataclass(frozen=True)
class FinikMerchantConfig:
    """Trusted server config, never supplied by a hotel or request body."""
    account_id: str
    display_name: str
    callback_url: str
    return_url: str
    merchant_hostname: str


@dataclass(frozen=True)
class QrIntentDraft:
    invoice_id: str
    payment_intent_id: str
    amount_kg: Decimal
    provider: str
    request_body: dict
    payment_page_url: None = None
    confirmed: bool = False


def build_finik_qr_intent(
    *,
    invoice_id: str,
    payment_intent_id: str,
    verified_issued_invoice: bool,
    outstanding_kg: Decimal,
    config: FinikMerchantConfig,
    language: str = "ru",
) -> QrIntentDraft:
    """Return a provider-specific draft, without issuing a signed request.

    Backend must resolve the issued invoice, exact outstanding and merchant
    config in one trusted transaction. No payment result is implied.
    """
    invoice = _verified_uuid(invoice_id)
    payment_id = _verified_uuid(payment_intent_id)
    if not verified_issued_invoice:
        raise ValueError("Only finalized commercial invoices may request QR")
    amount = money(outstanding_kg)
    if amount <= 0:
        raise ValueError("QR must not be created for zero/credit invoice")
    if language not in VALID_LANG:
        raise ValueError("Unsupported QR interface language")
    if not ACCOUNT_ID.fullmatch(config.account_id):
        raise ValueError("Invalid merchant account ID")
    if not NAME_RE.fullmatch(config.display_name):
        raise ValueError("Invalid merchant display name")
    host = config.merchant_hostname
    if not host or host.lower()!=host or "/" in host or ":" in host:
        raise ValueError("Invalid trusted merchant hostname")
    callback = _trusted_https_url(config.callback_url, expected_host=host)
    redirect = _trusted_https_url(config.return_url, expected_host=host)
    body = {
        "Amount": amount,
        "CardType": "FINIK_QR",
        "PaymentId": payment_id,
        "RedirectUrl": redirect,
        "Lang": language,
        "Data": {
            "accountId": config.account_id,
            "name_en": config.display_name,
            "webhookUrl": callback,
            "description": "MARINA FLEX commercial subscription",
        },
    }
    return QrIntentDraft(
        invoice_id=invoice, payment_intent_id=payment_id,
        provider="FINIK_WEB_SDK", amount_kg=amount, request_body=body,
    )


@dataclass(frozen=True)
class UnverifiedFinikNotification:
    """Raw webhook claims WITHOUT signature proof; never confirmed revenue."""
    provider_transaction_id: str
    requested_payment_id: str
    claimed_status: str
    claimed_amount: Decimal
    verification_state: str = "UNTRUSTED"


def parse_unverified_finik_webhook(payload: dict) -> UnverifiedFinikNotification:
    """Schema check ONLY. No signed authentication, no cash accounting.

    Exact signature canonicalization must be independently verified against
    official Finik Web SDK before wiring any webhook to commercial accounting.
    """
    if not isinstance(payload, dict):
        raise ValueError("Finik webhook must be an object")
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        raise ValueError("Missing webhook fields")
    status = payload.get("status")
    transaction_id = payload.get("transactionId")
    if not isinstance(transaction_id, str) or not PROVIDER_EVENT_RE.fullmatch(transaction_id):
        raise ValueError("Unusable provider transaction id")
    if not isinstance(status, str):
        raise ValueError("Unusable transaction status")
    raw_amount = payload.get("amount")
    if isinstance(raw_amount, bool) or isinstance(raw_amount, float):
        raise ValueError("Do not trust imprecise floating-point webhook amounts")
    amount = money(raw_amount)
    if amount <= 0:
        raise ValueError("Unusable webhook amount")
    return UnverifiedFinikNotification(
        provider_transaction_id=transaction_id,
        requested_payment_id=_verified_uuid(fields.get("paymentId")),
        claimed_status=status.lower(),
        claimed_amount=amount,
    )
