#!/usr/bin/env python3
"""Monitor the isolated RC441 stack using the reviewed production checks."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from production_monitoring_check import (
    canonical_container_snapshot, check_backup, check_containers,
    normalize_compose_ps, parse_request_log_5xx, utc_now,
)

SERVICES = ("caddy", "api", "web", "admin", "staff", "guest-web", "postgres")
ROUTES = (
    ("web.rc441.localhost", "/"),
    ("admin.rc441.localhost", "/"),
    ("staff.rc441.localhost", "/"),
    ("api.rc441.localhost", "/health/ready"),
    ("web.rc441.localhost", "/g/health-check"),
    ("staff-queue.rc430.example.com", "/"),
)


def run_checks(rc: Path, backup_dir: Path) -> list[str]:
    errors = []
    try:
        payload = subprocess.check_output(
            [str(rc / "compose-rc"), "ps", "--format", "json"],
            cwd=rc, text=True, timeout=20,
        )
        rows = canonical_container_snapshot(normalize_compose_ps(payload))
        for row in rows:
            row["restart_count"] = int(subprocess.check_output(
                ["docker", "inspect", "--format", "{{.RestartCount}}", row["name"]],
                text=True, timeout=5,
            ))
        errors.extend(check_containers(rows, 3, SERVICES))
    except Exception as exc:
        errors.append(f"container inspection failed: {type(exc).__name__}")
    try:
        logs = subprocess.check_output(
            [str(rc / "compose-rc"), "logs", "--no-color", "--since", "15m", "api"],
            cwd=rc, text=True, timeout=15,
        )
        if parse_request_log_5xx(logs):
            errors.append("API structured 5xx present in last 15 minutes")
    except Exception as exc:
        errors.append(f"API log inspection failed: {type(exc).__name__}")
    try:
        errors.extend(check_backup(backup_dir, 24, True))
    except Exception as exc:
        errors.append(f"backup inspection failed: {type(exc).__name__}")
    try:
        usage = shutil.disk_usage(rc)
        if usage.used / (usage.used + usage.free) * 100 > 85:
            errors.append("disk usage exceeds 85% of user-available capacity")
    except OSError:
        errors.append("disk inspection failed")
    for host, path in ROUTES:
        try:
            response = subprocess.run(
                ["curl", "--silent", "--show-error", "--max-time", "5",
                 "--connect-timeout", "2", "--cacert", str(rc / "rc-ca.crt"),
                 "--connect-to", f"{host}:443:127.0.0.1:17444",
                 "-H", "Accept: text/html,application/json;q=0.9",
                 "-o", "/dev/null", "-w", "%{http_code}", f"https://{host}{path}"],
                text=True, capture_output=True, timeout=7,
            )
            if response.returncode or response.stdout.strip() != "200":
                errors.append(f"HTTPS unavailable: {host}{path}")
        except Exception as exc:
            errors.append(f"HTTPS inspection failed: {host}: {type(exc).__name__}")
    return errors


def publish_result(errors: list[str], state_file: Path, notify: bool, label: str) -> int:
    try:
        previous = json.loads(state_file.read_text())
    except (OSError, ValueError):
        previous = {}
    if not isinstance(previous, dict):
        previous = {}
    signature = [re.sub(r"\d+(?:\.\d+)?", "#", error) for error in errors]
    status = "RED" if errors else "GREEN"
    result = {
        "component": label, "utc": utc_now().isoformat(), "status": status,
        "errors": errors, "alert_signature": signature,
        "last_notification": previous.get("last_notification"),
        "external_https_accepted": False,
    }
    changed = signature != previous.get("alert_signature")
    retry = previous.get("notification_error") or (errors and not previous.get("last_notification"))
    if notify and (changed or retry):
        try:
            notification = subprocess.run(
                ["notify-send", "--print-id", "--app-name", "MARINA SMART",
                 "--urgency", "critical" if errors else "normal",
                 f"{label} {status}", "\n".join(errors) if errors else "Checks recovered"],
                capture_output=True, text=True, timeout=10,
            )
            if notification.returncode:
                raise RuntimeError("desktop notification rejected")
            result["last_notification"] = {
                "utc": result["utc"], "id": notification.stdout.strip(), "status": status,
            }
        except Exception as exc:
            result["notification_error"] = type(exc).__name__
            result["status"] = "RED"
    state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(mode="w", dir=state_file.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, state_file)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if errors or result.get("notification_error") else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rc-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--notify-desktop", action="store_true")
    parser.add_argument("--label", default="MARINA RC441")
    args = parser.parse_args()
    rc = args.rc_dir.resolve()
    return publish_result(
        run_checks(rc, args.backup_dir or rc / "backups"),
        args.state_file, args.notify_desktop, args.label,
    )


if __name__ == "__main__":
    raise SystemExit(main())
