#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.production.example"
COMPOSE = ROOT / "compose.production.yaml"
APP_ENTRY = ROOT / "services/api/app/app_entry.py"
CAPABILITIES = ROOT / "services/api/app/runtime_capabilities.py"
FOLIO = ROOT / "apps/admin/components/ReservationFolioPanel.tsx"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    env_text = ENV_FILE.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    entry = APP_ENTRY.read_text(encoding="utf-8")
    capabilities = CAPABILITIES.read_text(encoding="utf-8")
    folio = FOLIO.read_text(encoding="utf-8")
    env = parse_env(env_text)

    require(env.get("LAUNCH_PROFILE") == "FULL_NO_PAYMENTS", "production launch profile must be FULL_NO_PAYMENTS")

    for key in (
        "ENABLE_PUBLIC_SITE",
        "ENABLE_PMS",
        "ENABLE_CRM",
        "ENABLE_STAFF",
        "ENABLE_GUEST_OS",
        "ENABLE_KITCHEN",
        "ENABLE_AUTOMATION",
        "ENABLE_AI_SALES",
    ):
        require(env.get(key) == "true", f"{key} must stay enabled in the current launch profile")

    for key in ("ENABLE_PAYMENT_OPERATIONS", "ENABLE_SERVICE_POINT_QR", "ENABLE_MKASSA"):
        require(env.get(key) == "false", f"{key} must stay disabled until explicit owner approval")
        require(key in compose, f"compose must pass {key} to Resort Core")
        require(key in capabilities, f"runtime capability surface must expose {key}")

    require('if PAYMENT_OPERATIONS_ENABLED:\n    app.include_router(reservation_payments_router)' in entry,
            "reservation payment router must be composed only behind ENABLE_PAYMENT_OPERATIONS")
    require('if SERVICE_POINT_QR_ENABLED:\n    app.include_router(service_point_payments_public_router)' in entry,
            "service-point public payment routes must be gated")
    require('if SERVICE_POINT_QR_ENABLED and MKASSA_ENABLED:\n    app.include_router(mkassa_payment_bridge_router)' in entry,
            "MKassa bridge must require both QR and MKassa flags")
    require('app.include_router(runtime_capabilities_router)' in entry,
            "runtime capabilities endpoint must be active")

    # Operational contours requested by the owner must remain composed while payments are off.
    for router_name in (
        "owner_corrections_router",
        "pms_chessboard_router",
        "pms_reservation_create_router",
        "guest_os_admin_router",
        "guest_services_router",
        "housekeeping_schedule_router",
        "operations_router",
        "kitchen_admin_router",
        "staff_voice_router",
        "automation_router",
        "ai_sales_router",
        "realtime_router",
        "manager_dashboard_router",
    ):
        require(f"app.include_router({router_name})" in entry, f"required operational router missing: {router_name}")

    require("/core/api/v1/runtime/capabilities" in folio,
            "Admin folio must read runtime capabilities before exposing payment mutation controls")
    require("paymentOperationsEnabled" in folio,
            "Admin folio must gate payment UI by runtime capability")
    require("Оплаты временно отключены" in folio,
            "Admin must communicate the no-payment launch state clearly")

    # NFC stays dormant regardless of this profile.
    require("app.include_router(nfc" not in entry.lower(), "NFC router must remain dormant")

    print("NO_PAYMENT_LAUNCH_PROFILE=PASS")
    print("Operational contours: ON")
    print("Payment mutations / Service Point QR / MKassa / NFC: OFF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
