#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from release_contract import EXPECTED_MIGRATIONS
from verify_launch_acceptance import REQUIRED_EXTERNAL_GATES, validate_manifest


def verified_gate() -> dict:
    return {
        "status": "VERIFIED",
        "evidence_ref": "evidence://test/non-secret-reference",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def complete_manifest() -> dict:
    external = {name: verified_gate() for name in REQUIRED_EXTERNAL_GATES}
    external["provider_acceptance"] = {
        "enabled": False,
        "status": "NOT_REQUIRED",
        "evidence_ref": None,
        "verified_at": None,
    }
    return {
        "release": {
            "candidate_sha": "a" * 40,
            "migrations": list(EXPECTED_MIGRATIONS),
        },
        "external_evidence": external,
    }


def main() -> None:
    valid = complete_manifest()
    assert validate_manifest(valid, expected_sha="a" * 40) == []

    wrong_sha = deepcopy(valid)
    assert any("candidate_sha mismatch" in item for item in validate_manifest(wrong_sha, expected_sha="b" * 40))

    missing_room_reconciliation = deepcopy(valid)
    missing_room_reconciliation["external_evidence"]["room_reconciliation"] = {
        "status": "NOT_VERIFIED",
        "evidence_ref": None,
        "verified_at": None,
    }
    errors = validate_manifest(missing_room_reconciliation, expected_sha="a" * 40)
    assert any("room_reconciliation: production cutover remains STOP" in item for item in errors)

    obsolete_room_questionnaire_gate = deepcopy(valid)
    obsolete_room_questionnaire_gate["external_evidence"]["owner_room_register"] = verified_gate()
    errors = validate_manifest(obsolete_room_questionnaire_gate, expected_sha="a" * 40)
    assert any("owner_room_register is obsolete" in item for item in errors)

    provider_enabled_without_evidence = deepcopy(valid)
    provider_enabled_without_evidence["external_evidence"]["provider_acceptance"] = {
        "enabled": True,
        "status": "NOT_VERIFIED",
        "evidence_ref": None,
        "verified_at": None,
    }
    errors = validate_manifest(provider_enabled_without_evidence, expected_sha="a" * 40)
    assert any("launch-enabled providers require VERIFIED evidence" in item for item in errors)

    missing_evidence_ref = deepcopy(valid)
    missing_evidence_ref["external_evidence"]["beget_host_preflight"]["evidence_ref"] = ""
    errors = validate_manifest(missing_evidence_ref, expected_sha="a" * 40)
    assert any("beget_host_preflight: VERIFIED requires evidence_ref" in item for item in errors)

    bad_ledger = deepcopy(valid)
    bad_ledger["release"]["migrations"] = list(EXPECTED_MIGRATIONS[:-1])
    errors = validate_manifest(bad_ledger, expected_sha="a" * 40)
    assert any("must exactly match canonical release contract" in item for item in errors)

    print("LAUNCH_ACCEPTANCE_VERIFIER_TEST_OK")


if __name__ == "__main__":
    main()
