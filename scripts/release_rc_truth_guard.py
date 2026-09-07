#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RC_PATH = Path("release/current-rc.json")
DOCS = (
    Path("knowledge/04_CURRENT_STATE.md"),
    Path("knowledge/09_LAUNCH_ACCEPTANCE.md"),
    Path("docs/DEPLOYMENT_RUNBOOK.md"),
    Path("docs/RELEASE_0.62.1_2026-09-07.md"),
)
ALLOWED_HYGIENE_PATHS = {
    "release/current-rc.json",
    "release/launch-evidence.example.json",
    "knowledge/04_CURRENT_STATE.md",
    "knowledge/09_LAUNCH_ACCEPTANCE.md",
    "docs/DEPLOYMENT_RUNBOOK.md",
    "docs/PRODUCTION_DATABASE_MIGRATIONS.md",
    "docs/RELEASE_0.60.0_2026-09-05.md",
    "docs/RELEASE_0.61.0_2026-09-06.md",
    "docs/RELEASE_0.62.0_2026-09-07.md",
    "docs/RELEASE_0.62.1_2026-09-07.md",
    "docs/README.md",
    "docs/STAGING_RUNBOOK_2026-08-28.md",
    "scripts/release_rc_truth_guard.py",
    "scripts/verify_internal_hardening.py",
    ".github/workflows/release-rc-truth-ci.yml",
    ".github/workflows/launch-acceptance-ci.yml",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOW_NON_ACCEPTED_HEAD_FLAG = "--allow-non-accepted-head"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def validate_workflows(label: str, evidence: object, expected: dict[str, int], errors: list[str]) -> None:
    if not isinstance(evidence, dict):
        errors.append(f"{label} must be an object")
        return
    if evidence != expected:
        errors.append(f"{label} must equal {expected}, got {evidence}")


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
        "release_version": "0.62.1",
        "status": "INTERNAL_RC_FROZEN_EXTERNAL_EVIDENCE_PENDING",
        "source_branch": "audit/internal-hardening-20260907",
        "accepted_executable_head": "b3bb0c1be4c522d765509796ddd1d32e8606dc89",
        "observed_merge_commit": "7f689458b2cf507d76a8c54fbe164e9492f79aca",
        "postmerge_truth_head": "7f689458b2cf507d76a8c54fbe164e9492f79aca",
        "production_source_branch": "main",
        "migration_count": 22,
        "critical_constraint_count": 87,
    }
    if rc.get("schema_version") != 1:
        errors.append("unsupported RC manifest schema")
    for key, value in expected.items():
        if rc.get(key) != value:
            errors.append(f"{key} must be {value!r}")
    if rc.get("main_allowed_as_production_source") is not True:
        errors.append("main must remain the allowed production source branch")
    if rc.get("observed_merge_tree_equivalent") is not True:
        errors.append("observed merge must remain tree-equivalent to accepted head")
    for key in ("external_beget_staging_verified", "legacy_live_rollback_verified", "production_cutover_authorized"):
        if rc.get(key) is not False:
            errors.append(f"{key} must remain false until real external evidence exists")
    if rc.get("canonical_property_seed") != {"rooms": 84, "room_categories": 12, "rate_rows": 48}:
        errors.append("canonical property seed must remain 84 rooms / 12 categories / 48 rates")

    validate_workflows("accepted_head_workflows", rc.get("accepted_head_workflows"), {"triggered": 28, "success": 28, "failures": 0}, errors)
    validate_workflows("merged_main_workflows", rc.get("merged_main_workflows"), {"triggered": 23, "success": 23, "failures": 0}, errors)
    validate_workflows("postmerge_truth_workflows", rc.get("postmerge_truth_workflows"), {"triggered": 23, "success": 23, "failures": 0}, errors)

    accepted = str(rc.get("accepted_executable_head") or "").lower()
    observed = str(rc.get("observed_merge_commit") or "").lower()
    postmerge = str(rc.get("postmerge_truth_head") or "").lower()
    for label, value in (("accepted_executable_head", accepted), ("observed_merge_commit", observed), ("postmerge_truth_head", postmerge)):
        if not SHA_RE.fullmatch(value):
            errors.append(f"{label} is not an exact 40-character Git SHA")

    if not allow_non_accepted_head:
        try:
            git("cat-file", "-e", f"{accepted}^{{commit}}")
            changed = git("diff", "--name-only", accepted, "HEAD")
            unexpected = sorted(path for path in changed.splitlines() if path and path not in ALLOWED_HYGIENE_PATHS)
            if unexpected:
                errors.append("executable/product drift after accepted head: " + ", ".join(unexpected))
            observed_diff = git("diff", "--name-only", accepted, observed)
            if observed_diff:
                errors.append("observed main merge is not tree-equivalent to accepted executable head")
            postmerge_diff = git("diff", "--name-only", observed, postmerge)
            unexpected_post = sorted(path for path in postmerge_diff.splitlines() if path and path not in ALLOWED_HYGIENE_PATHS)
            if unexpected_post:
                errors.append("post-merge truth head contains executable/product drift: " + ", ".join(unexpected_post))
        except subprocess.CalledProcessError as exc:
            errors.append(f"cannot validate frozen release tree: {exc}")

    required_markers = ("0.62.1", accepted, observed, "22", "87", "main", "EXTERNAL", "STOP")
    for doc in DOCS:
        try:
            text = doc.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"cannot read {doc}: {exc}")
            continue
        for marker in required_markers:
            if marker not in text:
                errors.append(f"{doc} missing release marker {marker!r}")

    if errors:
        for error in errors:
            fail(error)
        print("RESULT: RELEASE RC TRUTH RED")
        return 1

    print("FACT: release_version=0.62.1")
    print(f"FACT: accepted_executable_head={accepted}")
    print(f"FACT: observed_merge_commit={observed}")
    print("FACT: accepted_head_workflows=28/28")
    print("FACT: merged_main_eligible_workflows=23/23")
    print("FACT: pre_refreeze_release_control_failure=Release RC Truth CI")
    print("FACT: migrations=22")
    print("FACT: critical_constraints=87")
    print("FACT: production_source_branch=main")
    print("FACT: production_cutover_authorized=false")
    if allow_non_accepted_head:
        print("RESULT: RELEASE RC CONTRACT GREEN; CANDIDATE HYGIENE HEAD ALLOWED")
    else:
        print("RESULT: RELEASE RC TRUTH GREEN; EXTERNAL CUTOVER STOP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
