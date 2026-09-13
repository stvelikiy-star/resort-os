#!/usr/bin/env python3
"""Fail closed if the Three Crowns management Marketing contour regresses."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"required file missing: {path}")
    return target.read_text(encoding="utf-8")


CHECKS: list[tuple[str, str, str]] = [
    # Admin composition and navigation
    ("apps/admin/components/AdminShell.tsx", 'import MarketingBoard from "./MarketingBoard"', "MarketingBoard imported"),
    ("apps/admin/components/AdminShell.tsx", '"MARKETING"', "MARKETING tab registered"),
    ("apps/admin/components/AdminShell.tsx", '>Маркетинг</button>', "Marketing navigation present"),
    ("apps/admin/components/AdminShell.tsx", 'tab === "MARKETING" && isManager && <MarketingBoard />', "Marketing workspace manager-only mount"),

    # Admin Marketing reads real Core data and remains consent-gated
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/reports/overview", "Marketing reports are Core-backed"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/booking/requests?limit=200", "Marketing leads are real booking requests"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/guest-offers", "Marketing campaigns use guest offers"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/marketing/summary", "Marketing consent summary endpoint"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/marketing/audience?channel=WHATSAPP&limit=1000", "WhatsApp audience is consent-filtered"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/marketing/audience?channel=EMAIL&limit=1000", "Email audience is consent-filtered"),
    ("apps/admin/components/MarketingBoard.tsx", "/core/api/v1/admin/marketing/requests/${item.id}/touchpoints", "manager touchpoints are recorded"),
    ("apps/admin/components/MarketingBoard.tsx", "safeWhatsappIds.has(item.id)", "WhatsApp outreach checks safe audience"),
    ("apps/admin/components/MarketingBoard.tsx", "safeEmailIds.has(item.id)", "Email outreach checks safe audience"),
    ("apps/admin/components/MarketingBoard.tsx", "Нет consent", "UI exposes missing-consent boundary"),

    # Core authority and RBAC
    ("services/api/app/app_entry.py", "app.include_router(marketing_router)", "admin marketing router composed"),
    ("services/api/app/app_entry.py", "app.include_router(marketing_integration_router)", "provider event router composed"),
    ("services/api/app/app_entry.py", "app.include_router(marketing_automation_router)", "automation marketing router composed"),
    ("services/api/app/marketing.py", 'router = APIRouter(prefix="/api/v1/admin/marketing"', "admin marketing API prefix"),
    ("services/api/app/marketing.py", 'manager_access = require_roles("OWNER", "MANAGER")', "Marketing RBAC is manager-only"),
    ("services/api/app/marketing.py", '@router.get("/audience")', "consent-safe audience endpoint"),
    ("services/api/app/marketing.py", 'WHERE l.status=\'OPTED_IN\'', "audience excludes non-opted-in contacts"),
    ("services/api/app/marketing.py", '@router.post("/requests/{request_id}/consent"', "explicit consent recording endpoint"),
    ("services/api/app/marketing.py", '@router.post("/requests/{request_id}/touchpoints"', "touchpoint recording endpoint"),
    ("services/api/app/marketing.py", '@integration_router.post("/provider-events"', "provider delivery/unsubscribe endpoint"),
    ("services/api/app/marketing.py", "UNSUBSCRIBED", "unsubscribe fail-closed lifecycle"),
]

FORBIDDEN: list[tuple[str, str, str]] = [
    ("apps/admin/components/MarketingBoard.tsx", "Загрузить демо", "Marketing must not expose demo bootstrap"),
    ("apps/admin/components/MarketingBoard.tsx", "mock", "Marketing must not use mock runtime data"),
]


def main() -> int:
    passed = 0
    for path, needle, label in CHECKS:
        if needle not in read(path):
            raise AssertionError(f"FAIL [{label}]: {path} missing {needle!r}")
        passed += 1
    for path, needle, label in FORBIDDEN:
        if needle.lower() in read(path).lower():
            raise AssertionError(f"FAIL [{label}]: forbidden marker {needle!r} in {path}")
        passed += 1
    print(f"MANAGEMENT_MARKETING_ACCEPTANCE_PASS checks={passed}")
    print("BOUNDARY: Marketing reads operational truth from Resort Core and outreach remains consent-gated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"MANAGEMENT_MARKETING_ACCEPTANCE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(1)
