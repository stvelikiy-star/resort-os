#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.payment_idempotency import (
    normalize_optional_text,
    normalize_payment_timestamp,
    normalize_required_text,
)


assert normalize_required_text("  CASH  ") == "CASH"
assert normalize_optional_text("  REF-001  ") == "REF-001"
assert normalize_optional_text("   ") is None
assert normalize_optional_text(None) is None

naive = datetime(2026, 9, 5, 12, 30, 1, 123456)
assert normalize_payment_timestamp(naive) == datetime(2026, 9, 5, 12, 30, 1, 123000, tzinfo=timezone.utc)
plus_six = datetime(2026, 9, 5, 18, 30, 1, 123999, tzinfo=timezone(timedelta(hours=6)))
assert normalize_payment_timestamp(plus_six) == datetime(2026, 9, 5, 12, 30, 1, 123000, tzinfo=timezone.utc)
assert normalize_payment_timestamp(None) is None

try:
    normalize_required_text("   ")
except HTTPException as exc:
    assert exc.status_code == 422
    assert exc.detail["code"] == "INVALID_PAYMENT_METHOD"
else:
    raise AssertionError("blank normalized payment method must be rejected")

print("PASS: payment idempotency normalization contract")