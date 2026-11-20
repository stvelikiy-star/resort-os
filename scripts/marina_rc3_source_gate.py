#!/usr/bin/env python3
"""MARINA SMART shared RC3 *source* lock. Does not authorize production.

RC2 #314's historical candidate file stays immutable. RC3 source evidence is
bound to reviewed critical Git blob IDs and all 39 frozen Prisma SQL checksums.
CI conclusions are fetched from GitHub separately for the exact final PR head.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RC3_FILE = Path("release/marina-smart-shared-rc3.json")
RC2_FILE = Path("release/marina-smart-current-candidate.json")
EXPECTED_SOURCE_PR = 324
REQUIRED_WORKFLOWS = {
    "marina-shared-live-browser-postgres-ci.yml",
    "marina-shared-auth-preview-ci.yml",
    "marina-shared-ops-roles-ci.yml",
    "marina-two-property-restore-ci.yml",
    "marina-full-stack-smoke-ci.yml",
    "release-gate-ci.yml",
    "marina-shared-rc3-source-ci.yml",
}
REQUIRED_FLAGS_FALSE = (
    "external_staging_verified",
    "ubuntu_restore_verified",
    "production_cutover_authorized",
    "production_deployed",
    "mobile_live_e2e_verified",
    "real_whatsapp_ai_verified",
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()


def check_files(manifest: dict, root: Path) -> list[str]:
    errors: list[str] = []
    files = manifest.get("critical_git_blobs")
    if not isinstance(files, dict) or len(files) < 14:
        return ["missing reviewed critical Git source blob manifest"]
    for path_text, expected in sorted(files.items()):
        path = Path(path_text)
        if (path.is_absolute() or ".." in path.parts or not re.fullmatch(r"[0-9a-f]{40}", str(expected))):
            errors.append("invalid critical source file specification")
            continue
        location = root / path
        if not location.is_file() or git_blob_sha(location.read_bytes()) != expected:
            errors.append("reviewed critical source changed: " + path_text)
    return errors


def validate(manifest: dict, root: Path) -> list[str]:
    errors = []
    if manifest.get("schema_version") != 1 or manifest.get("product") != "MARINA SMART":
        errors.append("invalid RC3 identity")
    if manifest.get("release_id") != "MARINA_SHARED_RC3_20261104":
        errors.append("unexpected release identifier")
    if manifest.get("source_branch") != "release/marina-shared-platform-rc3-integration-20261104":
        errors.append("RC3 source branch mismatch")
    if manifest.get("pull_request") != EXPECTED_SOURCE_PR:
        errors.append("RC3 must stay in reviewed Draft PR #324")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("integration_source_sha", ""))):
        errors.append("RC3 integrated source SHA must be full 40-character hash")
    if manifest.get("state") != "DRAFT_SOURCE_ACCEPTANCE_PENDING":
        errors.append("RC3 source cannot declare release GO")
    for name in REQUIRED_FLAGS_FALSE:
        if manifest.get(name) is not False:
            errors.append(name + " must remain false until actual external verification")
    if manifest.get("migration_count") != 39:
        errors.append("migration count must remain 39")
    if manifest.get("legacy_rc2_manifest") != str(RC2_FILE):
        errors.append("RC2 immutable source lock reference missing")
    if set(manifest.get("required_workflows", [])) != REQUIRED_WORKFLOWS:
        errors.append("required workflow list not exact")
    for name in REQUIRED_WORKFLOWS:
        if not (root / ".github" / "workflows" / name).is_file():
            errors.append("missing mandatory CI workflow: " + name)

    try:
        rc2 = json.loads((root / RC2_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        errors.append("historical RC2 source lock absent")
    else:
        pinned = rc2.get("migration_sha256")
        if not isinstance(pinned, dict) or len(pinned) != 39:
            errors.append("historical 39-migration source lock missing")
        else:
            actual = {p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (root / "packages" / "database" / "prisma" / "migrations").glob("*/migration.sql")}
            if actual != pinned:
                errors.append("Prisma migrations drift from frozen RC2 (name or content)")
        for protected in ("production_cutover_authorized", "backup_restore_target_verified",
                          "external_staging_verified"):
            if rc2.get(protected) is not False:
                errors.append("frozen historical RC2 runtime status changed")
    errors.extend(check_files(manifest, root))
    return errors


def main() -> int:
    try:
        manifest = json.loads((ROOT / RC3_FILE).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print("MARINA_RC3_SOURCE_LOCK_FAIL: cannot read manifest: " + str(exc), file=sys.stderr)
        return 1
    errors = validate(manifest, ROOT)
    if errors:
        for reason in errors:
            print("MARINA_RC3_SOURCE_LOCK_FAIL: " + reason, file=sys.stderr)
        return 1
    print("MARINA_RC3_SOURCE_LOCK_PASS: "
          + f"critical_files={len(manifest['critical_git_blobs'])} "
          + "frozen_migrations=39 "
          + "required_ci=7 "
          + "production_no_go=true "
          + "external_stage_not_proven=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
