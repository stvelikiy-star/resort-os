#!/usr/bin/env python3
"""Fail-closed truth guard for the MARINA SMART multi-tenant candidate."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release" / "marina-smart-current-candidate.json"
STATE_PATH = ROOT / "knowledge" / "MARINA_SMART_CURRENT_STATE_20261008.md"

EXPECTED_HEAD = "64a20f08a91ddebc4c2522d3e640e131dce179d4"
EXPECTED_BRANCH = "marina-smart/multi-tenant-foundation-20261008"
EXPECTED_PR = 234


def main() -> int:
    errors: list[str] = []
    if not MANIFEST_PATH.exists():
        errors.append("missing MARINA SMART candidate manifest")
        manifest = {}
    else:
        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"cannot parse candidate manifest: {exc}")
            manifest = {}

    required = {
        "product": "MARINA SMART",
        "status": "INTERNAL_CANDIDATE_STAGING_REQUIRED",
        "candidate_commit": EXPECTED_HEAD,
        "source_branch": EXPECTED_BRANCH,
        "pull_request": EXPECTED_PR,
        "migration_count": 31,
        "tenant_model": "Tenant/Property",
        "tenant_context_enabled": False,
        "staging_gate": "manual_read_only",
        "external_staging_verified": False,
        "cross_tenant_e2e_verified": False,
        "backup_restore_target_verified": False,
        "production_cutover_authorized": False,
        "payment_operations_enabled": False,
        "nfc_wallet_enabled": False,
    }
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for key, value in required.items():
        if manifest.get(key) != value:
            errors.append(f"{key} must be {value!r}")

    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("candidate_commit", ""))):
        errors.append("candidate_commit must be an exact 40-character Git SHA")

    if not STATE_PATH.exists():
        errors.append("missing MARINA SMART current-state document")
    else:
        state = STATE_PATH.read_text(encoding="utf-8")
        for marker in (
            "PR: #234",
            "CI: 41/41 SUCCESS",
            "Tenant/Property",
            "tenant_id",
            "property_id",
            "cross-tenant login/read/write E2E",
            "production cutover authorization",
            "The existing roles, navigation and approved compact chessboard remain unchanged.",
        ):
            if marker not in state:
                errors.append(f"current-state marker missing: {marker}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: MARINA CANDIDATE TRUTH RED")
        return 1

    print("FACT: product=MARINA SMART")
    print(f"FACT: candidate_commit={EXPECTED_HEAD}")
    print("FACT: candidate_migrations=31")
    print("FACT: tenant_model=Tenant/Property")
    print("FACT: tenant_context_enabled=false")
    print("FACT: external_staging_verified=false")
    print("FACT: cross_tenant_e2e_verified=false")
    print("FACT: production_cutover_authorized=false")
    print("RESULT: MARINA CANDIDATE TRUTH GREEN; STAGING REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
