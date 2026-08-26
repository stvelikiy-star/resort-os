#!/usr/bin/env python3
from fastapi import HTTPException

from app.payment_idempotency import normalize_optional_text, normalize_required_text


assert normalize_required_text("  CASH  ") == "CASH"
assert normalize_optional_text("  REF-001  ") == "REF-001"
assert normalize_optional_text("   ") is None
assert normalize_optional_text(None) is None

try:
    normalize_required_text("   ")
except HTTPException as exc:
    assert exc.status_code == 422
    assert exc.detail["code"] == "INVALID_PAYMENT_METHOD"
else:
    raise AssertionError("blank normalized payment method must be rejected")

print("PASS: payment idempotency normalization contract")
