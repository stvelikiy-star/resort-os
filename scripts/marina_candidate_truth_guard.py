#!/usr/bin/env python3
"""Validate the current MARINA candidate identity and unverified rollout boundary."""
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path

from release_contract import EXPECTED_MIGRATIONS

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "release" / "marina-smart-current-candidate.json"
STATE_PATH = ROOT / "knowledge" / "MARINA_SMART_CURRENT_STATE_20261008.md"
EXPECTED_BRANCH = "release/marina-shared-platform-rc2-20261104"
EXPECTED_PR = 314
EXPECTED_REVIEWED_SOURCE = "62a2caec856e8fe32801c9156d90de655298ad33"
ADDITIONAL_REQUIRED_WORKFLOWS = ("marina-shared-live-browser-postgres-ci.yml",)
REQUIRED_WORKFLOWS = frozenset({
    "marina-staging-readiness-ci.yml", "marina-rc1-source-gate.yml",
    "marina-full-stack-smoke-ci.yml", "marina-two-property-restore-ci.yml",
    "marina-shared-auth-preview-ci.yml", "marina-hold-contract.yml",
    "marina-hold-migration.yml", "marina-zz113-rollback-ci.yml",
    "staff-roles-ci.yml", "pms-chessboard-ci.yml", "pms-owner-grid-ci.yml",
    "marina-smart-hotel-setup-ci.yml", "marina-ai-embedded-ci.yml",
    "marina-whatsapp-workspace-ci.yml", "marina-hotel-knowledge-ci.yml",
    "marina-manual-payments-ci.yml", "marina-production-package-ci.yml",
    "marina-api-image-ci.yml", "marina-api-postgres-smoke-ci.yml",
})


def validate_source_lock(manifest: dict, root: Path) -> list[str]:
    """Verify source evidence only; never infer a successful CI or deployment."""
    errors = []
    migration_dir = root / "packages/database/prisma/migrations"
    actual = {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(migration_dir.glob("*/migration.sql"))}
    if manifest.get("migration_sha256") != actual:
        errors.append("migration SHA-256 lock differs from committed SQL")
    required = manifest.get("required_workflows")
    if (not isinstance(required, list) or not all(isinstance(x, str) for x in required)
            or len(required) != len(REQUIRED_WORKFLOWS)
            or set(required) != REQUIRED_WORKFLOWS):
        errors.append("mandatory workflow set is incomplete or duplicated")
    extra = manifest.get("additional_required_workflows")
    if extra != list(ADDITIONAL_REQUIRED_WORKFLOWS):
        errors.append("RC2 additional real-browser PostgreSQL workflow is missing or duplicated")
    for name in sorted(REQUIRED_WORKFLOWS.union(ADDITIONAL_REQUIRED_WORKFLOWS)):
        path = root / ".github/workflows" / name
        if not path.is_file():
            errors.append(f"missing required workflow: {name}")
            continue
        source = path.read_text(encoding="utf-8")
        # Restrict the check to the PR event; a push-only trigger is insufficient.
        pr_section = source.split("  pull_request:\n", 1)[-1].split("  workflow_dispatch:", 1)[0]
        if "  pull_request:\n" not in source or "'release/marina-smart-current-candidate.json'" not in pr_section:
            errors.append(f"candidate manifest does not trigger required workflow: {name}")
    if manifest.get("release_stage") != "SOURCE_LOCKED_SHARED_RUNTIME_PENDING":
        errors.append("shared runtime acceptance must remain pending")
    return errors


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
        "staging_gate": "isolated_synthetic_shared_pms",
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
    elif manifest["candidate_commit"] != EXPECTED_REVIEWED_SOURCE:
        errors.append("RC2 candidate_commit must pin the reviewed application SHA")
    if manifest.get("ci_baseline_commit") != EXPECTED_REVIEWED_SOURCE:
        errors.append("RC2 CI baseline must match the reviewed application SHA")

    migrations = ROOT / "packages" / "database" / "prisma" / "migrations"
    actual_migrations = tuple(sorted(p.parent.name for p in migrations.glob("*/migration.sql")))
    if len(actual_migrations) != len(EXPECTED_MIGRATIONS) or set(actual_migrations) != set(EXPECTED_MIGRATIONS):
        errors.append("committed migration files differ from the reviewed release contract")

    errors.extend(validate_source_lock(manifest, ROOT))

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
    print(f"FACT: mandatory_workflows={len(REQUIRED_WORKFLOWS)}+{len(ADDITIONAL_REQUIRED_WORKFLOWS)}; CI acceptance must be inspected separately")
    print("FACT: external staging, target restore and production authorization remain false")
    print("RESULT: MARINA CANDIDATE TRUTH GREEN; STAGING REQUIRED; CI STATUS NOT ASSERTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
