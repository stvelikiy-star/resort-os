from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def normalize_required_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_PAYMENT_METHOD",
                "message": "Payment method must contain a non-whitespace value.",
            },
        )
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


async def lock_payment_identity(conn: Any, idempotency_key: str, external_ref: str | None) -> None:
    """Serialize globally unique payment identities inside the current DB transaction."""
    tokens = [f"payment:idempotency:{idempotency_key}"]
    if external_ref:
        tokens.append(f"payment:external-ref:{external_ref}")
    for token in sorted(tokens):
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1::text, 0))",
            token,
        )


def ensure_same_payment_payload(
    existing: Any,
    *,
    amount_kgs: int,
    method: str,
    external_ref: str | None,
    note: str | None = None,
    compare_note: bool = False,
) -> None:
    mismatches: list[str] = []
    if int(existing["amountKgs"]) != amount_kgs:
        mismatches.append("amount_kgs")
    if normalize_required_text(existing["method"]) != method:
        mismatches.append("method")
    if normalize_optional_text(existing["externalRef"]) != external_ref:
        mismatches.append("external_ref")
    if compare_note:
        stored_note = normalize_optional_text(existing["note"])
        if stored_note != note:
            mismatches.append("note")

    if mismatches:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IDEMPOTENCY_PAYLOAD_MISMATCH",
                "message": "This idempotency key was already used with a different payment payload.",
                "mismatched_fields": mismatches,
                "payment_id": str(existing["id"]),
            },
        )
