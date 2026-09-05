#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def assert_artifact(root: Path, spec: dict[str, Any], label: str) -> Path:
    path = root / str(spec.get("path") or "")
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    expected_size = int(spec.get("size_bytes") or -1)
    if path.stat().st_size != expected_size:
        raise ValueError(f"{label} size mismatch: expected {expected_size}, got {path.stat().st_size}")
    expected_sha = str(spec.get("sha256") or "")
    actual_sha = sha256(path)
    if actual_sha != expected_sha:
        raise ValueError(f"{label} sha256 mismatch: expected {expected_sha}, got {actual_sha}")
    return path


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"unsafe archive member path: {member.name}")
    archive.extractall(destination)


def sync_verified_manifest(manifest_path: Path, manifest: dict[str, Any]) -> str:
    offsite = manifest.get("offsite_copy") or {}
    if offsite.get("status") != "COPIED":
        return "NOT_COPIED"
    destination = Path(str(offsite.get("path") or "")).expanduser().resolve()
    if not destination.is_dir():
        raise ValueError(f"off-site evidence directory is missing: {destination}")
    copied_manifest = destination / "manifest.json"
    if not copied_manifest.is_file():
        raise ValueError(f"off-site manifest is missing: {copied_manifest}")
    shutil.copy2(manifest_path, copied_manifest)
    if sha256(copied_manifest) != sha256(manifest_path):
        raise ValueError("off-site verified manifest checksum differs from local manifest")
    return "VERIFIED_MANIFEST_SYNCED"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Three Crowns legacy rollback evidence and rehearse non-destructive restore")
    parser.add_argument("evidence_dir")
    parser.add_argument("--mark-verified", action="store_true", help="Update manifest restore_rehearsal after successful verification")
    args = parser.parse_args()

    try:
        root = Path(args.evidence_dir).expanduser().resolve()
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("unsupported rollback manifest schema")
        if manifest.get("status") not in {"CAPTURED_NOT_RESTORED", "RESTORE_VERIFIED"}:
            raise ValueError(f"unexpected rollback status: {manifest.get('status')}")
        if manifest.get("safety", {}).get("mutates_live_site") is not False:
            raise ValueError("manifest does not assert non-destructive live-site capture")

        artifacts = manifest.get("artifacts") or {}
        site_archive = assert_artifact(root, artifacts.get("site_archive") or {}, "site archive")
        dns_snapshot = assert_artifact(root, artifacts.get("dns_snapshot") or {}, "DNS snapshot")
        dns = json.loads(dns_snapshot.read_text(encoding="utf-8"))
        if dns.get("domain") != manifest.get("domain") or not isinstance(dns.get("records"), dict):
            raise ValueError("DNS snapshot does not match manifest domain/records contract")

        with tempfile.TemporaryDirectory(prefix="three-crowns-rollback-") as tmp:
            restore_root = Path(tmp)
            with tarfile.open(site_archive, "r:gz") as archive:
                members = archive.getmembers()
                if not members:
                    raise ValueError("site archive is empty")
                safe_extract(archive, restore_root)
            if not any(restore_root.iterdir()):
                raise ValueError("site archive restore rehearsal produced no files")

        db_spec = artifacts.get("database_dump") or {}
        if db_spec.get("status") == "ABSENT_CONFIRMED":
            db_result = "ABSENT_CONFIRMED"
        elif db_spec.get("status") in {"UNDETERMINED", "NOT_REQUESTED"}:
            db_result = "UNDETERMINED"
        else:
            db_dump = assert_artifact(root, db_spec, "database dump")
            if shutil.which("pg_restore") is None:
                raise ValueError("pg_restore is required to verify a pg_dump custom archive")
            proc = subprocess.run(["pg_restore", "--list", str(db_dump)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if proc.returncode != 0 or not proc.stdout.strip():
                raise ValueError(f"pg_restore --list failed: {proc.stderr.strip()[:500]}")
            db_result = "ARCHIVE_READABLE"

        offsite_result = "UNCHANGED"
        if args.mark_verified:
            manifest["status"] = "RESTORE_VERIFIED"
            manifest["restore_rehearsal"] = {
                "status": "VERIFIED",
                "verified_at": utc_now(),
                "site_archive": "EXTRACTED_TO_TEMPORARY_LOCATION",
                "database_dump": db_result,
                "dns_snapshot": "CHECKSUM_AND_SCHEMA_VERIFIED",
                "note": "Non-destructive rehearsal; live paths and DNS were not modified.",
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            offsite_result = sync_verified_manifest(manifest_path, manifest)

        print(f"ROLLBACK_VERIFY_OK evidence={root}")
        print(f"site_archive_sha256={sha256(site_archive)}")
        print(f"database={db_result}")
        print(f"offsite={offsite_result}")
        print("RESULT: RESTORE_REHEARSAL_VERIFIED" if args.mark_verified else "RESULT: EVIDENCE_VERIFIED_NOT_MARKED")
        return 0
    except Exception as exc:
        print(f"ROLLBACK_VERIFY_FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
