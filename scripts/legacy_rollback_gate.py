#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def artifact(root: Path, spec: dict[str, Any], label: str) -> Path:
    path = root / str(spec.get("path") or "")
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    if path.stat().st_size != int(spec.get("size_bytes") or -1):
        raise ValueError(f"{label} size mismatch")
    if sha256(path) != str(spec.get("sha256") or ""):
        raise ValueError(f"{label} sha256 mismatch")
    return path


def validate_dns(dns: dict[str, Any], domain: str) -> None:
    if dns.get("domain") != domain:
        raise ValueError("DNS snapshot domain mismatch")
    records = dns.get("records")
    if not isinstance(records, dict):
        raise ValueError("DNS records missing")
    if "RESOLVER_FALLBACK" in records:
        raise ValueError("resolver fallback is not authoritative DNS/TTL evidence")
    if not records.get("NS") or not records.get("SOA"):
        raise ValueError("authoritative DNS evidence must include NS and SOA")
    if not any(records.get(key) for key in ("A", "AAAA", "CNAME")):
        raise ValueError("DNS evidence must include current web routing (A/AAAA/CNAME)")
    for record_type, lines in records.items():
        if not isinstance(lines, list):
            raise ValueError(f"DNS record family {record_type} is not a list")
        for line in lines:
            parts = str(line).split()
            if len(parts) < 5 or not parts[1].isdigit() or parts[2].upper() != "IN":
                raise ValueError(f"DNS line lacks TTL/class evidence: {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed final gate for legacy 3korony.com rollback evidence")
    parser.add_argument("evidence_dir")
    parser.add_argument("--max-age-hours", type=float, default=24.0, help="Maximum age of rollback capture before cutover")
    args = parser.parse_args()

    try:
        root = Path(args.evidence_dir).expanduser().resolve()
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("unsupported rollback manifest schema")
        if manifest.get("status") != "RESTORE_VERIFIED":
            raise ValueError("rollback restore rehearsal is not verified")
        if not str(manifest.get("rollback_owner") or "").strip():
            raise ValueError("rollback owner is missing")

        captured_at = parse_time(str(manifest.get("captured_at") or ""))
        age_hours = (datetime.now(timezone.utc) - captured_at).total_seconds() / 3600
        if age_hours < -0.25 or age_hours > args.max_age_hours:
            raise ValueError(f"rollback capture is not fresh enough: age_hours={age_hours:.2f}")

        safety = manifest.get("safety") or {}
        for key in ("mutates_live_site", "changes_dns", "stops_services", "contains_database_credentials"):
            if safety.get(key) is not False:
                raise ValueError(f"unsafe rollback evidence flag: {key}")

        decisions = manifest.get("evidence_decisions") or {}
        if decisions.get("authoritative_dns_reviewed") is not True:
            raise ValueError("authoritative DNS/mail review has not been explicitly confirmed")

        source = manifest.get("source") or {}
        if not source.get("uploads") and decisions.get("uploads_absent_confirmed") is not True:
            raise ValueError("uploads/media evidence is ambiguous")
        if not source.get("configs") and decisions.get("config_absent_confirmed") is not True:
            raise ValueError("vhost/runtime config evidence is ambiguous")

        artifacts = manifest.get("artifacts") or {}
        artifact(root, artifacts.get("site_archive") or {}, "site archive")
        dns_path = artifact(root, artifacts.get("dns_snapshot") or {}, "DNS snapshot")
        validate_dns(json.loads(dns_path.read_text(encoding="utf-8")), str(manifest.get("domain") or ""))

        db = artifacts.get("database_dump") or {}
        if db.get("status") == "ABSENT_CONFIRMED":
            if decisions.get("database_absent_confirmed") is not True:
                raise ValueError("database absence is not explicitly confirmed")
        elif db.get("status") in {"UNDETERMINED", "NOT_REQUESTED", None}:
            raise ValueError("legacy database presence is undetermined")
        else:
            artifact(root, db, "database dump")

        rehearsal = manifest.get("restore_rehearsal") or {}
        if rehearsal.get("status") != "VERIFIED" or not rehearsal.get("verified_at"):
            raise ValueError("restore rehearsal evidence is incomplete")

        offsite = manifest.get("offsite_copy") or {}
        if offsite.get("status") != "COPIED":
            raise ValueError("off-site rollback copy is mandatory")
        offsite_root = Path(str(offsite.get("path") or "")).expanduser().resolve()
        offsite_manifest = offsite_root / "manifest.json"
        if not offsite_manifest.is_file():
            raise ValueError("off-site verified manifest is missing")
        if sha256(offsite_manifest) != sha256(manifest_path):
            raise ValueError("off-site manifest is not synchronized with verified local evidence")
        for label, spec in artifacts.items():
            if not isinstance(spec, dict) or not spec.get("path"):
                continue
            local = root / str(spec["path"])
            remote = offsite_root / str(spec["path"])
            if not remote.is_file() or sha256(remote) != sha256(local):
                raise ValueError(f"off-site artifact mismatch: {label}")

        print("LEGACY_ROLLBACK_GATE_OK")
        print(f"domain={manifest.get('domain')}")
        print(f"capture_age_hours={age_hours:.2f}")
        print("RESULT: CUTOVER_ROLLBACK_PREREQUISITE_GREEN")
        return 0
    except Exception as exc:
        print(f"LEGACY_ROLLBACK_GATE_BLOCKED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
