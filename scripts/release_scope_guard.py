#!/usr/bin/env python3
"""Static release-scope guard for the active Three Crowns Resort Core app.

This does not start the server or connect to PostgreSQL. It imports the composed
FastAPI application and checks the route contract that must be true for the
current owner-approved V1 scope.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.app_entry import app  # noqa: E402


REQUIRED_PATHS = {
    "/health",
    "/health/live",
    "/health/ready",
    "/api/v1/booking/check-availability",
    "/api/v1/booking/requests",
    "/api/v1/admin/booking/requests",
    "/api/v1/admin/booking/reservations",
    "/api/v1/admin/finance/summary",
    "/api/v1/admin/reception/reservations",
    "/api/v1/pms/grid",
    "/api/v1/admin/dashboard",
}

FORBIDDEN_EXACT_PATHS = {
    "/api/v1/beach/charge",
}

FORBIDDEN_PATH_FRAGMENTS = (
    "/nfc",
    "/beach/charge",
)

_PREPAYMENT_KEY = re.compile(r"^\s*PREPAYMENT_PERCENT\s*(?:=|:)")


def exposes_active_prepayment_percent(text: str) -> bool:
    """Detect an uncommented PREPAYMENT_PERCENT key in dotenv or YAML syntax."""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if _PREPAYMENT_KEY.match(line):
            return True
    return False


def run_self_test() -> int:
    cases = {
        "PREPAYMENT_PERCENT=30\n": True,
        "  PREPAYMENT_PERCENT = 30\n": True,
        "      PREPAYMENT_PERCENT: ${PREPAYMENT_PERCENT}\n": True,
        "# PREPAYMENT_PERCENT=30\n": False,
        "   # PREPAYMENT_PERCENT: 30\n": False,
        "OTHER_PREPAYMENT_PERCENT=30\n": False,
        "NOTE: PREPAYMENT_PERCENT\n": False,
        "\n": False,
    }
    for text, expected in cases.items():
        actual = exposes_active_prepayment_percent(text)
        if actual != expected:
            print(f"FAIL: PREPAYMENT_PERCENT parser mismatch for {text!r}: {actual} != {expected}")
            return 1
    print("PASS: PREPAYMENT_PERCENT guard handles dotenv, YAML, comments and false positives")
    return 0


def main() -> int:
    paths = {route.path for route in app.routes if getattr(route, "path", None)}

    errors: list[str] = []
    missing = sorted(REQUIRED_PATHS - paths)
    if missing:
        errors.append("missing required active routes: " + ", ".join(missing))

    forbidden = sorted(path for path in paths if path in FORBIDDEN_EXACT_PATHS)
    forbidden += sorted(
        path for path in paths
        if any(fragment in path.lower() for fragment in FORBIDDEN_PATH_FRAGMENTS)
        and path not in forbidden
    )
    if forbidden:
        errors.append("deferred NFC/beach routes are composed: " + ", ".join(sorted(set(forbidden))))

    booking_admin = (API_ROOT / "app" / "booking_admin.py").read_text(encoding="utf-8")
    if "PREPAYMENT_PERCENT" in booking_admin:
        errors.append("booking_admin.py still contains PREPAYMENT_PERCENT")

    active_env_files = [ROOT / ".env.example", ROOT / ".env.production.example", ROOT / "compose.production.yaml"]
    for path in active_env_files:
        if path.exists() and exposes_active_prepayment_percent(path.read_text(encoding="utf-8")):
            errors.append(f"{path.relative_to(ROOT)} still exposes PREPAYMENT_PERCENT")

    print("Three Crowns active release scope guard")
    print(f"FACT: composed_routes={len(paths)}")
    print(f"FACT: app_version={app.version}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: NOT READY")
        return 1

    print("PASS: active Core route scope matches current V1 owner decisions")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        raise SystemExit(run_self_test())
    raise SystemExit(main())
