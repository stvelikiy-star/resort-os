#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from production_endpoint_probe import Targets, validate_targets
from verify_launch_acceptance import validate_manifest

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MACHINE_GATES = {
    "beget_host_preflight",
    "legacy_rollback_backup",
    "external_public_truth_probe",
    "monitoring_alerting",
    "pre_cutover_backup",
    "dns_rollback_capture",
}
MANUAL_REQUIRED_GATES = {
    "github_branch_protection",
    "drive_launch_control_permissions",
    "room_reconciliation",
    "external_https_wss_staging",
    "real_device_acceptance",
}
OWNER_GATE = "owner_cutover_approval"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_sha(value: str) -> str:
    normalized = value.strip().lower()
    if not SHA_RE.fullmatch(normalized):
        raise ValueError("release SHA must be an exact 40-character lowercase Git SHA")
    return normalized


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError("output path exists and is not a directory")
        if any(resolved.iterdir()):
            raise ValueError("output directory must be empty")
    else:
        resolved.mkdir(parents=True, mode=0o700)
    return resolved


def write_log(path: Path, text: str) -> dict[str, Any]:
    path.write_text(text, encoding="utf-8")
    return {"path": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def safe_manifest_write(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(path)


def validate_pre_owner_launch_manifest(path: Path, expected_sha: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"cannot read launch manifest: {exc}"]
    if not isinstance(manifest, dict):
        return {}, ["launch manifest must be a JSON object"]

    all_errors = validate_manifest(manifest, expected_sha=expected_sha)
    ignored_stop_errors = {
        f"{name}: production cutover remains STOP until VERIFIED"
        for name in MACHINE_GATES | {OWNER_GATE}
    }
    errors.extend(item for item in all_errors if item not in ignored_stop_errors)

    external = manifest.get("external_evidence")
    if not isinstance(external, dict):
        return manifest, errors or ["external_evidence must be an object"]

    for name in sorted(MANUAL_REQUIRED_GATES):
        gate = external.get(name)
        if not isinstance(gate, dict) or gate.get("status") != "VERIFIED":
            errors.append(f"{name}: manual/external prerequisite must already be VERIFIED")

    owner = external.get(OWNER_GATE)
    if not isinstance(owner, dict) or owner.get("status") != "NOT_VERIFIED":
        errors.append("owner_cutover_approval must remain NOT_VERIFIED until this technical readiness gate is complete")

    provider = external.get("provider_acceptance")
    if isinstance(provider, dict) and bool(provider.get("enabled")) and provider.get("status") != "VERIFIED":
        errors.append("provider_acceptance: enabled provider must already be VERIFIED")

    return manifest, errors


def runtime_compose_path(product_repo_root: Path, compose_file: str) -> str:
    candidate = Path(compose_file)
    return str(candidate.resolve() if candidate.is_absolute() else (product_repo_root / candidate).resolve())


def command_plan(
    *,
    release_sha: str,
    product_repo_root: Path,
    rollback_evidence_dir: str,
    dns_evidence_dir: str,
    backup_file: str,
    backup_manifest: str,
    backup_offsite_dir: str,
    restore_evidence: str,
    restore_owner: str,
    compose_file: str,
    env_file: str | None,
    backup_dir: str,
    disk_path: str,
    targets: Targets,
    output_dir: Path,
) -> list[tuple[str, list[str], dict[str, str]]]:
    python = sys.executable
    compose = runtime_compose_path(product_repo_root, compose_file)
    env_path = str(Path(env_file).expanduser().resolve()) if env_file else None

    linkage = [
        python,
        "scripts/deployment_release_linkage.py",
        "--expected-sha",
        release_sha,
        "--repo-root",
        str(product_repo_root),
        "--compose-file",
        compose,
        "--output",
        str(output_dir / "deployment-release-linkage.json"),
    ]
    if env_path:
        linkage += ["--env-file", env_path]

    monitoring = [
        python,
        "scripts/production_monitoring_check.py",
        "--compose-file",
        compose,
        "--backup-dir",
        backup_dir,
        "--disk-path",
        disk_path,
        "--require-offsite",
        "--require-network",
        "--endpoint",
        f"core={targets.core_url}/health/ready",
        "--endpoint",
        f"public={targets.public_url}/",
        "--endpoint",
        f"admin={targets.admin_url}/",
        "--endpoint",
        f"staff={targets.staff_url}/",
        "--tls-host",
        "3korony.com",
        "--tls-host",
        "api.3korony.com",
        "--tls-host",
        "admin.3korony.com",
        "--tls-host",
        "staff.3korony.com",
    ]
    if env_path:
        monitoring += ["--env-file", env_path]

    return [
        ("host_preflight", ["bash", "scripts/host_preflight.sh"], {}),
        ("release_rc_truth", [python, "scripts/release_rc_truth_guard.py"], {}),
        ("legacy_rollback_gate", [python, "scripts/legacy_rollback_gate.py", rollback_evidence_dir], {}),
        (
            "dns_rollback_gate",
            [
                python,
                "scripts/dns_rollback_gate.py",
                dns_evidence_dir,
                "--output",
                str(output_dir / "dns-rollback-evidence.json"),
            ],
            {},
        ),
        (
            "pre_cutover_backup_gate",
            [
                python,
                "scripts/pre_cutover_backup_gate.py",
                "--backup-file",
                backup_file,
                "--manifest",
                backup_manifest,
                "--offsite-dir",
                backup_offsite_dir,
                "--restore-evidence",
                restore_evidence,
                "--restore-owner",
                restore_owner,
                "--output",
                str(output_dir / "pre-cutover-backup-evidence.json"),
            ],
            {},
        ),
        ("deployment_release_linkage", linkage, {}),
        ("production_monitoring", monitoring, {}),
        (
            "production_endpoint_probe",
            [
                python,
                "scripts/production_endpoint_probe.py",
                "--public-url",
                targets.public_url,
                "--core-url",
                targets.core_url,
                "--admin-url",
                targets.admin_url,
                "--staff-url",
                targets.staff_url,
                "--wss-url",
                targets.wss_url,
                "--output",
                str(output_dir / "production-endpoint-evidence.json"),
            ],
            {},
        ),
        (
            "external_public_truth",
            [python, "scripts/external_public_truth_probe.py", f"{targets.public_url}/"],
            {},
        ),
    ]


def execute_step(command: list[str], env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(command, env=env, capture_output=True, text=True, check=False)


def run_plan(
    *,
    plan: list[tuple[str, list[str], dict[str, str]]],
    output_dir: Path,
    manifest: dict[str, Any],
    executor: Callable[[list[str], dict[str, str]], subprocess.CompletedProcess[str]] = execute_step,
) -> int:
    steps: list[dict[str, Any]] = []
    manifest["steps"] = steps
    for index, (name, command, env_overrides) in enumerate(plan, start=1):
        started = utc_now()
        result = executor(command, env_overrides)
        finished = utc_now()
        stdout_spec = write_log(output_dir / f"{index:02d}-{name}.stdout.log", result.stdout or "")
        stderr_spec = write_log(output_dir / f"{index:02d}-{name}.stderr.log", result.stderr or "")
        step = {
            "name": name,
            "started_at": started,
            "finished_at": finished,
            "return_code": int(result.returncode),
            "status": "GREEN" if result.returncode == 0 else "RED",
            "stdout": stdout_spec,
            "stderr": stderr_spec,
        }
        steps.append(step)
        manifest["updated_at"] = finished
        if result.returncode != 0:
            manifest["status"] = "RED"
            manifest["failed_step"] = name
            safe_manifest_write(output_dir / "manifest.json", manifest)
            return 1
        safe_manifest_write(output_dir / "manifest.json", manifest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed technical production cutover readiness gate; never changes DNS or records owner GO")
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--launch-manifest", required=True)
    parser.add_argument("--product-repo-root", required=True)
    parser.add_argument("--rollback-evidence-dir", required=True)
    parser.add_argument("--dns-evidence-dir", required=True)
    parser.add_argument("--backup-file", required=True)
    parser.add_argument("--backup-manifest", required=True)
    parser.add_argument("--backup-offsite-dir", required=True)
    parser.add_argument("--restore-evidence", required=True)
    parser.add_argument("--restore-owner", required=True)
    parser.add_argument("--compose-file", default="compose.beget.yaml")
    parser.add_argument("--env-file")
    parser.add_argument("--backup-dir", default="/srv/three-crowns/backups")
    parser.add_argument("--disk-path", default="/srv/three-crowns")
    parser.add_argument("--public-url", required=True)
    parser.add_argument("--core-url", required=True)
    parser.add_argument("--admin-url", required=True)
    parser.add_argument("--staff-url", required=True)
    parser.add_argument("--wss-url", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        release_sha = normalize_sha(args.release_sha)
        launch_manifest_path = Path(args.launch_manifest).expanduser().resolve()
        _, launch_errors = validate_pre_owner_launch_manifest(launch_manifest_path, release_sha)
        if launch_errors:
            raise ValueError("; ".join(launch_errors))
        product_repo_root = Path(args.product_repo_root).expanduser().resolve()
        if not product_repo_root.is_dir():
            raise ValueError("product_repo_root must exist")
        targets = validate_targets(
            Targets(
                public_url=args.public_url,
                core_url=args.core_url,
                admin_url=args.admin_url,
                staff_url=args.staff_url,
                wss_url=args.wss_url,
            )
        )
        if not args.restore_owner.strip():
            raise ValueError("restore_owner is required")
        output_dir = prepare_output_dir(Path(args.output_dir))
    except Exception as exc:
        print(f"BLOCKED: production cutover readiness configuration error: {exc}", file=sys.stderr)
        return 2

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "kind": "THREE_CROWNS_PRODUCTION_CUTOVER_READINESS",
        "status": "RUNNING",
        "started_at": utc_now(),
        "release_sha": release_sha,
        "launch_manifest": str(launch_manifest_path),
        "product_repo_root": str(product_repo_root),
        "targets": {
            "public_url": targets.public_url,
            "core_url": targets.core_url,
            "admin_url": targets.admin_url,
            "staff_url": targets.staff_url,
            "wss_url": targets.wss_url,
        },
        "manual_prerequisites": sorted(MANUAL_REQUIRED_GATES),
        "owner_cutover_approval": "NOT_VERIFIED",
        "safety": {
            "changes_dns": False,
            "activates_providers": False,
            "records_owner_go": False,
            "mutates_business_data": False,
            "contains_credentials": False,
        },
    }
    safe_manifest_write(output_dir / "manifest.json", manifest)

    plan = command_plan(
        release_sha=release_sha,
        product_repo_root=product_repo_root,
        rollback_evidence_dir=args.rollback_evidence_dir,
        dns_evidence_dir=args.dns_evidence_dir,
        backup_file=args.backup_file,
        backup_manifest=args.backup_manifest,
        backup_offsite_dir=args.backup_offsite_dir,
        restore_evidence=args.restore_evidence,
        restore_owner=args.restore_owner.strip(),
        compose_file=args.compose_file,
        env_file=args.env_file,
        backup_dir=args.backup_dir,
        disk_path=args.disk_path,
        targets=targets,
        output_dir=output_dir,
    )
    result = run_plan(plan=plan, output_dir=output_dir, manifest=manifest)
    if result != 0:
        print(f"READINESS_EVIDENCE={output_dir / 'manifest.json'}")
        print("RESULT: PRODUCTION_CUTOVER_READINESS_RED")
        return result

    manifest["status"] = "GREEN"
    manifest["completed_at"] = utc_now()
    manifest["machine_evidence"] = {
        "dns_rollback_capture": "dns-rollback-evidence.json",
        "pre_cutover_backup": "pre-cutover-backup-evidence.json",
        "immutable_deployment_linkage": "deployment-release-linkage.json",
        "production_https_wss": "production-endpoint-evidence.json",
        "host_preflight": "01-host_preflight.stdout.log",
        "legacy_rollback_backup": "03-legacy_rollback_gate.stdout.log",
        "monitoring_alerting": "07-production_monitoring.stdout.log",
        "external_public_truth_probe": "09-external_public_truth.stdout.log",
    }
    manifest["next_action"] = (
        "Attach/review machine evidence in the launch manifest, keep owner_cutover_approval NOT_VERIFIED, "
        "obtain explicit owner GO only after review, then run verify_launch_acceptance.py --mode cutover."
    )
    safe_manifest_write(output_dir / "manifest.json", manifest)
    print(f"READINESS_EVIDENCE={output_dir / 'manifest.json'}")
    print("RESULT: PRODUCTION_CUTOVER_TECHNICAL_READINESS_GREEN; OWNER_GO_STILL_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
