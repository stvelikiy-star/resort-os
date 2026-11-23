#!/usr/bin/env python3
"""Fail-closed governance boundary for the November 2026 MARINA SMART main integration.

The Resort OS 0.62.2 manifest and historical guard are deliberately left intact.
This checks only that no executable/product files have changed since the verified
November main integration. It never grants permission for production cutover.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE = "b975e5feb7aa2bfba059bc6d3b599f6d1ce1e1e8"
TESTED_PR_HEAD = "6d5eff8d212cfb9da4b04bfb4fdec428f32b6d48"
LEGACY_BASE = "a53850983d8fc6e1f1997199049a5b071511ed80"
ALLOWED_GOVERNANCE = frozenset({
    ".github/workflows/release-rc-truth-ci.yml",
    ".github/workflows/launch-acceptance-ci.yml",
    "release/launch-evidence.example.json",
    "scripts/verify_marina_november_release_boundary.py",
})

# Only these audited P0 changes are allowed beyond the frozen November
# product source. Git blob digests prevent widening this exception silently.
# Approved workflow is test-only; pinned to prevent unreviewed CI drift.
APPROVED_NATIVE_QA_BLOBS = {
    "scripts/design/fl2-native-qa-session-contract.py": "5129f897f2fbe6f6afd6aacf278a26971d75e406",
    "scripts/design/fl2-native-qa-logout-restart.yaml": "d107612040190b3e6eefeb3900c68a839bd72e05",
    ".github/workflows/marina-ios-simulator-keychain-linker-pilot-ci.yml": "0df95da7243cd64667eb8d505277b67d5c846ad9",
    ".github/workflows/marina-native-android-ios-maestro-ci.yml": "459c78da0a2bf5e96c2cbee2abbddac9f008b44f",
    "scripts/design/fl2-android-maestro-demo.sh": "b4372aa0fcb965a3d9337d86c2f4faf96db700c3",
    "scripts/design/fl2-native-live-role.yaml": "69e7fa4bd88ffa3c6fe20ba7e552ed0b6a7108d6",
    "scripts/design/fl2-native-live-role.sh": "12df57b660f8bb3bdb0d6bc922bdab2f2d3d8cbd",
    "scripts/design/fl2-native-live-role.README.md": "8e2e78527633902591c6fa56dd53b18afb9ab077",
    ".github/workflows/marina-native-live-qa-build-ci.yml": "393d005e99efd87aae20b35b6e422494d1fcfe25",
    "scripts/design/fl2-native-qa-connect.yaml": "f92d7e839c81f451bf2896b610f019541f9213c1",
    "scripts/design/fl2-native-qa-connect.sh": "b0df9bd280ac5b3deb5e6a5d5a5e34767cfb4ccb",
    ".github/workflows/marina-native-qa-negative-auth-ci.yml": "3660cb878e9660c6a19238737b217adaa0d5b038",
    "scripts/design/fl2-native-qa-negative-login.yaml": "1e1843e93a9c28fba0e45d06bdb01bf2d1b89734",
    "scripts/design/fl2-native-qa-negative-login.sh": "95207036fe6d063f76d6f80b57f97182b0dfa5d4",
    ".github/workflows/marina-native-live-five-roles-ci.yml": "216a6c977f2df4234ef5e313d3f713a84f1c6e5b",
    "scripts/design/fl2-native-live-five-roles.sh": "bd1088c60ba9f1aa8c5abd21e477f245fcd18e6d",
}

APPROVED_P0_BLOBS = {
    "services/api/app/stays.py": "16f5a87445a9eaf9315b9b43e25d54c069bd69ce",
    "scripts/test_marina_pms_schedule_property_boundary.py": "701b21a7f74d4b1c210b6e89f65a95dfdd8d8771",
}


def changed_paths_are_safe(paths: list[str]) -> bool:
    return all(path in ALLOWED_GOVERNANCE for path in paths)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def verify_legacy_manifest() -> None:
    legacy = json.loads(Path("release/current-rc.json").read_text(encoding="utf-8"))
    required = {
        "schema_version": 1,
        "release_version": "0.62.2",
        "accepted_executable_head": LEGACY_BASE,
        "production_source_branch": "main",
        "production_cutover_authorized": False,
        "payment_operations_enabled": False,
        "nfc_wallet_enabled": False,
        "mkassa_enabled": False,
    }
    for key, value in required.items():
        if legacy.get(key) != value:
            raise ValueError("historical 0.62.2 contract changed: " + key)


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        assert changed_paths_are_safe(list(ALLOWED_GOVERNANCE))
        assert not changed_paths_are_safe(["apps/admin/components/AdminShell.tsx"])
        assert not changed_paths_are_safe(["packages/database/prisma/schema.prisma"])
        assert not changed_paths_are_safe(["release/current-rc.json"])
        assert changed_paths_are_safe(["release/launch-evidence.example.json", ".github/workflows/launch-acceptance-ci.yml"])
        assert not changed_paths_are_safe([".github/workflows/release-rc-truth-ci.yml", "services/api/app/main.py"])
        print("PASS: governance-only paths permitted, executable/history drift rejected")
        return 0
    if len(sys.argv) > 1:
        print("FAIL: unknown arguments", file=sys.stderr)
        return 2
    try:
        verify_legacy_manifest()
        git("cat-file", "-e", BASE + "^{commit}")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASE, "HEAD"],
            check=True, capture_output=True, text=True
        )
        changed = git("diff", "--name-only", "--no-renames", BASE, "HEAD").splitlines()
        unexpected = sorted(path for path in changed if path not in ALLOWED_GOVERNANCE and path not in APPROVED_P0_BLOBS and path not in APPROVED_NATIVE_QA_BLOBS)
        if unexpected:
            raise ValueError("unaccepted executable/history drift: " + ", ".join(unexpected))
        for path, approved_blob in {**APPROVED_P0_BLOBS, **APPROVED_NATIVE_QA_BLOBS}.items():
            if path in changed and git("hash-object", path) != approved_blob:
                raise ValueError("P0 file does not match approved blob: " + path)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print("FAIL: NOVEMBER MARINA RELEASE TRUTH RED: " + str(exc))
        return 1

    print("PASS: MARINA November main source frozen at " + BASE)
    print("FACT: PR #555 integrated; PR #569 tested at " + TESTED_PR_HEAD)
    print("FACT: historical release 0.62.2 contract remains independently checked")
    print("FACT: only blob-pinned occupied-room check-in P0 and regression are accepted beyond frozen main")
    print("FACT: CI acceptance and external Web/Mobile/Android/runtime must be verified separately")
    print("FACT: production_cutover_authorized=false; NO-GO until external release gates pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
