#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DOMAIN = "3korony.com"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value)


def require_readable(path: Path, label: str, *, directory: bool | None = None) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"{label} does not exist: {resolved}")
    if directory is True and not resolved.is_dir():
        raise ValueError(f"{label} must be a directory: {resolved}")
    if directory is False and not resolved.is_file():
        raise ValueError(f"{label} must be a file: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise ValueError(f"{label} is not readable: {resolved}")
    return resolved


def archive_paths(output: Path, paths: list[tuple[str, Path]]) -> None:
    with tarfile.open(output, "w:gz", dereference=False) as archive:
        for label, path in paths:
            archive.add(path, arcname=f"{label}/{path.name}", recursive=True)


def run_checked(command: list[str], *, env: dict[str, str] | None = None, stdout_path: Path | None = None) -> None:
    if stdout_path is not None:
        with stdout_path.open("wb") as handle:
            proc = subprocess.run(command, stdout=handle, stderr=subprocess.PIPE, check=False, env=env)
    else:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False, env=env)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace") if isinstance(proc.stderr, bytes) else (proc.stderr or "")
        raise RuntimeError(f"command failed ({command[0]}): {stderr.strip()[:500]}")


def capture_database(target: Path, env_name: str) -> dict[str, Any]:
    database_url = os.environ.get(env_name, "").strip()
    if not database_url:
        raise ValueError(f"database backup requested but environment variable {env_name} is empty")
    if shutil.which("pg_dump") is None:
        raise ValueError("pg_dump is required when database backup is requested")
    run_checked(["pg_dump", "--format=custom", "--no-owner", "--no-acl", database_url], env=os.environ.copy(), stdout_path=target)
    return {"path": target.name, "size_bytes": target.stat().st_size, "sha256": sha256(target), "format": "pg_dump_custom"}


def resolve_dns(domain: str) -> dict[str, Any]:
    result: dict[str, Any] = {"domain": domain, "captured_at": utc_now(), "records": {}}
    if shutil.which("dig"):
        for record_type in ("A", "AAAA", "CNAME", "NS", "MX", "TXT", "SOA"):
            proc = subprocess.run(
                ["dig", "+noall", "+answer", domain, record_type],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            result["records"][record_type] = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    else:
        addresses: list[str] = []
        try:
            addresses = sorted({item[4][0] for item in socket.getaddrinfo(domain, 443)})
        except socket.gaierror:
            pass
        result["records"]["RESOLVER_FALLBACK"] = addresses
        result["warning"] = "dig unavailable; TTL/MX/NS/TXT/SOA were not captured"
    return result


def load_dns_snapshot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "domain" not in data or "records" not in data:
        raise ValueError("DNS snapshot JSON must contain domain and records")
    return data


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Non-destructive legacy 3korony.com rollback capture")
    parser.add_argument("--web-root", required=True, help="Current live web root to archive; required and read-only")
    parser.add_argument("--uploads", action="append", default=[], help="Additional upload/media directory; repeatable")
    parser.add_argument("--config", action="append", default=[], help="Web/vhost/runtime config file or directory; repeatable")
    parser.add_argument("--output-dir", required=True, help="New evidence directory; must not already contain a completed manifest")
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--dns-snapshot-file", help="Use pre-captured DNS JSON instead of network lookup (for controlled/offline runs)")
    parser.add_argument("--database-url-env", help="Environment variable containing legacy DB URL; omit when legacy site has no DB")
    parser.add_argument("--offsite-dir", help="Optional mounted/off-site destination; copy completed evidence directory there")
    parser.add_argument("--rollback-owner", required=True, help="Named person/role responsible for rollback execution")
    args = parser.parse_args()

    try:
        rollback_owner = args.rollback_owner.strip()
        if not rollback_owner:
            raise ValueError("rollback owner cannot be empty")
        web_root = require_readable(Path(args.web_root), "web root", directory=True)
        uploads = [require_readable(Path(item), "uploads/media path") for item in args.uploads]
        configs = [require_readable(Path(item), "config path") for item in args.config]
        output_root = Path(args.output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        if any(output_root.iterdir()):
            raise ValueError(f"output directory must be empty to avoid mixing rollback evidence: {output_root}")

        dns = load_dns_snapshot(require_readable(Path(args.dns_snapshot_file), "DNS snapshot", directory=False)) if args.dns_snapshot_file else resolve_dns(args.domain)
        if dns.get("domain") != args.domain:
            raise ValueError(f"DNS snapshot domain mismatch: expected {args.domain}, got {dns.get('domain')}")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = output_root / f"legacy-site-{safe_name(args.domain)}-{timestamp}.tar.gz"
        inputs: list[tuple[str, Path]] = [("webroot", web_root)]
        inputs.extend((f"uploads-{index+1}", path) for index, path in enumerate(uploads))
        inputs.extend((f"config-{index+1}", path) for index, path in enumerate(configs))
        archive_paths(archive, inputs)

        artifacts: dict[str, Any] = {
            "site_archive": {"path": archive.name, "size_bytes": archive.stat().st_size, "sha256": sha256(archive)}
        }
        if args.database_url_env:
            db_dump = output_root / f"legacy-db-{timestamp}.dump"
            artifacts["database_dump"] = capture_database(db_dump, args.database_url_env)
        else:
            artifacts["database_dump"] = {"status": "NOT_REQUESTED", "reason": "legacy DB presence must be explicitly determined"}

        dns_path = output_root / "dns-snapshot.json"
        dns_path.write_text(json.dumps(dns, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifacts["dns_snapshot"] = {"path": dns_path.name, "size_bytes": dns_path.stat().st_size, "sha256": sha256(dns_path)}

        manifest = {
            "schema_version": 1,
            "status": "CAPTURED_NOT_RESTORED",
            "domain": args.domain,
            "captured_at": utc_now(),
            "rollback_owner": rollback_owner,
            "source": {
                "web_root": str(web_root),
                "uploads": [str(path) for path in uploads],
                "configs": [str(path) for path in configs],
            },
            "artifacts": artifacts,
            "restore_rehearsal": {"status": "NOT_RUN"},
            "offsite_copy": {"status": "NOT_REQUESTED"},
            "safety": {
                "mutates_live_site": False,
                "changes_dns": False,
                "stops_services": False,
                "contains_database_credentials": False,
            },
        }
        manifest_path = output_root / "manifest.json"

        destination: Path | None = None
        if args.offsite_dir:
            offsite_root = Path(args.offsite_dir).expanduser().resolve()
            offsite_root.mkdir(parents=True, exist_ok=True)
            destination = offsite_root / output_root.name
            if destination.exists():
                raise ValueError(f"refusing to overwrite existing off-site rollback copy: {destination}")
            manifest["offsite_copy"] = {"status": "COPIED", "path": str(destination)}

        write_manifest(manifest_path, manifest)

        if destination is not None:
            shutil.copytree(output_root, destination)
            copied_manifest = destination / "manifest.json"
            if sha256(copied_manifest) != sha256(manifest_path):
                raise RuntimeError("off-site manifest checksum differs from local manifest")
            for name, spec in artifacts.items():
                if isinstance(spec, dict) and spec.get("path"):
                    local = output_root / spec["path"]
                    remote = destination / spec["path"]
                    if not remote.is_file() or sha256(remote) != sha256(local):
                        raise RuntimeError(f"off-site artifact checksum mismatch: {name}")

        print(f"ROLLBACK_CAPTURE_OK output={output_root}")
        print(f"site_archive_sha256={artifacts['site_archive']['sha256']}")
        print(f"dns_snapshot_sha256={artifacts['dns_snapshot']['sha256']}")
        print("RESULT: CAPTURED_NOT_RESTORED — restore rehearsal is still mandatory before cutover")
        return 0
    except Exception as exc:
        print(f"ROLLBACK_CAPTURE_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
