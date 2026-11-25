#!/usr/bin/env python3
"""Source gate for a NEW additive release without rewriting immutable RC3 evidence.

RC2/RC3 manifests remain 39-migration history. The current release must
preserve all 39 original SQL hashes and include pinned zz115 through zz137 SQL.
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
    "zz126_marina_owner_accounting_journal_proposals_20261116": "1368d2ebba7902f1197c6151e97ccc1e7a4ed6d32070b0b6e6dffef1a1d13f42",
    "zz127_marina_served_batch_allocation_20261124": "95bac1119041a5eb816977c4824eea719dbb5a95da99c6e5615b5ca1dd771df3",
    "zz128_marina_owner_accounting_decision_evidence_20261124": "a2b611bdc28bee0e56c0db084f469fe0ef9a23f3960ed8ca995fcbf9f0735ec6",
    "zz129_marina_owner_accounting_postings_20261125": "775329b35e5e5128afd6e13a74d9b040fdc102be58c5c79e13640649945d1fdb",
    "zz130_marina_owner_revenue_accounting_certification_20261125": "1287bb02ba19d1a30fef5dcc53c5ec786b572cb3c5a12bcc588dc469da741c7e",
    "zz131_marina_owner_source_reversal_integrity_20261125": "6f74b46833e78fbbf02fced5cb0a8564f7a2bdad6eedf74445f4fd9d0d52af11",
    "zz132_marina_owner_revenue_period_integrity_20261125": "0a6084420b707d8741eaec61141c1a1fa3a03ddac0460b327452c3cc009ad179",
    "zz133_marina_owner_guest_service_revenue_20261125": "487ff0ccc1b1a46804c5de2b153dd3e95c921002ce27eea49d1840b16fb465d6",
    "zz134_marina_owner_guest_service_posting_lifecycle_20261125": "bb1e57baa2cac2c4e94c294a229b67fc98e7597486c022c265f8f3cd8c9b4621",
    "zz135_marina_owner_certified_tax_correction_20261125": "9f3239acbfa138c2c9e63a98e43875d5ad6a127cbe1cb5b43b2247edcedbb152",
    "zz136_marina_owner_certified_revenue_reductions_20261125": "e9c640033403f30b80be77a7aeede6caec3ce01d034f83bbf171603dd5c14b67",
    "zz137_marina_owner_certified_refund_cash_evidence_20261125": "0f1b18a74bf2cecea5cecf301dea4dc8835bdc3b20e6d300b95f443aafec2837"
}
# Reviewed tightening: summary is trimmed and whitespace-only reports are rejected.
# Keep the historical RC3 manifest immutable; pin this additive source exactly.
TASK_REPORT_PATH = "services/api/app/staff_task_reports.py"
TASK_REPORT_BLOB = "3a874ddc986fd91a5537540ee808d192c4fd6144"
WORKFLOW_PATH = ".github/workflows/marina-shared-rc3-source-ci.yml"
# Reviewed MARINA SMART staged additions are additive to immutable RC3.
# No historical manifest, RC3 gate, or original SQL hash is rewritten.
REVIEWED_SHARED_STAFF_P0_BLOBS = {
    "services/api/app/shared_auth_preview.py": "cb4acbe3083a5981f550f6f614d67bc4f2acb436",
    "scripts/test_marina_shared_auth.py": "edb42395111dbd19fe2e3e3facaa9ff4d4cfe39e",
    "apps/staff/components/StaffRoleGateway.tsx": "957821d21a17350529f9fcef442527772a42e0c9",
    "apps/staff/components/StoreStaffStock.tsx": "82b87098c1ab1355562551ec76cd8b4eb7b5478c",
    "scripts/marina_shared_owner_finance_p0_ci.py": "71cabedce521c0019a3fd900d075830d51891a13",
    # Reviewed evidence-only full refund: no external transfer, no partial refund.
    "services/api/app/reservation_payments.py": "f7e533861624cd8a62fd29e81c7b0d73337717f3",
    "services/api/app/pms_reservation_create.py": "f068836d615409443f1742fc492f27886f9d6aee",
    "scripts/marina_shared_manual_refund_evidence_ci.py": "f52d7947e64e935497617834e17535def9a59042",
    "scripts/test_marina_finance_tenant_boundary.py": "4a4e796b2dc9d96a710d8e52aa087930aacc3045",
    "scripts/marina_shared_kitchen_cost_truth_ci.py": "da7a8f7dc0719fad59482b3312c22aeef22a60f0",
    "services/api/app/owner_served_kitchen_cost_trace.py": "848956bbe269623462b8979381baad86555b2f36",
    "services/api/app/owner_accrual_readiness.py": "a6484821beaae10aa3f3de3bbf5011e38389872f",
    "scripts/test_owner_served_kitchen_cost_trace.py": "c30f2859bd5769228c7cbcd1a1c6159797369abf",
    "scripts/marina_shared_served_cost_trace_ci.py": "0d8a608004d04fd6b4ad01f548da34fc59627385",
    "apps/admin/components/AdminExperienceRuntime.tsx": "aeecbcd54bd3479ba80e541e31f884cf7ba2870d",
    "services/api/app/hotel_finance.py": "f11fba20ea217fea3b2f075f39ddb4f2de907e6a",
    "apps/mobile/scripts/verify-backend-contract.mjs": "913a486146cd599c92e11dbc590906e9ba8a867f",
    "apps/mobile/app/finance.tsx": "4434075da2ed4f891d7d238d606e03783dd9b1dc",
    "apps/mobile/src/api/liveModules.ts": "3b953a3a9caafb85397fe2ea5d8425bc737e9b86",
    "apps/mobile/src/api/contractValidation.ts": "bb4b0325bac08c6a362181e6e58a4306fd4d7dfc",
    "apps/mobile/__tests__/owner-accrual-readiness.test.ts": "70f981613d914bf8b9c433ce2b2cbfd771d88059",
    "apps/admin/components/HotelFinanceBoard.tsx": "eea0633c6fb63c600ebca4bd290ec52cf994f56f",
    "apps/staff/components/CookBatchAssignments.tsx": "884a3290e678f8777167999e5aceaa60d470902b",
    "apps/staff/components/SharedDiningShift.tsx": "193b5a27d698a89914433cffa3a22d798fb2b285",
    # MARINA-specific 52nd migration, exact batch-to-served item ledger.
    "scripts/marina_shared_three_hotel_restore_ci.py": "0f00022721637c58d3897f5164496af7173e37dd",
    "scripts/release_contract.py": "194292383b34b647e0db8374d25167ad3b1b93cd",
    "scripts/release_contract_test.py": "9b943cc2afd21f83ce9eda4ab3387e485fdd1ebf",
    ".github/workflows/marina-zz113-rollback-ci.yml": "38c9cbac9c6e8081553f4f9310b10656a28af0c1",
    "scripts/marina_disposable_upgrade_acceptance_ci.py": "b877c5976def9451853953b86ec48b6804ab16b0",
    ".github/workflows/marina-564-legacy-upgrade-acceptance-ci.yml": "9bf375ac39d02cf78122dbe4544f1d69d3335cb6",
    "services/api/app/app_entry.py": "8b8e630073ddbe6a8855a5494116c5cac11064ca",
    "services/api/app/shared_auth_preview.py": "22d59980e7bf38531ea887b62e64f08a179f9067",
    "services/api/app/kitchen_batch_allocation.py": "21f71b7bd7d7a6c4aa2b044b4617a4547a16be47",
    "services/api/app/owner_served_kitchen_cost_trace.py": "d051cd2f1962fb4540434b026dec75e8c2afc6a7",
    "scripts/marina_shared_batch_allocation_ci.py": "9db3435b5ac282ba058b49ecd15ee5f0d8a51752",
    "scripts/marina_owner_accounting_decision_ci.py": "4b84740d89e497f976accaa6da3da082129e349e",
    "services/api/app/owner_accounting_journal.py": "bfadba59080ec2badb554ee03ed39d964cb04c0e",
    "services/api/app/owner_recognition_policy.py": "b379a397c079581bdbeef843c76374fa67250209",
    "services/api/app/owner_ledger_policy.py": "5489152a7cf19737932a4413c9e446afa62b69e4",
    "services/api/app/owner_accounting_postings.py": "d0ba5bf21facfb7683e5af013fdf15121579e7bf",
    "services/api/app/owner_revenue_corrections.py": "10f52e7f916598620c73fa2d3a61f08bed435aaa",
    "services/api/app/owner_delivered_revenue.py": "1e8881079cd4d4a64f96aaabbb51c1d21e59a035",
    "scripts/test_owner_ledger_policy.py": "c8de02aff23a49ac33c21c314353a386d3e73879",
    "scripts/marina_owner_posting_api_ci.py": "7e19cc3878471554bed2c0fa80df964dee042d83",
    "services/api/app/owner_revenue_source_journal.py": "a748840fcce9904dbb4e52fe20c9ff6163bd9375",
    "scripts/marina_owner_expense_posting_ci.py": "3c5879734d3bff96269559b1aa08e25adfe937c2",
    "scripts/marina_owner_served_cogs_posting_ci.py": "75bb2cc1fb85ff6379ec0b8010115a4aad6b290b",
    "scripts/test_owner_recognition_policy.py": "7a856095b84319c654c9b536f763e1d763cf790a",
    ".github/workflows/marina-owner-recognition-policy-ci.yml": "7965e38127aaf6a9ffe73f0c0ce755425d36d6e1",
    "scripts/test_owner_accounting_decision_evidence.py": "fcc8c6f8f9da2496ae39d7d7ffdf960a093f9a89",
    ".github/workflows/marina-shared-staff-lifecycle-p0-ci.yml": "991f743e639637c6d829bdb6b4e35926c40f6195",
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
    "reviewed critical source changed: services/api/app/pms_reservation_create.py",
    "reviewed critical source changed: services/api/app/owner_accrual_readiness.py",
    "reviewed critical source changed: services/api/app/app_entry.py",
    "reviewed critical source changed: scripts/release_contract.py",
})

def validate_additive() -> list[str]:
    errors: list[str] = []
    rc2 = json.loads((ROOT / RC2_FILE).read_text(encoding="utf8"))
    rc3 = json.loads((ROOT / RC3_FILE).read_text(encoding="utf8"))
    pinned = rc2.get("migration_sha256")
    if not isinstance(pinned, dict) or len(pinned) != 39:
        return ["historical RC2 expected 39 pinned migration hashes"]
    if len(EXPECTED_MIGRATIONS) != 62 or EXPECTED_MIGRATIONS[39:] != tuple(NEW_MIGRATIONS):
        errors.append("current release must contain exactly 39 historical + zz115 through zz137 migrations")
    expected = set(pinned) | set(NEW_MIGRATIONS)
    actual = {
        p.parent.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "packages/database/prisma/migrations").glob("*/migration.sql")
    }
    if set(actual) != expected or set(EXPECTED_MIGRATIONS) != expected:
        errors.append("new release migration set is not the approved additive 62")
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
    print("MARINA_RC3_ADDITIVE_PASS: historical=39/39 immutable, new=zz115 through zz137, total=62, original source gate preserved, NO-GO")
