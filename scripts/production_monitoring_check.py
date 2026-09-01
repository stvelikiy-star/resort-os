#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_SERVICES = ("caddy", "api", "web", "admin", "staff", "n8n")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_receipt(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.lstrip().startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def verify_sha256sums(target: Path) -> list[str]:
    errors: list[str] = []
    sums = target / "SHA256SUMS"
    if not sums.is_file():
        return ["backup SHA256SUMS missing"]
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            errors.append(f"invalid SHA256SUMS line: {line!r}")
            continue
        expected, name = parts
        name = name.lstrip("* ")
        artifact = target / name
        if not artifact.is_file():
            errors.append(f"backup artifact missing: {name}")
            continue
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest != expected:
            errors.append(f"backup checksum mismatch: {name}")
    return errors


def check_backup(backup_dir: Path, max_age_hours: float, require_offsite: bool, now: datetime | None = None) -> list[str]:
    errors: list[str] = []
    receipt_path = backup_dir / "last-success.env"
    if not receipt_path.is_file():
        return ["backup last-success receipt missing"]
    receipt = parse_receipt(receipt_path)
    completed = receipt.get("COMPLETED_AT", "")
    target_value = receipt.get("TARGET", "")
    if not completed:
        errors.append("backup receipt missing COMPLETED_AT")
    else:
        try:
            age = ((now or utc_now()) - parse_iso(completed)).total_seconds() / 3600
            if age < -0.01:
                errors.append("backup receipt timestamp is in the future")
            elif age > max_age_hours:
                errors.append(f"backup age {age:.2f}h exceeds {max_age_hours:.2f}h")
        except ValueError:
            errors.append("backup COMPLETED_AT is not ISO-8601")
    if not target_value:
        errors.append("backup receipt missing TARGET")
        return errors
    target = Path(target_value).resolve()
    root = backup_dir.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        errors.append("backup receipt TARGET escapes BACKUP_DIR")
        return errors
    if not target.is_dir():
        errors.append("backup receipt TARGET directory missing")
        return errors
    if not (target / "postgres.dump").is_file() or (target / "postgres.dump").stat().st_size <= 0:
        errors.append("backup postgres.dump missing or empty")
    errors.extend(verify_sha256sums(target))
    offsite = receipt.get("OFFSITE_STATUS", "")
    if require_offsite and offsite != "VERIFIED_UPLOAD":
        errors.append(f"off-site backup not verified: {offsite or 'MISSING'}")
    return errors


def normalize_compose_ps(payload: str) -> list[dict[str, Any]]:
    payload = payload.strip()
    if not payload:
        return []
    try:
        decoded = json.loads(payload)
        if isinstance(decoded, list):
            return [item for item in decoded if isinstance(item, dict)]
        if isinstance(decoded, dict):
            return [decoded]
    except json.JSONDecodeError:
        pass
    rows: list[dict[str, Any]] = []
    for line in payload.splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def canonical_container_snapshot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        service = str(row.get("service") or row.get("Service") or "").strip()
        if not service:
            continue
        result.append({
            "service": service,
            "state": str(row.get("state") or row.get("State") or "").lower(),
            "health": str(row.get("health") or row.get("Health") or "").lower(),
            "restart_count": int(row.get("restart_count") or row.get("RestartCount") or 0),
            "name": str(row.get("name") or row.get("Name") or ""),
        })
    return result


def gather_container_snapshot(compose_file: str, env_file: str | None) -> list[dict[str, Any]]:
    command = ["docker", "compose"]
    if env_file:
        command += ["--env-file", env_file]
    command += ["-f", compose_file, "ps", "--format", "json"]
    proc = subprocess.run(command, check=True, capture_output=True, text=True)
    snapshot = canonical_container_snapshot(normalize_compose_ps(proc.stdout))
    for item in snapshot:
        name = item.get("name")
        if not name:
            continue
        inspect = subprocess.run(
            ["docker", "inspect", "--format", "{{.RestartCount}}", str(name)],
            check=True,
            capture_output=True,
            text=True,
        )
        item["restart_count"] = int(inspect.stdout.strip() or "0")
    return snapshot


def check_containers(snapshot: list[dict[str, Any]], max_restarts: int) -> list[str]:
    errors: list[str] = []
    by_service = {str(item.get("service")): item for item in snapshot}
    for service in REQUIRED_SERVICES:
        item = by_service.get(service)
        if not item:
            errors.append(f"required service missing: {service}")
            continue
        if str(item.get("state", "")).lower() != "running":
            errors.append(f"service not running: {service}")
        health = str(item.get("health", "")).lower()
        if service != "caddy" and health != "healthy":
            errors.append(f"service not healthy: {service} ({health or 'no health state'})")
        try:
            restarts = int(item.get("restart_count", 0))
        except (TypeError, ValueError):
            errors.append(f"invalid restart count: {service}")
            continue
        if restarts > max_restarts:
            errors.append(f"service restart count too high: {service}={restarts}>{max_restarts}")
    return errors


def parse_request_log_5xx(text: str) -> int:
    count = 0
    for line in text.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            payload = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if payload.get("event") == "http_request":
            try:
                if int(payload.get("status", 0)) >= 500:
                    count += 1
            except (TypeError, ValueError):
                continue
    return count


def gather_api_logs(compose_file: str, env_file: str | None, since: str) -> str:
    command = ["docker", "compose"]
    if env_file:
        command += ["--env-file", env_file]
    command += ["-f", compose_file, "logs", "--no-color", "--since", since, "api"]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def check_endpoint(name: str, url: str, timeout: float) -> str | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "three-crowns-monitor/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                return f"endpoint {name} returned HTTP {response.status}"
    except Exception as exc:  # network errors are operational evidence
        return f"endpoint {name} failed: {type(exc).__name__}: {exc}"
    return None


def tls_days_remaining(host: str, port: int = 443, timeout: float = 5.0, now: datetime | None = None) -> float:
    context = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as wrapped:
            cert = wrapped.getpeercert()
    expires = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (expires - (now or utc_now())).total_seconds() / 86400


def parse_named_values(values: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for item in values:
        if "=" not in item:
            raise ValueError(f"expected NAME=VALUE, got {item!r}")
        name, value = item.split("=", 1)
        if not name.strip() or not value.strip():
            raise ValueError(f"expected non-empty NAME=VALUE, got {item!r}")
        result.append((name.strip(), value.strip()))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Three Crowns production monitoring acceptance check")
    parser.add_argument("--backup-dir", default="/srv/three-crowns/backups")
    parser.add_argument("--disk-path", default="/srv/three-crowns")
    parser.add_argument("--max-backup-age-hours", type=float, default=24.0)
    parser.add_argument("--max-disk-used-percent", type=float, default=85.0)
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--max-5xx", type=int, default=0)
    parser.add_argument("--logs-since", default="15m")
    parser.add_argument("--min-tls-days", type=float, default=14.0)
    parser.add_argument("--require-offsite", action="store_true")
    parser.add_argument("--compose-file", default="compose.beget.yaml")
    parser.add_argument("--env-file")
    parser.add_argument("--container-snapshot")
    parser.add_argument("--api-log-file")
    parser.add_argument("--endpoint", action="append", default=[], help="NAME=URL; repeatable")
    parser.add_argument("--tls-host", action="append", default=[])
    parser.add_argument("--require-network", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    errors: list[str] = []

    try:
        if args.container_snapshot:
            snapshot_raw = json.loads(Path(args.container_snapshot).read_text(encoding="utf-8"))
            if not isinstance(snapshot_raw, list):
                raise ValueError("container snapshot must be a JSON list")
            snapshot = canonical_container_snapshot(snapshot_raw)
        else:
            snapshot = gather_container_snapshot(args.compose_file, args.env_file)
        errors.extend(check_containers(snapshot, args.max_restarts))
    except Exception as exc:
        errors.append(f"container inspection failed: {type(exc).__name__}: {exc}")

    try:
        log_text = Path(args.api_log_file).read_text(encoding="utf-8") if args.api_log_file else gather_api_logs(args.compose_file, args.env_file, args.logs_since)
        five_xx = parse_request_log_5xx(log_text)
        if five_xx > args.max_5xx:
            errors.append(f"API 5xx count {five_xx} exceeds {args.max_5xx} in monitoring window")
    except Exception as exc:
        errors.append(f"API log inspection failed: {type(exc).__name__}: {exc}")

    try:
        errors.extend(check_backup(Path(args.backup_dir), args.max_backup_age_hours, args.require_offsite))
    except Exception as exc:
        errors.append(f"backup inspection failed: {type(exc).__name__}: {exc}")

    try:
        usage = shutil.disk_usage(args.disk_path)
        used_percent = (usage.used / usage.total * 100) if usage.total else 100.0
        if used_percent > args.max_disk_used_percent:
            errors.append(f"disk usage {used_percent:.2f}% exceeds {args.max_disk_used_percent:.2f}%")
    except Exception as exc:
        errors.append(f"disk inspection failed: {type(exc).__name__}: {exc}")

    try:
        endpoints = parse_named_values(args.endpoint)
    except ValueError as exc:
        errors.append(str(exc))
        endpoints = []
    if args.require_network and (not endpoints or not args.tls_host):
        errors.append("network acceptance requires at least one endpoint and one TLS host")
    for name, url in endpoints:
        failure = check_endpoint(name, url, args.timeout)
        if failure:
            errors.append(failure)
    for host in args.tls_host:
        try:
            days = tls_days_remaining(host, timeout=args.timeout)
            if days < args.min_tls_days:
                errors.append(f"TLS certificate for {host} expires in {days:.2f}d (< {args.min_tls_days:.2f}d)")
        except Exception as exc:
            errors.append(f"TLS check failed for {host}: {type(exc).__name__}: {exc}")

    if errors:
        for error in errors:
            print(f"ALERT: {error}")
        print("RESULT: PRODUCTION MONITORING RED")
        return 1
    print("FACT: required_services=6")
    print("FACT: backup_receipt=verified")
    print("FACT: structured_5xx_window=green")
    print("RESULT: PRODUCTION MONITORING GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
