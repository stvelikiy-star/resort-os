#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from release_contract import EXPECTED_MIGRATIONS

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_STATUS = {"VERIFIED", "NOT_VERIFIED", "NOT_REQUIRED"}
REQUIRED_EXTERNAL_GATES = (
    "room_reconciliation",
    "beget_host_preflight",
    "legacy_rollback_backup",
    "external_https_wss_staging",
    "external_public_truth_probe",
    "real_device_acceptance",
    "monitoring_alerting",
    "pre_cutover_backup",
    "dns_rollback_capture",
    "owner_cutover_approval",
)
OPTIONAL_EXTERNAL_GATES = ("provider_acceptance",)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_gate(name: str, gate: Any, errors: list[str]) -> None:
    if not isinstance(gate, dict):
        errors.append(f"{name}: gate must be an object")
        return
    status = gate.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"{name}: invalid status {status!r}")
        return
    if status == "VERIFIED":
        evidence_ref = str(gate.get("evidence_ref") or "").strip()
        verified_at = str(gate.get("verified_at") or "").strip()
        if not evidence_ref:
            errors.append(f"{name}: VERIFIED requires evidence_ref")
        if not verified_at:
            errors.append(f"{name}: VERIFIED requires verified_at")
        else:
            try:
                if parse_time(verified_at) > datetime.now(timezone.utc):
                    errors.append(f"{name}: verified_at cannot be in the future")
            except (ValueError, TypeError):
                errors.append(f"{name}: verified_at must be ISO-8601")


def validate_manifest(manifest: dict[str, Any], expected_sha: str | None = None) -> list[str]:
    errors: list[str] = []
    release = manifest.get("release")
    if not isinstance(release, dict):
        return ["release must be an object"]

    candidate_sha = str(release.get("candidate_sha") or "").strip().lower()
    if not SHA_RE.fullmatch(candidate_sha):
        errors.append("release.candidate_sha must be an exact 40-char lowercase Git SHA")
    if expected_sha and candidate_sha != expected_sha.lower():
        errors.append(f"release.candidate_sha mismatch: expected {expected_sha.lower()}, found {candidate_sha}")

    migrations = release.get("migrations")
    if migrations != list(EXPECTED_MIGRATIONS):
        errors.append(
            "release.migrations must exactly match canonical release contract: "
            + ", ".join(EXPECTED_MIGRATIONS)
        )

    external = manifest.get("external_evidence")
    if not isinstance(external, dict):
        return errors + ["external_evidence must be an object"]

    if "owner_room_register" in external:
        errors.append(
            "external_evidence.owner_room_register is obsolete: physical room import gate #38 is closed; use room_reconciliation for real target evidence"
        )

    for name in REQUIRED_EXTERNAL_GATES + OPTIONAL_EXTERNAL_GATES:
        if name not in external:
            errors.append(f"external_evidence.{name} is required")
            continue
        validate_gate(name, external[name], errors)

    provider = external.get("provider_acceptance")
    if isinstance(provider, dict):
        enabled = bool(provider.get("enabled"))
        status = provider.get("status")
        if enabled and status != "VERIFIED":
            errors.append("provider_acceptance: launch-enabled providers require VERIFIED evidence")
        if not enabled and status not in {"NOT_REQUIRED", "VERIFIED"}:
            errors.append("provider_acceptance: disabled providers must be NOT_REQUIRED or VERIFIED")

    for name in REQUIRED_EXTERNAL_GATES:
        gate = external.get(name)
        if isinstance(gate, dict) and gate.get("status") != "VERIFIED":
            errors.append(f"{name}: production cutover remains STOP until VERIFIED")

    return errors


def repository_checks(root: Path) -> list[str]:
    errors: list[str] = []
    current_state = (root / "knowledge" / "04_CURRENT_STATE.md").read_text(encoding="utf-8")
    runbook = (root / "docs" / "DEPLOYMENT_RUNBOOK.md").read_text(encoding="utf-8")
    migration_doc = (root / "docs" / "PRODUCTION_DATABASE_MIGRATIONS.md").read_text(encoding="utf-8")
    example = json.loads((root / "release" / "launch-evidence.example.json").read_text(encoding="utf-8"))

    canonical_docs = {
        "knowledge/04_CURRENT_STATE.md": current_state,
        "docs/DEPLOYMENT_RUNBOOK.md": runbook,
        "docs/PRODUCTION_DATABASE_MIGRATIONS.md": migration_doc,
    }
    joined = "\n".join(canonical_docs.values())
    stale_fragments = (
        "exact five-migration ledger",
        "all five migrations",
        "apply all five committed migrations",
        "baseline SQL itself is **not yet committed/executed/verified**",
        "Persisted canonical Stay, generic tenancy",
        "PR #37",
        "1be110c35e1e7d5876cae40a1b58cef42bd10a22",
        "91699f70f774726eb61a9882ccbdfe5944471856",
        "owner-approved physical 84-room production register",
        "final owner-approved physical 84-room register",
    )
    for fragment in stale_fragments:
        if fragment in joined:
            errors.append(f"stale release statement remains in canonical docs: {fragment}")

    for path, content in canonical_docs.items():
        for migration in EXPECTED_MIGRATIONS:
            if migration not in content:
                errors.append(f"{path} must include migration {migration}")

    if "27" not in migration_doc or "scripts/release_contract.py" not in migration_doc:
        errors.append("production migration documentation must reference the current shared 27-constraint release contract")

    manifest_errors = validate_manifest(example)
    structural_errors = [
        item
        for item in manifest_errors
        if "production cutover remains STOP" not in item
        and "disabled providers must" not in item
        and "launch-enabled providers require" not in item
    ]
    if structural_errors:
        errors.extend(f"example manifest: {item}" for item in structural_errors)
    if not any("production cutover remains STOP" in item for item in manifest_errors):
        errors.append("example launch manifest must remain fail-closed until real evidence is supplied")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Three Crowns launch acceptance verifier")
    parser.add_argument("--mode", choices=("repository", "cutover"), required=True)
    parser.add_argument("--manifest", default="release/launch-evidence.example.json")
    parser.add_argument("--release-sha")
    args = parser.parse_args()

    if args.mode == "repository":
        errors = repository_checks(Path.cwd())
        if errors:
            for item in errors:
                print(f"FAIL: {item}")
            print("RESULT: RELEASE REPOSITORY NOT READY")
            return 1
        print(f"FACT: migrations={len(EXPECTED_MIGRATIONS)}")
        print("FACT: physical_room_import_gate_38=closed")
        print("FACT: launch_example_is_fail_closed=true")
        print("RESULT: RELEASE REPOSITORY READY; EXTERNAL CUTOVER NOT AUTHORIZED")
        return 0

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    errors = validate_manifest(manifest, expected_sha=args.release_sha)
    if errors:
        for item in errors:
            print(f"FAIL: {item}")
        print("RESULT: PRODUCTION CUTOVER STOP")
        return 1
    print("RESULT: STRUCTURAL LAUNCH EVIDENCE COMPLETE")
    print("NOTE: this verifier validates supplied evidence metadata; it does not manufacture or independently observe external evidence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
