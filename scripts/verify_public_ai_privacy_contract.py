#!/usr/bin/env python3
"""Static privacy and truth contract for the public MARINA AI provider call."""

from pathlib import Path

SOURCE = Path("services/api/app/public_ai_admin.py").read_text(encoding="utf-8")

REQUIRED = {
    '"store": False': "public provider response storage is disabled",
    '"availability_from_core": True': "availability must come from Core",
    '"creates_confirmed_reservation": False': "public AI cannot confirm reservations",
    '"collects_payment": False': "public AI cannot collect payment",
    '"can_confirm_reservation": False': "chat response cannot confirm reservations",
    '"manager_handles_prepayment": True': "prepayment remains manager-owned",
    "Do not request passport, bank-card or other sensitive data": "sensitive-data request rule is present",
    "status_code=502": "provider failures fail closed",
}

for needle, label in REQUIRED.items():
    if needle not in SOURCE:
        raise SystemExit(f"FAIL: missing public AI contract: {label} ({needle})")

print("MARINA_PUBLIC_AI_PRIVACY_CONTRACT: PASS")
