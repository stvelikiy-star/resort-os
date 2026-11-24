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
    ".github/workflows/marina-ios-simulator-keychain-linker-pilot-ci.yml": "0e4e2adf456706346760415f98f1e8e9a808bb96",
    ".github/workflows/marina-native-android-ios-maestro-ci.yml": "dc33e47bb732fe40f89f9d6a207d733ec313a0d8",
    "scripts/design/fl2-android-maestro-demo.sh": "b4372aa0fcb965a3d9337d86c2f4faf96db700c3",
    "scripts/design/fl2-native-live-role.yaml": "7bee19e1cc24b570a21bee7586577c9e00ed3c72",
    "scripts/design/fl2-native-live-dashboard.yaml": "51d2207ff63287cbb5f77dd3f02a5a0d2e254fa6",
    "scripts/design/fl2-native-live-role.sh": "3f182262269a0e50e7f177769eab8e9149ce5cc7",
    "scripts/design/fl2-native-live-role.README.md": "8e2e78527633902591c6fa56dd53b18afb9ab077",
    ".github/workflows/marina-native-live-qa-build-ci.yml": "144abd84c53bbd44375343f6071897a2535ffba2",
    "scripts/design/fl2-native-qa-connect.yaml": "f92d7e839c81f451bf2896b610f019541f9213c1",
    "scripts/design/fl2-native-qa-connect.sh": "b0df9bd280ac5b3deb5e6a5d5a5e34767cfb4ccb",
    ".github/workflows/marina-native-qa-negative-auth-ci.yml": "f0e1d3e6596ce8d1aaf5418365438a5878cdcd6c",
    "scripts/design/fl2-native-qa-negative-login.yaml": "5b93dac84c91b9279bd71b9772fb4c98f5b0e1eb",
    "scripts/design/fl2-native-qa-negative-login.sh": "95207036fe6d063f76d6f80b57f97182b0dfa5d4",
    ".github/workflows/marina-native-live-five-roles-ci.yml": "78391acf5b4dff5ebbb59f690ff8cde447ce23cf",
    "scripts/design/fl2-native-live-five-roles.sh": "979105718516bf2d70dc009a43725bf855447000",
}

APPROVED_P0_BLOBS = {
    "services/api/app/stays.py": "16f5a87445a9eaf9315b9b43e25d54c069bd69ce",
    "scripts/test_marina_pms_schedule_property_boundary.py": "701b21a7f74d4b1c210b6e89f65a95dfdd8d8771",
    "apps/staff/components/WaiterEntry.tsx": "939bf766588432200172b4d9f14fe96f0b13611b",
    # The additive RC3 gate is also pinned: immutable historical evidence
    # remains unchanged, only reviewed current-release additions are accepted.
    "scripts/marina_rc3_additive_gate.py": "8c405b6516851a6acd6f1a80b4d3fecc44cafb20",
    # PR #592: reviewed staging-only shared Staff operational routes and
    # two-hotel auth regression. Exact blob pins keep this exception fail-closed.
    "services/api/app/shared_auth_preview.py": "efb78195889db902fffc70df422f915fe6178409",
    "scripts/test_marina_shared_auth.py": "9c90ca127cba6c0eee2d22f0c6512bf586319509",
    "apps/staff/components/StoreStaffStock.tsx": "82b87098c1ab1355562551ec76cd8b4eb7b5478c",
    "apps/staff/components/StaffRoleGateway.tsx": "957821d21a17350529f9fcef442527772a42e0c9",
    # Reviewed P0 two-hotel OWNER financial facts, exact method-scoped routes,
    # and test-only workflow. No production shared-auth promotion.
    "scripts/marina_shared_owner_finance_p0_ci.py": "71cabedce521c0019a3fd900d075830d51891a13",
    # Full refund can only be recorded after external evidence; nothing is sent.
    "services/api/app/reservation_payments.py": "f7e533861624cd8a62fd29e81c7b0d73337717f3",
    "services/api/app/pms_reservation_create.py": "f068836d615409443f1742fc492f27886f9d6aee",
    "scripts/marina_shared_manual_refund_evidence_ci.py": "f52d7947e64e935497617834e17535def9a59042",
    "scripts/test_marina_finance_tenant_boundary.py": "4a4e796b2dc9d96a710d8e52aa087930aacc3045",
    "scripts/marina_shared_kitchen_cost_truth_ci.py": "e955a3cbd8a12ce76f8dd421bf1c277fe1cbde21",
    # Read-only production-to-served dish cost reconciliation, NOT booked COGS.
    "services/api/app/owner_served_kitchen_cost_trace.py": "d051cd2f1962fb4540434b026dec75e8c2afc6a7",
    "services/api/app/owner_accrual_readiness.py": "4d018cea0e9ffd3724594995dab4e91a76b5464f",
    "scripts/test_owner_served_kitchen_cost_trace.py": "c30f2859bd5769228c7cbcd1a1c6159797369abf",
    "scripts/marina_shared_served_cost_trace_ci.py": "0d8a608004d04fd6b4ad01f548da34fc59627385",
    "apps/admin/components/HotelFinanceBoard.tsx": "48472078d48cb3a707355f1fac36b46d02b80734",
    # MARINA batch provenance: reviewed additive migration, API and executable test.
    "scripts/release_contract.py": "30a001c5fc1eed727ff600f24d6c22bf2a5d0756",
    "services/api/app/app_entry.py": "088b69374b5b0e5ee3b86eab6cd59a8cf8f6642f",
    "services/api/app/kitchen_batch_allocation.py": "b02b46e4adffc29020fb3f9e60e89843bfbac346",
    "scripts/marina_shared_batch_allocation_ci.py": "4b1330ff2c6470f01b282715f6750bac6311826a",
    "packages/database/prisma/migrations/zz127_marina_served_batch_allocation_20261124/migration.sql": "36ccf6d1b520389c45f532a0e5477ce2021a6fc2",
    ".github/workflows/marina-shared-staff-lifecycle-p0-ci.yml": "24e9586d68e90e4292bb5f53f44d7fddeead7849",
    "apps/staff/components/WaiterEntry.module.css": "7218c412d73930418c4d703267bf83e5f8153c0e",
    "scripts/test_marina_staff_legacy_dining_preservation.py": "15fb8274b823c5dcb0842aa6be4ca585b85d05a5",
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
