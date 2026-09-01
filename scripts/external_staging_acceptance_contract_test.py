#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from external_staging_acceptance import (
    MUTATION_ACK,
    TargetSet,
    command_plan,
    prepare_output_dir,
    run_acceptance,
    validate_targets,
)

GOOD_SHA = "0123456789abcdef0123456789abcdef01234567"
TARGETS = TargetSet(
    public_url="https://staging.3korony.com",
    core_url="https://api-staging.3korony.com",
    admin_url="https://admin-staging.3korony.com",
    staff_url="https://staff-staging.3korony.com",
    ws_url="wss://api-staging.3korony.com",
)
EXPECTED_ORDER = [
    "legacy_rollback_gate",
    "deployment_release_linkage",
    "external_public_truth",
    "staging_business_acceptance",
    "production_monitoring",
]


def expect_value_error(label: str, fn, needle: str):
    try:
        fn()
    except ValueError as exc:
        assert needle in str(exc), f"{label}: {exc}"
    else:
        raise AssertionError(f"{label}: expected ValueError")


def build_plan(tmp: Path):
    return command_plan(
        expected_sha=GOOD_SHA,
        rollback_evidence_dir="/evidence/legacy",
        targets=validate_targets(TARGETS),
        compose_file="compose.beget.yaml",
        env_file=".env.production",
        backup_dir="/srv/three-crowns/backups",
        disk_path="/srv/three-crowns",
        release_linkage_output=str(tmp / "release-linkage.json"),
    )


def base_manifest():
    return {
        "schema_version": 1,
        "kind": "THREE_CROWNS_EXTERNAL_STAGING_ACCEPTANCE",
        "status": "RUNNING",
        "expected_sha": GOOD_SHA,
    }


def main() -> int:
    validated = validate_targets(TARGETS)
    assert validated.core_url == TARGETS.core_url

    expect_value_error(
        "production public hostname",
        lambda: validate_targets(TargetSet(
            public_url="https://3korony.com",
            core_url=TARGETS.core_url,
            admin_url=TARGETS.admin_url,
            staff_url=TARGETS.staff_url,
            ws_url=TARGETS.ws_url,
        )),
        "hostname must explicitly contain staging",
    )
    expect_value_error(
        "http core",
        lambda: validate_targets(TargetSet(
            public_url=TARGETS.public_url,
            core_url="http://api-staging.3korony.com",
            admin_url=TARGETS.admin_url,
            staff_url=TARGETS.staff_url,
            ws_url=TARGETS.ws_url,
        )),
        "HTTPS URL",
    )
    expect_value_error(
        "credentials in admin URL",
        lambda: validate_targets(TargetSet(
            public_url=TARGETS.public_url,
            core_url=TARGETS.core_url,
            admin_url="https://user:pass@admin-staging.3korony.com",
            staff_url=TARGETS.staff_url,
            ws_url=TARGETS.ws_url,
        )),
        "must not contain credentials",
    )
    expect_value_error(
        "non-WSS websocket",
        lambda: validate_targets(TargetSet(
            public_url=TARGETS.public_url,
            core_url=TARGETS.core_url,
            admin_url=TARGETS.admin_url,
            staff_url=TARGETS.staff_url,
            ws_url="ws://api-staging.3korony.com",
        )),
        "WSS URL",
    )

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        evidence = prepare_output_dir(tmp / "evidence")
        plan = build_plan(evidence)
        assert [name for name, _, _ in plan] == EXPECTED_ORDER
        smoke = next(item for item in plan if item[0] == "staging_business_acceptance")
        assert smoke[2]["APP_ENV"] == "staging"
        assert smoke[2]["STAGING_ACCEPTANCE_MUTATIONS"] == MUTATION_ACK
        assert smoke[2]["CORE_API_URL"] == TARGETS.core_url
        assert smoke[2]["CORE_WS_URL"] == TARGETS.ws_url
        monitor_cmd = next(item[1] for item in plan if item[0] == "production_monitoring")
        assert "--require-offsite" in monitor_cmd
        assert "--require-network" in monitor_cmd
        assert "core=https://api-staging.3korony.com/health/ready" in monitor_cmd

        calls: list[str] = []
        def green_executor(command: list[str], env: dict[str, str]):
            name = next(name for name, cmd, _ in plan if cmd == command)
            calls.append(name)
            return subprocess.CompletedProcess(command, 0, stdout=f"{name}=GREEN\n", stderr="")

        manifest = base_manifest()
        rc = run_acceptance(plan=plan, output_dir=evidence, manifest=manifest, executor=green_executor)
        assert rc == 0
        assert calls == EXPECTED_ORDER
        saved = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        assert saved["status"] == "GREEN"
        assert [item["name"] for item in saved["steps"]] == EXPECTED_ORDER
        for item in saved["steps"]:
            assert item["status"] == "GREEN"
            for stream in ("stdout", "stderr"):
                spec = item[stream]
                assert len(spec["sha256"]) == 64
                assert (evidence / spec["path"]).is_file()

    with tempfile.TemporaryDirectory() as tmp_raw:
        evidence = prepare_output_dir(Path(tmp_raw) / "evidence")
        plan = build_plan(evidence)
        calls = []
        def red_executor(command: list[str], env: dict[str, str]):
            name = next(name for name, cmd, _ in plan if cmd == command)
            calls.append(name)
            rc = 9 if name == "external_public_truth" else 0
            return subprocess.CompletedProcess(command, rc, stdout=f"{name}\n", stderr="synthetic failure\n" if rc else "")

        manifest = base_manifest()
        rc = run_acceptance(plan=plan, output_dir=evidence, manifest=manifest, executor=red_executor)
        assert rc == 1
        assert calls == EXPECTED_ORDER[:3], calls
        saved = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        assert saved["status"] == "RED"
        assert saved["failed_step"] == "external_public_truth"
        assert len(saved["steps"]) == 3

    with tempfile.TemporaryDirectory() as tmp_raw:
        path = Path(tmp_raw) / "evidence"
        path.mkdir()
        (path / "old.txt").write_text("old evidence", encoding="utf-8")
        expect_value_error(
            "non-empty evidence directory",
            lambda: prepare_output_dir(path),
            "must be empty",
        )

    print("PASS: external staging acceptance orchestration adversarial contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
