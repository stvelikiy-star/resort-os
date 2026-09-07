#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    rc = read("scripts/release_candidate_check.sh")
    baseline = read("scripts/generate_migration_baseline.sh")
    owner_legacy = read("scripts/verify_owner_control_v2.py")
    owner_ci = read("scripts/verify_owner_control_v2_ci.py")
    owner_workflow = read(".github/workflows/owner-control-v2-ci.yml")

    require("is retired" in rc, "legacy release_candidate_check is explicitly retired")
    require("exit 2" in rc, "legacy release_candidate_check always stops")
    require("prisma db push" in rc, "retirement reason records forbidden db-push behavior")
    require("npx prisma db push" not in rc, "retired entrypoint cannot execute prisma db push")
    require("/confirm-payment" not in rc, "retired entrypoint cannot create synthetic payments")
    require("scripts/release_operations_smoke.py" not in rc, "retired entrypoint cannot mutate room/task state")

    require('case "${APP_ENV:-}" in' in baseline, "baseline generator requires explicit APP_ENV")
    require("development|test|ci" in baseline, "baseline generator allowlist is disposable-only")
    require("staging" in baseline and "production" in baseline, "baseline generator explicitly forbids staging/production")
    require("${APP_ENV:-development}" not in baseline, "baseline generator has no implicit development fallback")
    require("ALLOW_REPLACE_MIGRATIONS" in baseline, "migration-history replacement still requires explicit opt-in")

    require("is retired" in owner_legacy, "legacy owner-control mutation entrypoint is retired")
    require("verify_owner_control_v2_ci.py" in owner_legacy, "legacy owner-control entrypoint points to guarded CI implementation")
    require('APP_ENV = os.environ.get("APP_ENV", "")' in owner_ci, "owner-control CI requires explicit environment")
    require('APP_ENV not in {"ci", "test"}' in owner_ci, "owner-control CI is limited to ci/test")
    require('LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}' in owner_ci, "owner-control CI defines localhost-only boundary")
    require("core_host not in LOCAL_HOSTS" in owner_ci, "owner-control CI rejects non-local Core")
    require("db_host not in LOCAL_HOSTS" in owner_ci, "owner-control CI rejects non-local PostgreSQL")
    require('os.environ.get("BOOTSTRAP_OWNER_PASSWORD", "")' in owner_ci, "owner-control CI has no password fallback")
    require('os.environ.get("AUTOMATION_SERVICE_KEY", "")' in owner_ci, "owner-control CI has no service-key fallback")
    require("APP_ENV: ci" in owner_workflow, "owner-control workflow explicitly declares CI environment")
    require("verify_owner_control_v2_ci.py" in owner_workflow, "owner-control workflow invokes guarded E2E only")

    print("MUTATING_UTILITY_SAFETY_PASS")


if __name__ == "__main__":
    main()
