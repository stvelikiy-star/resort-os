#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MUTATION_ACK = "I_UNDERSTAND_SYNTHETIC_WRITES"


@dataclass(frozen=True)
class TargetSet:
    public_url: str
    core_url: str
    admin_url: str
    staff_url: str
    ws_url: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_sha(value: str) -> str:
    normalized = value.strip().lower()
    if not SHA_RE.fullmatch(normalized):
        raise ValueError("expected SHA must be an exact 40-character hexadecimal Git commit")
    return normalized


def validate_https_staging_url(label: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"{label} must be an HTTPS URL with a hostname")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    if "staging" not in parsed.hostname.lower():
        raise ValueError(f"{label} hostname must explicitly contain staging")
    return value.rstrip("/")


def validate_wss_staging_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "wss" or not parsed.hostname:
        raise ValueError("ws_url must be a WSS URL with a hostname")
    if parsed.username or parsed.password:
        raise ValueError("ws_url must not contain credentials")
    if "staging" not in parsed.hostname.lower():
        raise ValueError("ws_url hostname must explicitly contain staging")
    return value.rstrip("/")


def validate_targets(targets: TargetSet) -> TargetSet:
    return TargetSet(
        public_url=validate_https_staging_url("public_url", targets.public_url),
        core_url=validate_https_staging_url("core_url", targets.core_url),
        admin_url=validate_https_staging_url("admin_url", targets.admin_url),
        staff_url=validate_https_staging_url("staff_url", targets.staff_url),
        ws_url=validate_wss_staging_url(targets.ws_url) if targets.ws_url else None,
    )


def prepare_output_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError("output path exists and is not a directory")
        if any(resolved.iterdir()):
            raise ValueError("output directory must be empty to avoid mixing acceptance evidence")
    else:
        resolved.mkdir(parents=True, mode=0o700)
    return resolved


def write_log(path: Path, text: str) -> dict[str, object]:
    path.write_text(text, encoding="utf-8")
    return {
        "path": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def safe_manifest_write(path: Path, payload: dict[str, object]) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(path)


def command_plan(
    *,
    expected_sha: str,
    rollback_evidence_dir: str,
    targets: TargetSet,
    compose_file: str,
    env_file: str | None,
    backup_dir: str,
    disk_path: str,
    release_linkage_output: str,
) -> list[tuple[str, list[str], dict[str, str]]]:
    python = sys.executable
    linkage = [
        python,
        "scripts/deployment_release_linkage.py",
        "--expected-sha",
        expected_sha,
        "--compose-file",
        compose_file,
        "--output",
        release_linkage_output,
    ]
    if env_file:
        linkage += ["--env-file", env_file]

    smoke_env = {
        "APP_ENV": "staging",
        "CORE_API_URL": targets.core_url,
        "STAGING_ACCEPTANCE_MUTATIONS": MUTATION_ACK,
    }
    if targets.ws_url:
        smoke_env["CORE_WS_URL"] = targets.ws_url

    monitor = [
        python,
        "scripts/production_monitoring_check.py",
        "--compose-file",
        compose_file,
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
    ]
    if env_file:
        monitor += ["--env-file", env_file]
    for host in dict.fromkeys(
        urlparse(url).hostname
        for url in (targets.public_url, targets.core_url, targets.admin_url, targets.staff_url)
    ):
        if host:
            monitor += ["--tls-host", host]

    return [
        (
            "legacy_rollback_gate",
            [python, "scripts/legacy_rollback_gate.py", rollback_evidence_dir],
            {},
        ),
        ("deployment_release_linkage", linkage, {}),
        (
            "external_public_truth",
            [python, "scripts/external_public_truth_probe.py", f"{targets.public_url}/"],
            {},
        ),
        (
            "staging_business_acceptance",
            [python, "scripts/staging_acceptance.py"],
            smoke_env,
        ),
        ("production_monitoring", monitor, {}),
    ]


def execute_step(command: list[str], env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(command, env=env, capture_output=True, text=True, check=False)


def run_acceptance(
    *,
    plan: list[tuple[str, list[str], dict[str, str]]],
    output_dir: Path,
    manifest: dict[str, object],
    executor: Callable[[list[str], dict[str, str]], subprocess.CompletedProcess[str]] = execute_step,
) -> int:
    steps: list[dict[str, object]] = []
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

    manifest["status"] = "GREEN"
    manifest["completed_at"] = utc_now()
    safe_manifest_write(output_dir / "manifest.json", manifest)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fail-closed Three Crowns external Beget staging acceptance sequence")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--rollback-evidence-dir", required=True)
    parser.add_argument("--public-url", required=True)
    parser.add_argument("--core-url", required=True)
    parser.add_argument("--admin-url", required=True)
    parser.add_argument("--staff-url", required=True)
    parser.add_argument("--ws-url")
    parser.add_argument("--compose-file", default="compose.beget.yaml")
    parser.add_argument("--env-file")
    parser.add_argument("--backup-dir", default="/srv/three-crowns/backups")
    parser.add_argument("--disk-path", default="/srv/three-crowns")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        expected_sha = normalize_sha(args.expected_sha)
        targets = validate_targets(
            TargetSet(
                public_url=args.public_url,
                core_url=args.core_url,
                admin_url=args.admin_url,
                staff_url=args.staff_url,
                ws_url=args.ws_url,
            )
        )
        output_dir = prepare_output_dir(Path(args.output_dir))
    except (ValueError, OSError) as exc:
        print(f"BLOCKED: external staging acceptance configuration error: {exc}", file=sys.stderr)
        return 2

    manifest: dict[str, object] = {
        "schema_version": 1,
        "kind": "THREE_CROWNS_EXTERNAL_STAGING_ACCEPTANCE",
        "status": "RUNNING",
        "started_at": utc_now(),
        "expected_sha": expected_sha,
        "targets": {
            "public_url": targets.public_url,
            "core_url": targets.core_url,
            "admin_url": targets.admin_url,
            "staff_url": targets.staff_url,
            "ws_url": targets.ws_url,
        },
        "safety": {
            "contains_credentials": False,
            "changes_dns": False,
            "mutates_staging_business_data": True,
            "production_target_allowed": False,
        },
    }
    safe_manifest_write(output_dir / "manifest.json", manifest)

    plan = command_plan(
        expected_sha=expected_sha,
        rollback_evidence_dir=args.rollback_evidence_dir,
        targets=targets,
        compose_file=args.compose_file,
        env_file=args.env_file,
        backup_dir=args.backup_dir,
        disk_path=args.disk_path,
        release_linkage_output=str(output_dir / "release-linkage.json"),
    )
    rc = run_acceptance(plan=plan, output_dir=output_dir, manifest=manifest)
    if rc == 0:
        print("RESULT: EXTERNAL STAGING ACCEPTANCE GREEN")
        print(f"EVIDENCE: {output_dir / 'manifest.json'}")
        return 0
    print(f"RESULT: EXTERNAL STAGING ACCEPTANCE RED at {manifest.get('failed_step')}", file=sys.stderr)
    print(f"EVIDENCE: {output_dir / 'manifest.json'}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
