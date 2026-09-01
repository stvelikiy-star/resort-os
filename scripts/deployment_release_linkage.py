#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_SERVICES = ("api", "web", "admin", "staff")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REVISION_LABEL = "org.opencontainers.image.revision"


def normalize_sha(value: str) -> str:
    normalized = value.strip().lower()
    if not SHA_RE.fullmatch(normalized):
        raise ValueError("expected SHA must be an exact 40-character hexadecimal Git commit")
    return normalized


def validate_release_linkage(
    *,
    expected_sha: str,
    source_sha: str,
    source_dirty: bool,
    services: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    try:
        expected = normalize_sha(expected_sha)
    except ValueError as exc:
        return [str(exc)]

    try:
        source = normalize_sha(source_sha)
    except ValueError:
        errors.append("source checkout SHA is not an exact 40-character Git commit")
        source = source_sha.strip().lower()

    if source != expected:
        errors.append(f"source checkout SHA mismatch: {source or 'MISSING'} != {expected}")
    if source_dirty:
        errors.append("source checkout is dirty")

    by_service = {str(item.get("service", "")): item for item in services}
    for service in REQUIRED_SERVICES:
        item = by_service.get(service)
        if not item:
            errors.append(f"required deployed service missing: {service}")
            continue
        state = str(item.get("state", "")).lower()
        if state != "running":
            errors.append(f"deployed service is not running: {service} ({state or 'unknown'})")
        image_id = str(item.get("image_id", "")).strip()
        if not image_id:
            errors.append(f"deployed service image id missing: {service}")
        revision = str(item.get("revision", "")).strip().lower()
        if not revision:
            errors.append(f"deployed service revision label missing: {service}")
        elif revision != expected:
            errors.append(f"deployed service revision mismatch: {service}={revision} expected={expected}")

    return errors


def run(command: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def gather_source(repo_root: Path) -> tuple[str, bool]:
    sha = run(["git", "rev-parse", "HEAD"], cwd=repo_root)
    dirty = bool(run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo_root))
    return sha, dirty


def gather_services(compose_file: str, env_file: str | None, repo_root: Path) -> list[dict[str, Any]]:
    prefix = ["docker", "compose"]
    if env_file:
        prefix += ["--env-file", env_file]
    prefix += ["-f", compose_file]

    result: list[dict[str, Any]] = []
    for service in REQUIRED_SERVICES:
        container_id = run(prefix + ["ps", "-q", service], cwd=repo_root)
        if not container_id:
            result.append({"service": service, "state": "missing", "image_id": "", "revision": ""})
            continue
        inspect_raw = run(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .State.Status}}|{{json .Image}}|{{json (index .Config.Labels \"org.opencontainers.image.revision\")}}",
                container_id,
            ],
            cwd=repo_root,
        )
        parts = inspect_raw.split("|", 2)
        if len(parts) != 3:
            raise RuntimeError(f"unexpected docker inspect result for {service}")
        state = json.loads(parts[0])
        image_id = json.loads(parts[1])
        revision = json.loads(parts[2]) if parts[2] != "<no value>" else ""
        result.append(
            {
                "service": service,
                "container_id": container_id,
                "state": state,
                "image_id": image_id,
                "revision": revision or "",
            }
        )
    return result


def build_evidence(expected_sha: str, source_sha: str, source_dirty: bool, services: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "expected_sha": normalize_sha(expected_sha),
        "source_sha": source_sha.strip().lower(),
        "source_dirty": bool(source_dirty),
        "services": [
            {
                "service": item.get("service"),
                "container_id": item.get("container_id", ""),
                "image_id": item.get("image_id", ""),
                "revision": item.get("revision", ""),
                "state": item.get("state", ""),
            }
            for item in services
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify exact Git SHA -> deployed Resort OS application image linkage")
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--compose-file", default="compose.beget.yaml")
    parser.add_argument("--env-file")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve()
    try:
        expected = normalize_sha(args.expected_sha)
        source_sha, source_dirty = gather_source(root)
        services = gather_services(args.compose_file, args.env_file, root)
        errors = validate_release_linkage(
            expected_sha=expected,
            source_sha=source_sha,
            source_dirty=source_dirty,
            services=services,
        )
    except (ValueError, RuntimeError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: release linkage inspection error: {type(exc).__name__}: {exc}")
        print("RESULT: DEPLOYMENT RELEASE LINKAGE RED")
        return 2

    evidence = build_evidence(expected, source_sha, source_dirty, services)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"FACT: expected_sha={expected}")
    print(f"FACT: source_sha={source_sha.strip().lower()}")
    for item in services:
        print(
            "FACT: "
            f"service={item.get('service')} state={item.get('state')} "
            f"image_id={item.get('image_id')} revision={item.get('revision')}"
        )

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: DEPLOYMENT RELEASE LINKAGE RED")
        return 1

    print("PASS: source checkout and all Resort OS application images match the exact accepted Git SHA")
    print("RESULT: DEPLOYMENT RELEASE LINKAGE GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
