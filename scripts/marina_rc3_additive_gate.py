#!/usr/bin/env python3
"""Source gate for a NEW additive release without rewriting immutable RC3 evidence.

RC2/RC3 manifests remain 39-migration history. The current release must
preserve all 39 original SQL hashes and include pinned zz115 through zz117 SQL.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from marina_rc3_source_gate import ROOT, RC2_FILE, RC3_FILE, validate, git_blob_sha
from release_contract import EXPECTED_MIGRATIONS

NEW_MIGRATIONS = {
    "zz115_marina_chef_production_targets_20261110": "239d49674b3709b66619705264e6a1e996ab12b4fc5c93cf5a7b3a0ca423c5f1",
    "zz116_marina_kitchen_recipes_20261111": "b72d41027c2a25125c3bbb3fd92796c1a0538ef44c59d6db0561129da4fdc061",
    "zz117_marina_kitchen_stock_20261111": "3cf125cb7b28d4961f0ca991f1685f2bc012628742d2e108ff868b520c825879"
}
WORKFLOW_PATH = ".github/workflows/marina-shared-rc3-source-ci.yml"
ALLOWED_LEGACY_ERRORS = frozenset({
    "Prisma migrations drift from frozen RC2 (name or content)",
    "reviewed critical source changed: " + WORKFLOW_PATH,
    "reviewed critical source changed: services/api/app/hotel_finance.py",
})

def validate_additive() -> list[str]:
    errors: list[str] = []
    rc2 = json.loads((ROOT / RC2_FILE).read_text(encoding="utf8"))
    rc3 = json.loads((ROOT / RC3_FILE).read_text(encoding="utf8"))
    pinned = rc2.get("migration_sha256")
    if not isinstance(pinned, dict) or len(pinned) != 39:
        return ["historical RC2 expected 39 pinned migration hashes"]
    if len(EXPECTED_MIGRATIONS) != 42 or EXPECTED_MIGRATIONS[39:] != tuple(NEW_MIGRATIONS):
        errors.append("current release must contain exactly 39 historical + zz115 through zz117 migrations")
    expected = set(pinned) | set(NEW_MIGRATIONS)
    actual = {
        p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "packages/database/prisma/migrations").glob("*/migration.sql")
    }
    if set(actual) != expected or set(EXPECTED_MIGRATIONS) != expected:
        errors.append("new release migration set is not the approved additive 42")
    for name, sha in pinned.items():
        if actual.get(name) != sha:
            errors.append("historical RC2 migration drift: " + name)
    for name, sha in NEW_MIGRATIONS.items():
        if actual.get(name) != sha:
            errors.append("reviewed additive migration missing or changed: " + name)

    legacy_errors = validate(rc3, ROOT)
    for error in legacy_errors:
        if error not in ALLOWED_LEGACY_ERRORS:
            errors.append(error)
    # The historical source-gate file and the previous CI workflow remain
    # retrievable as pinned immutable Git blobs. The new workflow replaces
    # only how the current additive release is checked.
    for path in ("scripts/marina_rc3_source_gate.py", WORKFLOW_PATH):
        expected_sha = rc3.get("critical_git_blobs", {}).get(path)
        if not isinstance(expected_sha, str):
            errors.append("historical critical blob not pinned: " + path)
            continue
        old = subprocess.run(["git","-C",str(ROOT),"cat-file","blob",expected_sha],
                             capture_output=True)
        if old.returncode or git_blob_sha(old.stdout) != expected_sha:
            errors.append("historical critical Git blob unavailable: " + path)
        if path.endswith("marina_rc3_source_gate.py") and (
            not (ROOT / path).exists() or git_blob_sha((ROOT / path).read_bytes()) != expected_sha
        ):
            errors.append("historical RC3 gate source changed")
    return errors

if __name__ == "__main__":
    problems = validate_additive()
    if problems:
        for message in problems:
            print("MARINA_RC3_ADDITIVE_FAIL:", message)
        raise SystemExit(1)
    print("MARINA_RC3_ADDITIVE_PASS: historical=39/39 immutable, new=zz115+zz116+zz117, total=42, original source gate preserved, NO-GO")
