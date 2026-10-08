#!/usr/bin/env python3
"""Static fail-closed contract for the first MARINA SMART tenant rollout slice.

This check never connects to a database and never changes runtime state. It verifies
that the migration, seed path, trusted auth context and release truth move together.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"missing required file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> int:
    migration = read("packages/database/prisma/migrations/zz107_marina_tenants_20261008/migration.sql")
    for marker in (
        'CREATE TABLE IF NOT EXISTS "tenants"',
        'ALTER TABLE "properties"',
        'ADD COLUMN IF NOT EXISTS "tenantId"',
        "legacy_",
        'FOREIGN KEY ("tenantId")',
        "ON DELETE RESTRICT",
        '"properties_tenant_code_key"',
    ):
        if marker not in migration:
            raise AssertionError(f"tenant migration marker missing: {marker}")

    seed = read("scripts/seed_from_intake.py")
    for marker in ("TENANT_CODE =", "async def upsert_tenant", "async def tenant_schema_available", "INSERT INTO tenants", '"tenantId"'):
        if marker not in seed:
            raise AssertionError(f"tenant-aware seed marker missing: {marker}")

    ak_bootstrap = read("scripts/bootstrap_ak_bermet_test.py")
    for marker in ("async def tenant_schema_available", "async def upsert_tenant", '"tenantId"'):
        if marker not in ak_bootstrap:
            raise AssertionError(f"AK BERMET tenant bootstrap marker missing: {marker}")

    marina_bootstrap = read("scripts/bootstrap_marina_test.py")
    for marker in ("async def tenant_schema_available", "async def upsert_tenant", '"tenantId"'):
        if marker not in marina_bootstrap:
            raise AssertionError(f"MARINA test tenant bootstrap marker missing: {marker}")

    auth = read("services/api/app/auth.py")
    for marker in (
        'MARINA_TENANT_CONTEXT_ENABLED =',
        'os.environ.get("MARINA_TENANT_CONTEXT_ENABLED", "false")',
        "def _tenant_context_select_sql()",
        'p."tenantId" AS tenant_id',
        'NULL::uuid AS tenant_id',
        'property_id=_optional_uuid_text(row["property_id"])',
        'tenant_id=_optional_uuid_text(row["tenant_id"])',
        'row["property_code"] != PROPERTY_CODE',
    ):
        if marker not in auth:
            raise AssertionError(f"trusted auth-context marker missing: {marker}")

    staging_gate = read("scripts/verify_marina_multitenant_staging.py")
    for marker in (
        "async def main()",
        "MARINA_STAGING_BASE_URL",
        "MARINA_STAGING_DATABASE_URL",
        'to_regclass(\'public.tenants\')',
        "properties without tenant",
        "read-only foundation gate passed",
    ):
        if marker not in staging_gate:
            raise AssertionError(f"staging gate marker missing: {marker}")

    staging_workflow = read(".github/workflows/marina-multitenant-staging-gate.yml")
    for marker in (
        "workflow_dispatch:",
        "MARINA_STAGING_BASE_URL",
        "MARINA_STAGING_DATABASE_URL",
        "verify_marina_multitenant_staging.py",
        "contents: read",
    ):
        if marker not in staging_workflow:
            raise AssertionError(f"manual staging workflow marker missing: {marker}")

    manifest = read("release/marina-smart-current-candidate.json")
    for marker in (
        '"product": "MARINA SMART"',
        '"status": "INTERNAL_CANDIDATE_STAGING_REQUIRED"',
        '"migration_count": 31',
        '"tenant_model": "Tenant/Property"',
        '"tenant_context_enabled": false',
        '"external_staging_verified": false',
        '"cross_tenant_e2e_verified": false',
        '"production_cutover_authorized": false',
    ):
        if marker not in manifest:
            raise AssertionError(f"candidate manifest marker missing: {marker}")

    current_state = read("knowledge/MARINA_SMART_CURRENT_STATE_20261008.md")
    for marker in (
        "PR: #234",
        "CI: 41/41 SUCCESS",
        "Tenant/Property",
        "two-tenant cross-tenant login/read/write E2E",
        "The existing roles, navigation and approved compact chessboard remain unchanged.",
    ):
        if marker not in current_state:
            raise AssertionError(f"candidate state marker missing: {marker}")

    truth_guard = read("scripts/marina_candidate_truth_guard.py")
    for marker in (
        "EXPECTED_HEAD =",
        "EXPECTED_BRANCH =",
        "candidate_commit",
        "cross_tenant_e2e_verified",
        "MARINA CANDIDATE TRUTH GREEN",
    ):
        if marker not in truth_guard:
            raise AssertionError(f"candidate truth guard marker missing: {marker}")

    production_env = read(".env.production.example")
    if "MARINA_TENANT_CONTEXT_ENABLED=false" not in production_env:
        raise AssertionError("production tenant context must remain disabled until staging gates pass")

    compose = read("compose.production.yaml")
    if "MARINA_TENANT_CONTEXT_ENABLED:" not in compose:
        raise AssertionError("production compose must pass the explicit tenant context flag")

    print("MARINA_MULTITENANT_FOUNDATION_PASS")
    print("BOUNDARY: migration + seed + trusted auth context + candidate truth are prepared; staging deployment remains STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
