#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RC_PATH = Path("release/current-rc.json")
RELEASE_DOC = Path("docs/RELEASE_0.62.2_REFREEZE_2026-09-17.md")
ALLOWED_HYGIENE_PATHS = {
    "release/current-rc.json",
    "docs/RELEASE_0.62.2_REFREEZE_2026-09-17.md",
    "scripts/release_rc_truth_guard.py",
    "scripts/verify_internal_hardening.py",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOW_NON_ACCEPTED_HEAD_FLAG = "--allow-non-accepted-head"

EXPECTED_ACCEPTED = "7b14e32dbf64ffd617a5c7720f98add24efd1341"
EXPECTED_TESTED_PR_HEAD = "5c606e5447958595f52c9d7dbacdb177e010cb4c"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def main() -> int:
    errors: list[str] = []
    allow_non_accepted_head = ALLOW_NON_ACCEPTED_HEAD_FLAG in sys.argv[1:]
    unknown_args = [arg for arg in sys.argv[1:] if arg != ALLOW_NON_ACCEPTED_HEAD_FLAG]
    if unknown_args:
        fail("unknown argument(s): " + ", ".join(unknown_args))
        return 2

    try:
        rc = json.loads(RC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read RC manifest: {exc}")
        return 1

    expected = {
        "release_version": "0.62.2",
        "status": "INTERNAL_RC_FROZEN_EXTERNAL_EVIDENCE_PENDING",
        "source_branch": "main",
        "accepted_executable_head": EXPECTED_ACCEPTED,
        "tested_pr_head": EXPECTED_TESTED_PR_HEAD,
        "tested_pr_number": 172,
        "observed_merge_commit": EXPECTED_ACCEPTED,
        "postmerge_truth_head": EXPECTED_ACCEPTED,
        "production_source_branch": "main",
        "migration_count": 24,
        "critical_constraint_count": 93,
        "launch_profile": "FULL_NO_PAYMENTS",
        "payment_operations_enabled": False,
        "nfc_wallet_enabled": False,
        "mkassa_enabled": False,
    }
    if rc.get("schema_version") != 1:
        errors.append("unsupported RC manifest schema")
    for key, value in expected.items():
        if rc.get(key) != value:
            errors.append(f"{key} must be {value!r}")

    if rc.get("main_allowed_as_production_source") is not True:
        errors.append("main must remain the allowed production source branch")
    if rc.get("observed_merge_tree_equivalent") is not True:
        errors.append("accepted executable head and observed merge must be the same main boundary")
    if rc.get("observed_merge_allowed_hygiene_only") is not True:
        errors.append("post-boundary drift must remain hygiene-only")
    if rc.get("observed_merge_allowed_hygiene_paths") != []:
        errors.append("accepted main boundary must not carry unclassified merge drift")

    if rc.get("accepted_head_workflows") != {"triggered": 48, "success": 48, "failures": 0}:
        errors.append("accepted PR #172 workflow evidence must remain 48/48 SUCCESS")
    expected_main = {"triggered": 39, "success": 37, "failures": 1, "other_completed": 1}
    if rc.get("merged_main_workflows") != expected_main:
        errors.append("first main-push workflow evidence does not match the recorded post-merge observation")
    if rc.get("postmerge_truth_workflows") != expected_main:
        errors.append("postmerge truth workflow evidence does not match the recorded post-merge observation")

    if rc.get("canonical_property_seed") != {"rooms": 84, "room_categories": 12, "rate_rows": 48}:
        errors.append("canonical property seed must remain 84 rooms / 12 categories / 48 rates")
    for key in ("external_beget_staging_verified", "legacy_live_rollback_verified", "production_cutover_authorized"):
        if rc.get(key) is not False:
            errors.append(f"{key} must remain false until real external evidence exists")

    accepted = str(rc.get("accepted_executable_head") or "").lower()
    tested = str(rc.get("tested_pr_head") or "").lower()
    for label, value in (("accepted_executable_head", accepted), ("tested_pr_head", tested)):
        if not SHA_RE.fullmatch(value):
            errors.append(f"{label} is not an exact 40-character Git SHA")

    if not allow_non_accepted_head:
        try:
            git("cat-file", "-e", f"{accepted}^{{commit}}")
            changed = git("diff", "--name-only", accepted, "HEAD")
            unexpected = sorted(path for path in changed.splitlines() if path and path not in ALLOWED_HYGIENE_PATHS)
            if unexpected:
                errors.append("executable/product drift after accepted head: " + ", ".join(unexpected))
        except subprocess.CalledProcessError as exc:
            errors.append(f"cannot validate frozen release tree: {exc}")

    try:
        release_doc = RELEASE_DOC.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"cannot read {RELEASE_DOC}: {exc}")
        release_doc = ""
    for marker in (
        "0.62.2",
        EXPECTED_ACCEPTED,
        EXPECTED_TESTED_PR_HEAD,
        "48/48",
        "FULL_NO_PAYMENTS",
        "24 migrations",
        "93 critical constraints",
        "84 rooms",
        "12 categories",
        "EXTERNAL",
        "STOP",
    ):
        if marker not in release_doc:
            errors.append(f"{RELEASE_DOC} missing release marker {marker!r}")

    if errors:
        for error in errors:
            fail(error)
        print("RESULT: RELEASE RC TRUTH RED")
        return 1

    print("FACT: release_version=0.62.2")
    print(f"FACT: accepted_executable_head={accepted}")
    print(f"FACT: tested_pr_head={tested}")
    print("FACT: tested_pr_workflows=48/48")
    print("FACT: launch_profile=FULL_NO_PAYMENTS")
    print("FACT: payment_operations_enabled=false")
    print("FACT: migrations=24")
    print("FACT: critical_constraints=93")
    print("FACT: production_source_branch=main")
    print("FACT: production_cutover_authorized=false")
    if allow_non_accepted_head:
        print("RESULT: RELEASE RC CONTRACT GREEN; CANDIDATE HYGIENE HEAD ALLOWED")
    else:
        print("RESULT: RELEASE RC TRUTH GREEN; EXTERNAL CUTOVER STOP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
