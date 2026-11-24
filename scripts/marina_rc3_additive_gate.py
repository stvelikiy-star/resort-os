#!/usr/bin/env python3
"""Source gate for a NEW additive release without rewriting immutable RC3 evidence.

RC2/RC3 manifests remain 39-migration history. The current release must
preserve all 39 original SQL hashes and include pinned zz115 through zz126 SQL.
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
    "zz117_marina_kitchen_stock_20261111": "3cf125cb7b28d4961f0ca991f1685f2bc012628742d2e108ff868b520c825879",
    "zz118_marina_kitchen_waste_spoilage_20261115": "b7416f6882a1e438214c3dfe4340e29709f59a0f9fe89cc31828bcfbe5782061",
    "zz119_marina_kitchen_procurement_20261115": "8d1c8afe955d729c7a46d1c360445f0001308007c4b75447fa33348c84cc36f1",
    "zz120_marina_owner_expenses_20261115": "bcf6e97009c49e1b7a9ec82cb2ea597109e510455b32f2cc00141df76d1bf0f2",
    "zz121_marina_supplier_documents_20261116": "4fc7366e2979a5ef50abfc004c1efeb5da911f2d8db484e0b2795834b52e9f60",
    "zz122_marina_supplier_returns_20261116": "ae2c7b46a2acaa1e463805eee4aa5ef3554fa349414c12b9b570508757234f5d",
    "zz123_marina_owner_revenue_source_events_20261116": "0be3f00ad48d352f4edfae00f3ba6b41e793f20c45032ff94a914b566a36fe17",
    "zz124_marina_owner_revenue_corrections_20261116": "4741659b4f047682b8a87b8b475ec8c395ca0823b24481cac7d3081545b78621",
    "zz125_marina_owner_revenue_evidence_bytes_20261116": "37f7b3e12f8c10e0defcd8acb2fbc3d0cea63f55c008e19622b2bb363e5fd285",
    "zz126_marina_owner_accounting_journal_proposals_20261116": "1368d2ebba7902f1197c6151e97ccc1e7a4ed6d32070b0b6e6dffef1a1d13f42"
}
# Reviewed tightening: summary is trimmed and whitespace-only reports are rejected.
# Keep the historical RC3 manifest immutable; pin this additive source exactly.
TASK_REPORT_PATH = "services/api/app/staff_task_reports.py"
TASK_REPORT_BLOB = "3a874ddc986fd91a5537540ee808d192c4fd6144"
WORKFLOW_PATH = ".github/workflows/marina-shared-rc3-source-ci.yml"
# Approved current-release P0 (PR #592) is additive to immutable RC3.
# No historical manifest, RC3 gate, or original SQL hash is rewritten.
REVIEWED_SHARED_STAFF_P0_BLOBS = {
    "services/api/app/shared_auth_preview.py": "cb4acbe3083a5981f550f6f614d67bc4f2acb436",
    "scripts/test_marina_shared_auth.py": "61e7e68db81c4414436abb7f36f7d344e4ea3134",
    "apps/staff/components/StaffRoleGateway.tsx": "957821d21a17350529f9fcef442527772a42e0c9",
    "apps/staff/components/StoreStaffStock.tsx": "82b87098c1ab1355562551ec76cd8b4eb7b5478c",
    "scripts/marina_shared_owner_finance_p0_ci.py": "71cabedce521c0019a3fd900d075830d51891a13",
    # Reviewed evidence-only full refund: no external transfer, no partial refund.
    "services/api/app/reservation_payments.py": "fe9e0afb085f8343e073a4ba55c3d2b64efc070e",
    "scripts/marina_shared_manual_refund_evidence_ci.py": "6af069651da5bf9e0623cc886ff3c54deec3faff",
    ".github/workflows/marina-shared-staff-lifecycle-p0-ci.yml": "7edafcdff327fc84e56b47725449385204f5b5cc",
}
ALLOWED_LEGACY_ERRORS = frozenset({
    "Prisma migrations drift from frozen RC2 (name or content)",
    "reviewed critical source changed: " + TASK_REPORT_PATH,
    "reviewed critical source changed: " + WORKFLOW_PATH,
    "reviewed critical source changed: services/api/app/hotel_finance.py",
    "reviewed critical source changed: apps/admin/app/shared-auth-preview/page.tsx",
    "reviewed critical source changed: services/api/app/section_permissions.py",
    "reviewed critical source changed: scripts/test_marina_shared_auth.py",
    "reviewed critical source changed: services/api/app/shared_auth_preview.py",
    "reviewed critical source changed: services/api/app/reservation_payments.py",
})

def validate_additive() -> list[str]:
    errors: list[str] = []
    rc2 = json.loads((ROOT / RC2_FILE).read_text(encoding="utf8"))
    rc3 = json.loads((ROOT / RC3_FILE).read_text(encoding="utf8"))
    pinned = rc2.get("migration_sha256")
    if not isinstance(pinned, dict) or len(pinned) != 39:
        return ["historical RC2 expected 39 pinned migration hashes"]
    if len(EXPECTED_MIGRATIONS) != 51 or EXPECTED_MIGRATIONS[39:] != tuple(NEW_MIGRATIONS):
        errors.append("current release must contain exactly 39 historical + zz115 through zz126 migrations")
    expected = set(pinned) | set(NEW_MIGRATIONS)
    actual = {
        p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "packages/database/prisma/migrations").glob("*/migration.sql")
    }
    if set(actual) != expected or set(EXPECTED_MIGRATIONS) != expected:
        errors.append("new release migration set is not the approved additive 51")
    for name, sha in pinned.items():
        if actual.get(name) != sha:
            errors.append("historical RC2 migration drift: " + name)
    for name, sha in NEW_MIGRATIONS.items():
        if actual.get(name) != sha:
            errors.append("reviewed additive migration missing or changed: " + name)

    if git_blob_sha((ROOT / TASK_REPORT_PATH).read_bytes()) != TASK_REPORT_BLOB:
        errors.append("reviewed additive task report source changed")

    # Explicitly re-verify every new executable/blob exception. This keeps the
    # old RC3 evidence immutable and prevents broadening by path alone.
    for path, expected_blob in REVIEWED_SHARED_STAFF_P0_BLOBS.items():
        target = ROOT / path
        if not target.is_file() or git_blob_sha(target.read_bytes()) != expected_blob:
            errors.append("reviewed shared staff P0 blob mismatch: " + path)

    legacy_errors = validate(rc3, ROOT)
    for error in legacy_errors:
        if error not in ALLOWED_LEGACY_ERRORS:
            errors.append(error)
    # The historical source-gate file and the previous CI workflow remain
    # retrievable as pinned immutable Git blobs. The new workflow replaces
    # only how the current additive release is checked.
    for path in ("scripts/marina_rc3_source_gate.py", WORKFLOW_PATH, TASK_REPORT_PATH):
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
    print("MARINA_RC3_ADDITIVE_PASS: historical=39/39 immutable, new=zz115 through zz126, total=51, original source gate preserved, NO-GO")
