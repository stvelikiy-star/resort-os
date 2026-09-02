#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RC_PATH = Path("release/current-rc.json")
DOCS = (Path("knowledge/04_CURRENT_STATE.md"), Path("knowledge/09_LAUNCH_ACCEPTANCE.md"))
ALLOWED_HYGIENE_PATHS = {
    "release/current-rc.json",
    "knowledge/04_CURRENT_STATE.md",
    "knowledge/09_LAUNCH_ACCEPTANCE.md",
    "docs/README.md",
    "docs/STAGING_RUNBOOK_2026-08-28.md",
    "scripts/release_rc_truth_guard.py",
    ".github/workflows/release-rc-truth-ci.yml",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def main() -> int:
    errors: list[str] = []
    try:
        rc = json.loads(RC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read RC manifest: {exc}")
        return 1

    if rc.get("schema_version") != 1:
        errors.append("unsupported RC manifest schema")
    if rc.get("status") != "INTERNAL_RC_FROZEN_EXTERNAL_EVIDENCE_PENDING":
        errors.append("RC status is not the expected frozen pre-external state")
    if rc.get("source_branch") != "integration/site-pms-cms-20260827":
        errors.append("source_branch must remain the integration branch")
    if rc.get("production_source_branch") != "integration/site-pms-cms-20260827":
        errors.append("production_source_branch must remain the integration branch")
    if rc.get("main_allowed_as_production_source") is not False:
        errors.append("main must remain forbidden as production source")
    for key in ("external_beget_staging_verified", "legacy_live_rollback_verified", "production_cutover_authorized"):
        if rc.get(key) is not False:
            errors.append(f"{key} must remain false until external evidence exists")

    accepted = str(rc.get("accepted_executable_head") or "").lower()
    observed = str(rc.get("observed_integration_merge") or "").lower()
    for label, value in (("accepted_executable_head", accepted), ("observed_integration_merge", observed)):
        if not SHA_RE.fullmatch(value):
            errors.append(f"{label} is not an exact 40-character Git SHA")

    workflows = rc.get("accepted_head_workflows") or {}
    triggered = workflows.get("triggered")
    success = workflows.get("success")
    failures = workflows.get("failures")
    if not isinstance(triggered, int) or triggered <= 0:
        errors.append("accepted head workflow evidence must contain a positive triggered count")
    elif success != triggered or failures != 0:
        errors.append("accepted head workflow evidence must be all-success with zero failures")
    if rc.get("observed_merge_tree_equivalent") is not True:
        errors.append("observed merge tree equivalence must be true")

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
                errors.append("observed integration merge is not tree-equivalent to accepted executable head")
        except subprocess.CalledProcessError as exc:
            errors.append(f"cannot validate observed integration merge: {exc}")

    for doc in DOCS:
        try:
            text = doc.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"cannot read {doc}: {exc}")
            continue
        if accepted not in text:
            errors.append(f"{doc} does not cite accepted executable head")
        if observed not in text:
            errors.append(f"{doc} does not cite observed integration merge")
        if "main` is not a production source" not in text and "main is not a production source" not in text:
            errors.append(f"{doc} does not state that main is not a production source")
        if "EXTERNAL" not in text or "STOP" not in text:
            errors.append(f"{doc} does not preserve external/cutover STOP boundary")

    if errors:
        for error in errors:
            fail(error)
        print("RESULT: RELEASE RC TRUTH RED")
        return 1

    print(f"FACT: accepted_executable_head={accepted}")
    print(f"FACT: observed_integration_merge={observed}")
    print(f"FACT: accepted_head_workflows={triggered}/{triggered}")
    print("PASS: RC manifest, canonical docs and frozen executable tree are consistent")
    print("PASS: main is explicitly forbidden as production source")
    print("RESULT: RELEASE RC TRUTH GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
