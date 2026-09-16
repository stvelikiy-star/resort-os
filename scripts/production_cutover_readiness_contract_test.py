#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from production_cutover_readiness import (
    MACHINE_GATES,
    MANUAL_REQUIRED_GATES,
    OWNER_GATE,
    command_plan,
    run_plan,
    validate_pre_owner_launch_manifest,
)
from production_endpoint_probe import Targets, parse_http_status_line, validate_targets
from release_contract import EXPECTED_MIGRATIONS

SHA = "1" * 40
NOW = "2026-09-16T06:00:00+00:00"


def gate(status: str, *, enabled: bool | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "evidence_ref": "evidence/test" if status == "VERIFIED" else None,
        "verified_at": NOW if status == "VERIFIED" else None,
    }
    if enabled is not None:
        payload["enabled"] = enabled
    return payload


def valid_launch_manifest() -> dict[str, object]:
    external: dict[str, object] = {}
    for name in sorted(MANUAL_REQUIRED_GATES):
        external[name] = gate("VERIFIED")
    for name in sorted(MACHINE_GATES):
        external[name] = gate("NOT_VERIFIED")
    external[OWNER_GATE] = gate("NOT_VERIFIED")
    external["provider_acceptance"] = gate("NOT_REQUIRED", enabled=False)
    return {
        "release": {"candidate_sha": SHA, "migrations": list(EXPECTED_MIGRATIONS)},
        "external_evidence": external,
    }


def assert_manifest_validation() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "launch.json"
        manifest = valid_launch_manifest()
        path.write_text(json.dumps(manifest), encoding="utf-8")
        _, errors = validate_pre_owner_launch_manifest(path, SHA)
        assert not errors, errors
        checks += 1

        broken = valid_launch_manifest()
        broken["external_evidence"]["github_branch_protection"] = gate("NOT_VERIFIED")  # type: ignore[index]
        path.write_text(json.dumps(broken), encoding="utf-8")
        _, errors = validate_pre_owner_launch_manifest(path, SHA)
        assert any("github_branch_protection" in item for item in errors)
        checks += 1

        broken = valid_launch_manifest()
        broken["external_evidence"][OWNER_GATE] = gate("VERIFIED")  # type: ignore[index]
        path.write_text(json.dumps(broken), encoding="utf-8")
        _, errors = validate_pre_owner_launch_manifest(path, SHA)
        assert any("owner_cutover_approval must remain NOT_VERIFIED" in item for item in errors)
        checks += 1

        broken = valid_launch_manifest()
        broken["external_evidence"]["provider_acceptance"] = gate("NOT_VERIFIED", enabled=True)  # type: ignore[index]
        path.write_text(json.dumps(broken), encoding="utf-8")
        _, errors = validate_pre_owner_launch_manifest(path, SHA)
        assert any("provider_acceptance" in item for item in errors)
        checks += 1

        broken = valid_launch_manifest()
        broken["release"]["candidate_sha"] = "2" * 40  # type: ignore[index]
        path.write_text(json.dumps(broken), encoding="utf-8")
        _, errors = validate_pre_owner_launch_manifest(path, SHA)
        assert any("candidate_sha mismatch" in item for item in errors)
        checks += 1
    return checks


def assert_target_validation() -> int:
    checks = 0
    valid = Targets(
        public_url="https://3korony.com",
        core_url="https://api.3korony.com",
        admin_url="https://admin.3korony.com",
        staff_url="https://staff.3korony.com",
        wss_url="wss://api.3korony.com/ws/pms/grid",
    )
    assert validate_targets(valid) == valid
    checks += 1
    assert parse_http_status_line(b"HTTP/1.1 403 Forbidden\r\n\r\n") == 403
    checks += 1
    for broken in (
        Targets("http://3korony.com", valid.core_url, valid.admin_url, valid.staff_url, valid.wss_url),
        Targets("https://example.com", valid.core_url, valid.admin_url, valid.staff_url, valid.wss_url),
        Targets(valid.public_url, valid.core_url, valid.admin_url, valid.staff_url, "wss://api.3korony.com/ws/other"),
    ):
        try:
            validate_targets(broken)
        except ValueError:
            checks += 1
        else:
            raise AssertionError("invalid production target was accepted")
    return checks


def assert_command_plan() -> int:
    checks = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        out = root / "out"
        out.mkdir()
        targets = Targets(
            public_url="https://3korony.com",
            core_url="https://api.3korony.com",
            admin_url="https://admin.3korony.com",
            staff_url="https://staff.3korony.com",
            wss_url="wss://api.3korony.com/ws/pms/grid",
        )
        plan = command_plan(
            release_sha=SHA,
            product_repo_root=root,
            rollback_evidence_dir="/e/legacy",
            dns_evidence_dir="/e/dns",
            backup_file="/e/db.dump",
            backup_manifest="/e/db.json",
            backup_offsite_dir="/offsite",
            restore_evidence="/e/restore.json",
            restore_owner="OWNER",
            compose_file="compose.beget.yaml",
            env_file="/srv/three-crowns/.env.production",
            backup_dir="/srv/three-crowns/backups",
            disk_path="/srv/three-crowns",
            targets=targets,
            output_dir=out,
        )
        names = [item[0] for item in plan]
        assert names == [
            "host_preflight",
            "release_rc_truth",
            "legacy_rollback_gate",
            "dns_rollback_gate",
            "pre_cutover_backup_gate",
            "deployment_release_linkage",
            "production_monitoring",
            "production_endpoint_probe",
            "external_public_truth",
        ]
        checks += 1
        flattened = "\n".join(" ".join(command) for _, command, _ in plan).lower()
        for forbidden in ("/unlock", "mkassa", "change-dns", "delete-domain", "owner_cutover_approval=verified"):
            assert forbidden not in flattened
            checks += 1
        assert "--require-offsite" in flattened and "--require-network" in flattened
        checks += 1
    return checks


def assert_fail_closed_execution() -> int:
    checks = 0
    plan = [
        ("one", ["one"], {}),
        ("two", ["two"], {}),
        ("three", ["three"], {}),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest: dict[str, object] = {"status": "RUNNING"}
        calls: list[str] = []

        def success(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
            calls.append(command[0])
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

        assert run_plan(plan=plan, output_dir=root, manifest=manifest, executor=success) == 0
        assert calls == ["one", "two", "three"]
        assert len(manifest["steps"]) == 3  # type: ignore[arg-type]
        checks += 1

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = {"status": "RUNNING"}
        calls = []

        def fail_second(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
            calls.append(command[0])
            code = 1 if command[0] == "two" else 0
            return subprocess.CompletedProcess(command, code, stdout="", stderr="failure\n" if code else "")

        assert run_plan(plan=plan, output_dir=root, manifest=manifest, executor=fail_second) == 1
        assert calls == ["one", "two"]
        assert manifest["status"] == "RED" and manifest["failed_step"] == "two"
        checks += 1
    return checks


def main() -> int:
    checks = 0
    checks += assert_manifest_validation()
    checks += assert_target_validation()
    checks += assert_command_plan()
    checks += assert_fail_closed_execution()
    assert checks >= 17
    print(f"PRODUCTION_CUTOVER_READINESS_CONTRACT_PASS checks={checks}")
    print("BOUNDARY: technical readiness only; DNS/provider activation and owner GO remain outside this gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
