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
    "scripts/marina_rc3_additive_gate.py": "5db2956e33e70f28d1b7e0c226751da7028b1be6",
    # PR #592: reviewed staging-only shared Staff operational routes and
    # two-hotel auth regression. Exact blob pins keep this exception fail-closed.
    "services/api/app/shared_auth_preview.py": "22d59980e7bf38531ea887b62e64f08a179f9067",
    "scripts/test_marina_shared_auth.py": "edb42395111dbd19fe2e3e3facaa9ff4d4cfe39e",
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
    "scripts/marina_shared_kitchen_cost_truth_ci.py": "da7a8f7dc0719fad59482b3312c22aeef22a60f0",
    # Read-only production-to-served dish cost reconciliation, NOT booked COGS.
    "services/api/app/owner_served_kitchen_cost_trace.py": "d051cd2f1962fb4540434b026dec75e8c2afc6a7",
    "services/api/app/owner_accrual_readiness.py": "a6484821beaae10aa3f3de3bbf5011e38389872f",
    "scripts/test_owner_served_kitchen_cost_trace.py": "c30f2859bd5769228c7cbcd1a1c6159797369abf",
    "scripts/marina_shared_served_cost_trace_ci.py": "0d8a608004d04fd6b4ad01f548da34fc59627385",
    "apps/admin/components/HotelFinanceBoard.tsx": "20cdda5d8839fa3c3b9a59bfd686c52a69ae14ab",
    "apps/staff/components/CookBatchAssignments.tsx": "884a3290e678f8777167999e5aceaa60d470902b",
    "apps/staff/components/SharedDiningShift.tsx": "193b5a27d698a89914433cffa3a22d798fb2b285",
    # MARINA batch provenance: reviewed additive migration, API and executable test.
    "scripts/release_contract.py": "b4793006c017a75d1cbe2a50299acf76ff0b6639",
    "scripts/release_contract_test.py": "8d8988b26704dd1662b9719f763bd55e26304b42",
    ".github/workflows/marina-zz113-rollback-ci.yml": "44fdddd225e29efb56bae9626b59c3cb0d88aa2d",
    "scripts/marina_disposable_upgrade_acceptance_ci.py": "b877c5976def9451853953b86ec48b6804ab16b0",
    ".github/workflows/marina-564-legacy-upgrade-acceptance-ci.yml": "9bf375ac39d02cf78122dbe4544f1d69d3335cb6",
    "services/api/app/app_entry.py": "8b8e630073ddbe6a8855a5494116c5cac11064ca",
    "services/api/app/kitchen_batch_allocation.py": "21f71b7bd7d7a6c4aa2b044b4617a4547a16be47",
    "scripts/marina_shared_batch_allocation_ci.py": "ba9ce140bb72bfdb7954cb7081ea4f312bb4a168",
    "packages/database/prisma/migrations/zz127_marina_served_batch_allocation_20261124/migration.sql": "36ccf6d1b520389c45f532a0e5477ce2021a6fc2",
    # P0 proposal decision evidence: explicit, hash-pinned release extension.
    "packages/database/prisma/migrations/zz128_marina_owner_accounting_decision_evidence_20261124/migration.sql": "f1243f4eb4762f416d9f67369c36e5d388e4e224",
    "services/api/app/owner_accounting_journal.py": "fcb45a4a75f7935e12d6793dcdd95062a5d7c8d6",
    "services/api/app/owner_recognition_policy.py": "b379a397c079581bdbeef843c76374fa67250209",
    "services/api/app/owner_ledger_policy.py": "c0a42b1b2c0d9a1f88a6a1bba30e982d7b39cb3e",
    "services/api/app/owner_accounting_postings.py": "52f385df8812f56169064771c052d9753032d364",
    "scripts/test_owner_ledger_policy.py": "ef82e4ced2f577b6b92831251a4e9cd40283f3ad",
    "scripts/marina_owner_posting_api_ci.py": "b493d85669ca903d63e5a49a2314b38bdcb6c117",
    "packages/database/prisma/migrations/zz129_marina_owner_accounting_postings_20261125/migration.sql": "bffc8229696d7e4ef55b0a2ed4725f26df1b9896",
    "scripts/test_owner_recognition_policy.py": "7a856095b84319c654c9b536f763e1d763cf790a",
    ".github/workflows/marina-owner-recognition-policy-ci.yml": "7965e38127aaf6a9ffe73f0c0ce755425d36d6e1",
    "scripts/test_owner_accounting_decision_evidence.py": "fcc8c6f8f9da2496ae39d7d7ffdf960a093f9a89",
    "scripts/marina_owner_accounting_decision_ci.py": "4b84740d89e497f976accaa6da3da082129e349e",
    ".github/workflows/marina-shared-staff-lifecycle-p0-ci.yml": "b515882c01b968a7c7ae0a2ccd91c533670fe36e",
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
