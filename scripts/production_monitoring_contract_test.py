#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "production_monitoring_check.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_backup(root: Path, completed_at: datetime, offsite: str = "VERIFIED_UPLOAD", corrupt: bool = False) -> Path:
    backup_dir = root / "backups"
    target = backup_dir / completed_at.strftime("%Y%m%dT%H%M%SZ")
    target.mkdir(parents=True)
    dump = target / "postgres.dump"
    dump.write_bytes(b"FAKE-CUSTOM-DUMP\n")
    (target / "SHA256SUMS").write_text(f"{sha256(dump)}  postgres.dump\n", encoding="utf-8")
    if corrupt:
        dump.write_bytes(b"TAMPERED\n")
    (backup_dir / "last-success.env").write_text(
        "\n".join([
            f"COMPLETED_AT={completed_at.isoformat()}",
            f"TARGET={target}",
            f"OFFSITE_STATUS={offsite}",
            "OFFSITE_PREFIX=s3://test/production/example/",
        ]) + "\n",
        encoding="utf-8",
    )
    return backup_dir


def write_snapshot(path: Path, *, api_restarts: int = 0, api_health: str = "healthy") -> None:
    rows = []
    for service in ("caddy", "api", "web", "admin", "staff", "n8n"):
        rows.append({
            "service": service,
            "state": "running",
            "health": "" if service == "caddy" else (api_health if service == "api" else "healthy"),
            "restart_count": api_restarts if service == "api" else 0,
        })
    path.write_text(json.dumps(rows), encoding="utf-8")


def run_case(tmp: Path, backup_dir: Path, snapshot: Path, logs: Path, extra: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--backup-dir", str(backup_dir),
        "--disk-path", str(tmp),
        "--max-disk-used-percent", "100",
        "--container-snapshot", str(snapshot),
        "--api-log-file", str(logs),
        "--require-offsite",
    ]
    if extra:
        command.extend(extra)
    return subprocess.run(command, capture_output=True, text=True)


def require_red(result: subprocess.CompletedProcess[str], fragment: str) -> None:
    assert result.returncode != 0, result.stdout + result.stderr
    assert "RESULT: PRODUCTION MONITORING RED" in result.stdout
    assert fragment in result.stdout, result.stdout


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        now = datetime.now(timezone.utc)
        backup_dir = write_backup(tmp, now)
        snapshot = tmp / "containers.json"
        logs = tmp / "api.log"
        write_snapshot(snapshot)
        logs.write_text('{"event":"http_request","status":200,"path":"/health/ready"}\n', encoding="utf-8")

        green = run_case(tmp, backup_dir, snapshot, logs)
        assert green.returncode == 0, green.stdout + green.stderr
        assert "RESULT: PRODUCTION MONITORING GREEN" in green.stdout

        marina_snapshot = tmp / "marina-containers.json"
        marina_services = ("caddy", "api", "web", "admin", "staff", "guest-web", "postgres")
        marina_rows = [
            {"service": service, "state": "running",
             "health": "" if service == "caddy" else "healthy", "restart_count": 0}
            for service in marina_services
        ]
        marina_snapshot.write_text(json.dumps(marina_rows), encoding="utf-8")
        marina_args = [
            argument
            for service in marina_services
            for argument in ("--required-service", service)
        ]
        result = run_case(tmp, backup_dir, marina_snapshot, logs, marina_args)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "FACT: required_services=7" in result.stdout

        for service in ("postgres", "guest-web"):
            missing = [row for row in marina_rows if row["service"] != service]
            marina_snapshot.write_text(json.dumps(missing), encoding="utf-8")
            require_red(run_case(tmp, backup_dir, marina_snapshot, logs, marina_args),
                        f"required service missing: {service}")
            unhealthy = [dict(row, health="unhealthy") if row["service"] == service
                         else row for row in marina_rows]
            marina_snapshot.write_text(json.dumps(unhealthy), encoding="utf-8")
            require_red(run_case(tmp, backup_dir, marina_snapshot, logs, marina_args),
                        f"service not healthy: {service}")

        class BrowserEndpoint(BaseHTTPRequestHandler):
            def do_GET(self):
                code = 200 if "text/html" in self.headers.get("Accept", "") else 503
                self.send_response(code)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), BrowserEndpoint)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            result = run_case(tmp, backup_dir, snapshot, logs,
                              ["--endpoint", f"customer-web={url}"])
            assert result.returncode == 0, result.stdout + result.stderr
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

        stale_root = tmp / "stale"
        stale_backup = write_backup(stale_root, now - timedelta(hours=30))
        require_red(run_case(tmp, stale_backup, snapshot, logs), "backup age")

        no_offsite_root = tmp / "no-offsite"
        no_offsite = write_backup(no_offsite_root, now, offsite="LOCAL_ONLY")
        require_red(run_case(tmp, no_offsite, snapshot, logs), "off-site backup not verified")

        corrupt_root = tmp / "corrupt"
        corrupt = write_backup(corrupt_root, now, corrupt=True)
        require_red(run_case(tmp, corrupt, snapshot, logs), "backup checksum mismatch")

        bad_snapshot = tmp / "bad-containers.json"
        write_snapshot(bad_snapshot, api_health="unhealthy")
        require_red(run_case(tmp, backup_dir, bad_snapshot, logs), "service not healthy: api")

        restart_snapshot = tmp / "restart-containers.json"
        write_snapshot(restart_snapshot, api_restarts=4)
        require_red(run_case(tmp, backup_dir, restart_snapshot, logs), "service restart count too high: api=4>3")

        bad_logs = tmp / "api-5xx.log"
        bad_logs.write_text(
            'api | {"event":"http_request","status":503,"path":"/api/v1/test"}\n',
            encoding="utf-8",
        )
        require_red(run_case(tmp, backup_dir, snapshot, bad_logs), "API 5xx count 1 exceeds 0")

        no_network = run_case(tmp, backup_dir, snapshot, logs, ["--require-network"])
        require_red(no_network, "network acceptance requires at least one endpoint and one TLS host")

    print("PRODUCTION_MONITORING_CONTRACT_OK")


if __name__ == "__main__":
    main()
