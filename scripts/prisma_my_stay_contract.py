#!/usr/bin/env python3
"""Fail-closed contract between the canonical Prisma schema and MY STAY SQL migrations.

The MY STAY/public-access tables were introduced by reviewed forward SQL migrations.
This guard prevents `prisma validate` from giving false confidence when the canonical
schema omits those tables or the new RBAC roles. Partial unique indexes remain SQL
migration truth because their WHERE predicates cannot be represented safely as a
plain Prisma @@unique without changing semantics.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "packages/database/prisma/schema.prisma"

REQUIRED_ROLES = {
    "OWNER",
    "MANAGER",
    "ADMIN",
    "RECEPTION",
    "DINING",
    "MAID",
    "TECHNICIAN",
    "BEACH_PARTNER",
}

REQUIRED_MODELS = {
    "GuestAccessCredential": "guest_access_credentials",
    "GuestSession": "guest_sessions",
    "ReservationMealPlan": "reservation_meal_plans",
    "DiningMenuItem": "dining_menu_items",
    "DiningOrder": "dining_orders",
    "DiningOrderItem": "dining_order_items",
    "ReservationCharge": "reservation_charges",
    "SmartAccessPoint": "smart_access_points",
    "SmartAccessGrant": "smart_access_grants",
    "PublicAccessPaymentIntent": "public_access_payment_intents",
}

REQUIRED_MARKERS = (
    "guestAccessCredential GuestAccessCredential?",
    "mealPlans             ReservationMealPlan[]",
    "diningOrders          DiningOrder[]",
    "charges               ReservationCharge[]",
    "smartAccessGrants     SmartAccessGrant[]",
    "createdDiningMenuItems DiningMenuItem[]",
    'map: "reservation_charges_reservation_status_idx"',
    'map: "public_access_payment_intents_point_status_idx"',
)


def block(text: str, kind: str, name: str) -> str:
    match = re.search(rf"\b{kind}\s+{re.escape(name)}\s*\{{(?P<body>.*?)\n\}}", text, re.S)
    if not match:
        raise AssertionError(f"Missing {kind} {name}")
    return match.group("body")


def main() -> int:
    text = SCHEMA.read_text(encoding="utf-8")

    role_body = block(text, "enum", "StaffRole")
    roles = {line.strip() for line in role_body.splitlines() if line.strip() and not line.strip().startswith("//")}
    missing_roles = REQUIRED_ROLES - roles
    assert not missing_roles, f"Prisma StaffRole missing: {sorted(missing_roles)}"

    for model_name, table_name in REQUIRED_MODELS.items():
        body = block(text, "model", model_name)
        assert f'@@map("{table_name}")' in body, f"{model_name} does not map to {table_name}"

    for marker in REQUIRED_MARKERS:
        assert marker in text, f"Missing Prisma MY STAY relation/index marker: {marker}"

    # These are partial unique indexes in reviewed SQL migrations. Modeling them as
    # unconditional Prisma uniques would silently reject valid NULL-provider/source rows.
    assert "@@unique([sourceType, sourceId])" not in text
    assert "@@unique([provider, externalRef])" not in block(text, "model", "PublicAccessPaymentIntent")

    migration5 = (ROOT / "packages/database/prisma/migrations/5_my_stay/migration.sql").read_text(encoding="utf-8")
    migration6 = (ROOT / "packages/database/prisma/migrations/6_public_access/migration.sql").read_text(encoding="utf-8")
    migration7 = (ROOT / "packages/database/prisma/migrations/7_in_stay_task_context/migration.sql").read_text(encoding="utf-8")
    migration8 = (ROOT / "packages/database/prisma/migrations/8_public_access_unlock_claim/migration.sql").read_text(encoding="utf-8")
    assert "reservation_charges_source_unique_idx" in migration5
    assert "public_access_payment_intents_provider_ref_unique_idx" in migration6
    assert "HOUSEKEEPING" in migration7 and "MAINTENANCE" in migration7
    assert "UNLOCKING" in migration8
    assert "public_access_payment_intents_status_check" in migration8

    print("PRISMA_MY_STAY_CONTRACT=PASS")
    print(f"roles={len(REQUIRED_ROLES)} models={len(REQUIRED_MODELS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
