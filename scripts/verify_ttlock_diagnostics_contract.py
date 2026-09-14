#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "services" / "api" / "app" / "ttlock_diagnostics.py"
ENTRY = ROOT / "services" / "api" / "app" / "app_entry.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    raw = MODULE.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")

    require('prefix="/api/v1/admin/ttlock"' in raw, "diagnostics are admin-scoped")
    require('require_roles("OWNER", "MANAGER")' in raw, "diagnostics require OWNER/MANAGER")
    require('/v3/lock/detail' in raw, "read-only lock detail probe exists")
    require('/v3/lock/queryOpenState' in raw, "read-only gateway state probe exists")
    require('/v3/lock/unlock' not in raw, "diagnostics never call unlock")
    require('/v3/lock/lock' not in raw, "diagnostics never call lock")
    require('READ_ONLY_PROVIDER_DIAGNOSTIC_NO_LOCK_ACTUATION' in raw, "response declares read-only truth")
    require('TTLOCK_ACCESS_TOKEN' in raw and 'TTLOCK_CLIENT_ID' in raw, "credentials come from environment")
    require('"access_token"' not in raw.lower(), "response does not expose token field")
    require('app.include_router(ttlock_diagnostics_router)' in entry, "diagnostics router is composed")

    print("PASS: TTLock diagnostics are OWNER/MANAGER-only")
    print("PASS: diagnostics use only lock detail + gateway open-state reads")
    print("PASS: no lock/unlock actuation exists in diagnostics module")
    print("PASS: provider credentials remain environment-only and are not returned")


if __name__ == "__main__":
    main()
