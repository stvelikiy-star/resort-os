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
    Path("docs/RELEASE_0.61.0_2026-09-06.md"),
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
    "docs/README.md",
    "docs/STAGING_RUNBOOK_2026-08-28.md",
    "scripts/release_rc_truth_guard.py",
    ".github/workflows/release-rc-truth-ci.yml",
    ".github/workflows/launch-acceptance-ci.yml",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOW_NON_ACCEPTED_HEAD_FLAG = "--allow-non-accepted-head"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def validate_workflows(label: str, evidence: object, errors: list[str]) -> None:
    if not isinstance(evidence, dict):
        errors.append(f"{label} must be an object")
        return
    triggered = evidence.get("triggered")
    success = evidence.get("success")
    failures = evidence.get("failures")
    if not isinstance(triggered, int) or triggered <= 0:
        errors.append(f"{label} must contain a positive triggered count")
        return
    if success != triggered or failures != 0:
        errors.append(f"{label} must be all-success with zero failures")


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

    if rc.get("schema_version") != 1:
        errors.append("unsupported RC manifest schema")
    if rc.get("release_version") != "0.61.0":
        errors.append("release_version must be 0.61.0 for the frozen release boundary")
    if rc.get("status") != "INTERNAL_RC_FROZEN_EXTERNAL_EVIDENCE_PENDING":
        errors.append("RC status is not the expected frozen pre-external state")
    if rc.get("source_branch") != "audit/full-project-fixes-20260905":
        errors.append("source_branch must identify the exact tested PR #116 source branch")
    if rc.get("production_source_branch") != "main":
        errors.append("production_source_branch must be main")
    if rc.get("main_allowed_as_production_source") is not True:
        errors.append("main must be the allowed production source branch")
    for key in ("external_beget_staging_verified", "legacy_live_rollback_verified", "production_cutover_authorized"):
        if rc.get(key) is not False:
            errors.append(f"{key} must remain false until real external evidence exists")

    if rc.get("migration_count") != 22:
        errors.append("migration_count must be 22 for Resort OS 0.61.0")
    if rc.get("critical_constraint_count") != 87:
        errors.append("critical_constraint_count must be 87 for Resort OS 0.61.0")
    seed = rc.get("canonical_property_seed") or {}
    if seed != {"rooms": 84, "room_categories": 12, "rate_rows": 48}:
        errors.append("canonical_property_seed must remain 84 rooms / 12 categories / 48 rate rows")

    accepted = str(rc.get("accepted_executable_head") or "").lower()
    observed = str(rc.get("observed_merge_commit") or "").lower()
    postmerge = str(rc.get("postmerge_truth_head") or "").lower()
    for label, value in (
        ("accepted_executable_head", accepted),
        ("observed_merge_commit", observed),
        ("postmerge_truth_head", postmerge),
    ):
        if not SHA_RE.fullmatch(value):
            errors.append(f"{label} is not an exact 40-character Git SHA")

    validate_workflows("accepted_head_workflows", rc.get("accepted_head_workflows"), errors)
    validate_workflows("merged_main_workflows", rc.get("merged_main_workflows"), errors)
    validate_workflows("postmerge_truth_workflows", rc.get("postmerge_truth_workflows"), errors)

    if rc.get("accepted_head_workflows") != {"triggered": 59, "success": 59, "failures": 0}:
        errors.append("accepted head evidence must remain exactly 59/59 for PR #116")
    if rc.get("merged_main_workflows") != {"triggered": 38, "success": 38, "failures": 0}:
        errors.append("merged main eligible evidence must remain exactly 38/38")
    if rc.get("postmerge_truth_workflows") != {"triggered": 38, "success": 38, "failures": 0}:
        errors.append("post-merge truth evidence must remain exactly 38/38")
    if rc.get("observed_merge_tree_equivalent") is not True:
        errors.append("observed merge tree equivalence must be true")

    # PR #116's main merge intentionally produced two fail-closed release-control
    # workflow failures because the previous frozen manifest still described 0.60.0.
    # The 38/38 main evidence above records the successful product/security/
    # migration/staging workflows. This guard itself is the refreeze mechanism that
    # must turn release truth/launch acceptance green again; it never treats those
    # pre-refreeze failures as product success or external evidence.

    if not allow_non_accepted_head:
        if SHA_RE.fullmatch(accepted):
            try:
                git("cat-file", "-e", f"{accepted}^{{commit}}")
                changed = git("diff", "--name-only", accepted, "HEAD")
                unexpected = sorted(path for path in changed.splitlines() if path and path not in ALLOWED_HYGIENE_PATHS)
                if unexpected:
                    errors.append("executable/product drift after frozen accepted head: " + ", ".join(unexpected))
            except subprocess.CalledProcessError as exc:
                errors.append(f"cannot validate accepted executable head: {exc}")

        if SHA_RE.fullmatch(accepted) and SHA_RE.fullmatch(observed):
            try:
                observed_diff = git("diff", "--name-only", accepted, observed)
                if observed_diff:
                    errors.append("observed main merge is not tree-equivalent to accepted executable head")
            except subprocess.CalledProcessError as exc:
                errors.append(f"cannot validate observed main merge: {exc}")

        if SHA_RE.fullmatch(observed) and SHA_RE.fullmatch(postmerge):
            try:
                postmerge_diff = git("diff", "--name-only", observed, postmerge)
                unexpected = sorted(path for path in postmerge_diff.splitlines() if path and path not in ALLOWED_HYGIENE_PATHS)
                if unexpected:
                    errors.append("post-merge truth head contains executable/product drift: " + ", ".join(unexpected))
            except subprocess.CalledProcessError as exc:
                errors.append(f"cannot validate post-merge truth head: {exc}")

    for doc in DOCS:
        try:
            text = doc.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"cannot read {doc}: {exc}")
            continue
        if accepted not in text:
            errors.append(f"{doc} does not cite accepted executable head")
        if observed not in text:
            errors.append(f"{doc} does not cite observed main merge")
        if "main" not in text.lower() or "production source" not in text.lower():
            errors.append(f"{doc} does not state the main production-source boundary")
        if "EXTERNAL" not in text or "STOP" not in text:
            errors.append(f"{doc} does not preserve external/cutover STOP boundary")
        if "22" not in text or "87" not in text:
            errors.append(f"{doc} does not state the 22-migration / 87-constraint 0.61.0 boundary")

    if errors:
        for error in errors:
            fail(error)
        print("RESULT: RELEASE RC TRUTH RED")
        return 1

    print(f"FACT: release_version={rc['release_version']}")
    print(f"FACT: accepted_executable_head={accepted}")
    print(f"FACT: observed_merge_commit={observed}")
    print(f"FACT: postmerge_truth_head={postmerge}")
    print("FACT: accepted_head_workflows=59/59")
    print("FACT: merged_main_eligible_workflows=38/38")
    print("FACT: pre_refreeze_release_control_failures=Release RC Truth CI,Launch Acceptance CI")
    print("FACT: migrations=22")
    print("FACT: critical_constraints=87")
    print("FACT: production_source_branch=main")
    print("FACT: production_cutover_authorized=false")
    if allow_non_accepted_head:
        print("FACT: candidate_head_mode=non_accepted_head_allowed; frozen tree comparison intentionally skipped")
        print("PASS: RC manifest and canonical docs are structurally consistent for candidate validation")
        print("RESULT: RELEASE RC CONTRACT GREEN; CANDIDATE IS NOT YET MERGED FROZEN MAIN")
    else:
        print("PASS: RC manifest, canonical docs and frozen executable tree are consistent")
        print("RESULT: RELEASE RC TRUTH GREEN; EXTERNAL CUTOVER STOP")
    return 0


if __name__ == "__main__":
    sys.exit(main())
