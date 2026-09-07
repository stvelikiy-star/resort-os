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

    print("MUTATING_UTILITY_SAFETY_PASS")


if __name__ == "__main__":
    main()
