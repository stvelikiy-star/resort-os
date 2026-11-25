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

# Legacy schema is compatible, complete migration is authoritative, and
# half-installed schemas must not quietly erase refund facts.
import asyncio
from app.payment_refund_read_model import refund_compatible_sql

class SchemaState:
    def __init__(self,balances,events):
        self.state={"balances":balances,"events":events}
    async def fetchrow(self,query):
        return self.state

async def verify_refund_schema():
    query="SELECT b.* FROM owner_reservation_payment_balances b"
    assert await refund_compatible_sql(SchemaState(True,True),query)==query
    legacy=await refund_compatible_sql(SchemaState(False,False),query)
    assert 'FROM payments p JOIN reservations r' in legacy and '"remainingReceivedKgs"' in legacy
    assert "owner_reservation_payment_balances" not in legacy
    empty=await refund_compatible_sql(SchemaState(False,False),'SELECT * FROM owner_partial_refund_events')
    assert "WHERE false" in empty and '"refundedAt"' in empty
    for a,b in [(True,False),(False,True)]:
        try:
            await refund_compatible_sql(SchemaState(a,b),query)
        except HTTPException as exc:
            assert exc.status_code==503 and exc.detail["code"]=="PARTIAL_REFUND_SCHEMA_INCOMPLETE"
        else:
            raise AssertionError("Incomplete schema must fail closed")

asyncio.run(verify_refund_schema())
print("PASS: partial refund schema compatibility")
