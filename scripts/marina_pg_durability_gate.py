#!/usr/bin/env python3
"""Read-only durability gate for MARINA SMART PostgreSQL Docker containers.

Usage:
  python scripts/marina_pg_durability_gate.py \
    --container marina-rc426-persist-pg \
    --expected-volume marina-rc426-persist-pgdata

Checks that PGDATA is backed by a persistent Docker volume (or explicitly
mounted host directory), rather than tmpfs/container filesystem. This protects
against losing a synthetic or commercial database on container/host restart.
Never prints Docker environment or database credentials. Never mutates Docker.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from typing import Any

PGDATA = "/var/lib/postgresql/data"


def inspect_errors(
    mounts: list[dict[str, Any]],
    tmpfs: dict[str, Any] | None,
    restart_policy: str,
    expected_volume: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if tmpfs and any(key.rstrip("/") == PGDATA for key in tmpfs):
        errors.append("PGDATA_TMPFS_FORBIDDEN")
    pg_mounts = [m for m in mounts if str(m.get("Destination", "")).rstrip("/") == PGDATA]
    if len(pg_mounts) != 1:
        errors.append("PGDATA_REQUIRES_ONE_EXPLICIT_PERSISTENT_MOUNT")
    else:
        mount = pg_mounts[0]
        kind = mount.get("Type")
        if kind not in {"volume", "bind"}:
            errors.append("PGDATA_MOUNT_NOT_PERSISTENT")
        if not mount.get("RW", False):
            errors.append("PGDATA_MOUNT_READONLY")
        if expected_volume and (kind != "volume" or mount.get("Name") != expected_volume):
            errors.append("PGDATA_NAMED_VOLUME_MISMATCH")
    if restart_policy not in {"always", "unless-stopped"}:
        errors.append("POSTGRES_AUTO_RESTART_NOT_CONFIGURED")
    return errors


def inspect_field(container: str, fmt: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "--format", fmt, container],
        capture_output=True, text=True, timeout=12, check=False,
    )
    if result.returncode:
        raise RuntimeError("DOCKER_INSPECT_UNAVAILABLE")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--expected-volume", default=None)
    args = parser.parse_args()
    try:
        mounts = json.loads(inspect_field(args.container, "{{json .Mounts}}"))
        tmpfs = json.loads(inspect_field(args.container, "{{json .HostConfig.Tmpfs}}"))
        policy = inspect_field(args.container, "{{.HostConfig.RestartPolicy.Name}}")
        errors = inspect_errors(mounts, tmpfs, policy, args.expected_volume)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        print("FAIL: POSTGRES_DURABILITY_INSPECTION_UNAVAILABLE")
        return 2
    if errors:
        for error in errors:
            print("FAIL:", error)
        return 1
    print("PASS: POSTGRES_PGDATA_PERSISTENT_AND_AUTO_RESTART_CONFIGURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())