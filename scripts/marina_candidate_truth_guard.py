#!/usr/bin/env python3
"""Validate the current MARINA candidate identity and unverified rollout boundary."""
from __future__ import annotations

import json
import re
from pathlib import Path

from release_contract import EXPECTED_MIGRATIONS

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release" / "marina-smart-current-candidate.json"
STATE_PATH = ROOT / "knowledge" / "MARINA_SMART_CURRENT_STATE_20261008.md"
EXPECTED_BRANCH = "fix/marina-staging-preflight-20261020"
EXPECTED_PR = 244


def main() -> int:
    errors: list[str] = []
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be a JSON object")
    except (OSError, ValueError) as exc:
        errors.append(f"cannot read candidate manifest: {exc}")
        manifest = {}

    required = {
        "schema_version": 1,
        "product": "MARINA SMART",
        "status": "INTERNAL_CANDIDATE_STAGING_REQUIRED",
        "source_branch": EXPECTED_BRANCH,
        "pull_request": EXPECTED_PR,
        "migration_count": len(EXPECTED_MIGRATIONS),
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
    for key, value in required.items():
        actual = manifest.get(key)
        if type(actual) is not type(value) or actual != value:
            errors.append(f"{key} must be {value!r}")

    # This pins the reviewed application revision, not this metadata commit.
    # CI status must be obtained from GitHub for the actual head, never inferred here.
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("candidate_commit", ""))):
        errors.append("candidate_commit must be an exact 40-character Git SHA")

    migrations = ROOT / "packages" / "database" / "prisma" / "migrations"
    actual_migrations = tuple(sorted(p.parent.name for p in migrations.glob("*/migration.sql")))
    if len(actual_migrations) != len(EXPECTED_MIGRATIONS) or set(actual_migrations) != set(EXPECTED_MIGRATIONS):
        errors.append("committed migration files differ from the reviewed release contract")

    try:
        state = STATE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read current-state document: {exc}")
    else:
        for marker in (
            f"PR: #{EXPECTED_PR}",
            f"Branch: {EXPECTED_BRANCH}",
            f"Application baseline: {manifest.get('candidate_commit', '')}",
            f"Migration ledger: {len(EXPECTED_MIGRATIONS)} migrations",
            "Tenant/Property",
            "tenant_id",
            "property_id",
            "PROPERTY_PINNED_RUNTIMES",
            "external_staging_verified=false",
            "backup_restore_target_verified=false",
            "production_cutover_authorized=false",
            "The existing roles, navigation and approved compact chessboard remain unchanged.",
        ):
            if marker not in state:
                errors.append(f"current-state marker missing: {marker}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: MARINA CANDIDATE TRUTH RED")
        return 1
    print(f"FACT: product=MARINA SMART branch={EXPECTED_BRANCH} PR={EXPECTED_PR}")
    print(f"FACT: candidate_commit={manifest['candidate_commit']}")
    print(f"FACT: candidate_migrations={len(EXPECTED_MIGRATIONS)}")
    print("FACT: external staging, target restore and production authorization remain false")
    print("RESULT: MARINA CANDIDATE TRUTH GREEN; STAGING REQUIRED; CI STATUS NOT ASSERTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
