"""Signed QA payment evidence: NEVER a Finik or bank webhook verifier.

We cannot claim bank confirmation until an official provider merchant account,
canonical signer and independently verified webhook are available. This module
only proves the trust boundary with ephemeral keys in disposable CI.

No live endpoints import this module. Production cannot enable its QA verifier.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from .flex_foundation import money

PROVIDER = "FLEX_QA_SIMULATOR"
EVENT_TYPE = "payment.succeeded"
MAX_AGE_MS = 5 * 60 * 1000
MAX_BODY_BYTES = 8192
TRANSACTION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,150}$")
EXACT_KEYS = frozenset({
    "provider", "event_type", "hotel_id", "invoice_id",
    "payment_intent_id", "provider_payment_id", "amount",
    "currency", "issued_at_ms",
})


@dataclass(frozen=True)
class VerifiedQaPayment:
    """Internal result after a CI-only public-key check, not bank settlement."""
    provider: str
    invoice_id: str
    hotel_id: str
    payment_intent_id: str
    provider_payment_id: str
    amount: Decimal
    currency: str
    payload_sha256: str


def _valid_uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid UUID field")
    try:
        normalized = str(uuid.UUID(value))
    except ValueError:
        raise ValueError("Invalid UUID field") from None
    if value != normalized:
        raise ValueError("Noncanonical UUID")
    return normalized


def canonical_qa_envelope(event: dict) -> bytes:
    """CI-private deterministic envelope, intentionally NOT Finik canonicalization."""
    if not isinstance(event, dict) or frozenset(event) != EXACT_KEYS:
        raise ValueError("Malformed QA event envelope")
    result = json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    raw = result.encode("utf-8")
    if len(raw) > MAX_BODY_BYTES:
        raise ValueError("Payload oversized")
    return raw


def verify_qa_payment(
    *,
    event: dict,
    signature_b64: str,
    sandbox_public_key_pem: str,
    now_ms: int | None = None,
) -> VerifiedQaPayment:
    """Require QA guard and strong signature, then validate exact invoice identity.

    The QA process must additionally correlate verified identity and amount with
    a trusted, already-recorded payment intent in its isolated PostgreSQL txn.
    """
    if os.environ.get("FLEX_SETTLEMENT_MODE") != "CI_DISPOSABLE_ONLY":
        raise RuntimeError("QA payment simulator disabled outside disposable CI")
    raw = canonical_qa_envelope(event)
    if event["provider"] != PROVIDER or event["event_type"] != EVENT_TYPE:
        raise ValueError("Unsupported simulator event")
    hotel = _valid_uuid(event["hotel_id"])
    invoice = _valid_uuid(event["invoice_id"])
    intent = _valid_uuid(event["payment_intent_id"])
    transaction = event["provider_payment_id"]
    if not isinstance(transaction, str) or not TRANSACTION_PATTERN.fullmatch(transaction):
        raise ValueError("Invalid transaction ID")
    if event["currency"] != "KGS" or not isinstance(event["amount"], str):
        raise ValueError("Unsupported currency or amount")
    amount = money(event["amount"])
    if amount <= 0:
        raise ValueError("Payment must be positive")
    timestamp = event["issued_at_ms"]
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise ValueError("Invalid provider event timestamp")
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if abs(now - timestamp) > MAX_AGE_MS:
        raise ValueError("Stale or future QA event")
    if not isinstance(signature_b64, str) or len(signature_b64) > 256:
        raise ValueError("Missing signature")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
        if len(signature) != 64:
            raise ValueError("Invalid Ed25519 signature length")
        key = load_pem_public_key(sandbox_public_key_pem.encode("utf-8"))
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("QA public signing key must be Ed25519")
        key.verify(signature, raw)
    except (ValueError, binascii.Error, InvalidSignature, TypeError):
        raise ValueError("Invalid signed QA payment") from None
    return VerifiedQaPayment(
        provider=PROVIDER, invoice_id=invoice, hotel_id=hotel,
        payment_intent_id=intent, provider_payment_id=transaction,
        amount=amount, currency="KGS",
        payload_sha256=hashlib.sha256(raw).hexdigest(),
    )
