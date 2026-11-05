#!/usr/bin/env python3
"""Read-only deployment configuration guard for independent MARINA SMART hotels.

Usage:
  python3 scripts/verify_marina_customer_isolation.py first.env second.env

Files contain secrets; this script NEVER prints values. Run before onboarding,
but keep secrets outside Git. This check does NOT prove a running deployment.
"""
from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path

HOST_KEYS = ("PUBLIC_HOST", "ADMIN_HOST", "STAFF_HOST", "API_HOST", "AUTOMATION_HOST")
UNIQUE_KEYS = ("PROPERTY_CODE", "COMPOSE_PROJECT_NAME", "POSTGRES_DB",
               "POSTGRES_USER", "POSTGRES_PASSWORD", "N8N_ENCRYPTION_KEY",
               "AUTOMATION_SERVICE_KEY", "GREEN_API_ID_INSTANCE",
               "GREEN_API_TOKEN_INSTANCE", "GREEN_API_WEBHOOK_SECRET")
PATH_KEYS = ("HOST_DATA_DIR", "BACKUP_DIR")
REQUIRED = ("PROPERTY_CODE", "COMPOSE_PROJECT_NAME", "MARINA_DEPLOYMENT_HOST_ID", "POSTGRES_DB",
            "POSTGRES_USER", "POSTGRES_PASSWORD", "N8N_ENCRYPTION_KEY",
            "AUTOMATION_SERVICE_KEY", "HOST_DATA_DIR", "BACKUP_DIR",
            "COOKIE_SECURE", "MARINA_TENANT_CONTEXT_ENABLED", *HOST_KEYS)
PLACEHOLDERS = ("change_me", "example", "placeholder")


def parse_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"Configuration file not found: {path.name}")
    result: dict[str, str] = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line:
            raise ValueError(f"{path.name}: invalid env line {n}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key in result:
            raise ValueError(f"{path.name}: invalid/duplicate key at line {n}")
        result[key] = value.strip().strip('"').strip("'")
    return result


def path_overlap(a: str, b: str) -> bool:
    one, two = Path(a).resolve(strict=False), Path(b).resolve(strict=False)
    return one == two or one in two.parents or two in one.parents


def validate_one(env: dict[str, str], label: str) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED:
        value = env.get(key, "").strip()
        if not value or any(hint in value.lower() for hint in PLACEHOLDERS):
            errors.append(f"{label}: {key} missing or placeholder")
    if env.get("COOKIE_SECURE", "").lower() != "true":
        errors.append(f"{label}: COOKIE_SECURE must be true")
    if env.get("MARINA_TENANT_CONTEXT_ENABLED", "").lower() not in ("false", "0"):
        errors.append(f"{label}: expected dedicated single-property mode (tenant preview off)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,62}", env.get("COMPOSE_PROJECT_NAME", "")):
        errors.append(f"{label}: invalid COMPOSE_PROJECT_NAME")
    for key in PATH_KEYS:
        value = env.get(key, "")
        if not value.startswith("/") or value == "/":
            errors.append(f"{label}: {key} must be an explicit absolute directory")
    if all(env.get(key, "").startswith("/") for key in PATH_KEYS):
        if path_overlap(env["HOST_DATA_DIR"], env["BACKUP_DIR"]):
            errors.append(f"{label}: data and backups must not share a directory subtree")
    hosts = [env.get(key, "").lower().strip(".") for key in HOST_KEYS]
    if len(set(hosts)) != len(HOST_KEYS):
        errors.append(f"{label}: service hostnames must be unique")
    for key, host in zip(HOST_KEYS, hosts):
        if not host or "://" in host or "/" in host or ":" in host or "." not in host:
            errors.append(f"{label}: {key} must be a DNS hostname")
        else:
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                errors.append(f"{label}: {key} must not be an IP address")
    return errors


def validate_pair(a: dict[str, str], b: dict[str, str]) -> list[str]:
    errors: list[str] = []
    # compose.production.yaml publishes 80/443 directly from each Caddy.
    # It is safe to reuse on independent VMs, but two instances on one host
    # would compete for the same ports. A shared edge needs another topology.
    if a.get("MARINA_DEPLOYMENT_HOST_ID") and (
        a["MARINA_DEPLOYMENT_HOST_ID"] == b.get("MARINA_DEPLOYMENT_HOST_ID")
    ):
        errors.append("same Ubuntu/VM host unsupported by compose.production.yaml (80/443 collision); use separate hosts until shared-edge topology is reviewed")
    for key in UNIQUE_KEYS:
        va, vb = a.get(key, "").strip(), b.get(key, "").strip()
        if va and vb and va == vb:
            errors.append(f"hotels share {key}")
    # Cross-key overlaps matter too: hotel A's data cannot be inside
    # hotel B's backup directory (or vice versa).
    for a_key in PATH_KEYS:
        for b_key in PATH_KEYS:
            if a.get(a_key) and b.get(b_key) and path_overlap(a[a_key], b[b_key]):
                errors.append(f"hotels share/overlap {a_key} and {b_key}")
    a_hosts = {a.get(key, "").lower().strip(".") for key in HOST_KEYS}
    b_hosts = {b.get(key, "").lower().strip(".") for key in HOST_KEYS}
    if (a_hosts - {""}) & (b_hosts - {""}):
        errors.append("hotels share public/administrative hostnames")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hotel_env", nargs="+", type=Path, help="Two or more private .env files")
    args = parser.parse_args()
    if len(args.hotel_env) < 2:
        parser.error("Provide at least two independent hotel env files")
    try:
        values = [parse_env(p) for p in args.hotel_env]
        errors = []
        for i, env in enumerate(values):
            errors += validate_one(env, f"hotel_{i+1}")
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                errors += [f"hotel_{i+1}/hotel_{j+1}: {e}" for e in validate_pair(values[i], values[j])]
    except (ValueError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    if errors:
        for issue in errors:
            print(f"BLOCKED: {issue}", file=sys.stderr)
        return 1
    print(f"PASS: {len(values)} customer deployment configurations are distinct (static checks only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
