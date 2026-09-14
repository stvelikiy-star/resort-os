#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS, migration_names_match_exactly

BACKUP_FORMAT = "three-crowns-postgres-backup-v3"
PROPERTY_CODE = "THREE_CROWNS"
EXPECTED_BASELINE_COUNTS = {"rooms": 84, "room_types": 12, "rate_periods": 48}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a JSON object")
    return data


def validate_pre_cutover_backup(
    *,
    backup_file: Path,
    manifest_file: Path,
    offsite_dir: Path,
    restore_evidence_file: Path,
    restore_owner: str,
    max_age_hours: float,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    owner = restore_owner.strip()
    if not owner:
        errors.append("restore owner is required")
    if max_age_hours <= 0:
        errors.append("max_age_hours must be positive")

    try:
        manifest = load_json(manifest_file, "backup manifest")
    except Exception as exc:
        return errors + [str(exc)]

    if manifest.get("format") != BACKUP_FORMAT:
        errors.append(f"backup manifest format must be {BACKUP_FORMAT}")

    try:
        created_at = parse_time(str(manifest.get("created_at") or ""))
        age_hours = (now_utc - created_at).total_seconds() / 3600
        if age_hours < -0.25:
            errors.append("backup timestamp is in the future")
        elif max_age_hours > 0 and age_hours > max_age_hours:
            errors.append(f"backup is stale: age_hours={age_hours:.2f} > {max_age_hours:.2f}")
    except Exception:
        created_at = None
        errors.append("backup manifest created_at must be valid ISO-8601")

    if not backup_file.is_file():
        errors.append(f"backup file missing: {backup_file}")
        actual_sha = ""
    else:
        actual_sha = sha256_file(backup_file)
        if backup_file.name != str(manifest.get("backup_file") or ""):
            errors.append("backup filename does not match manifest")
        if backup_file.stat().st_size != int(manifest.get("size_bytes") or -1):
            errors.append("backup size does not match manifest")
        if actual_sha != str(manifest.get("sha256") or ""):
            errors.append("backup sha256 does not match manifest")

    if manifest.get("property_code") != PROPERTY_CODE:
        errors.append(f"backup property_code must be {PROPERTY_CODE}")

    facts = manifest.get("facts") or {}
    if not isinstance(facts, dict):
        errors.append("backup facts must be an object")
        facts = {}
    counts = facts.get("counts") or {}
    if not isinstance(counts, dict):
        errors.append("backup facts.counts must be an object")
        counts = {}
    for key, expected in EXPECTED_BASELINE_COUNTS.items():
        if counts.get(key) != expected:
            errors.append(f"backup baseline mismatch: {key}={counts.get(key)!r}, expected {expected}")

    database = facts.get("database") or {}
    if not isinstance(database, dict):
        errors.append("backup facts.database must be an object")
        database = {}
    if database.get("migration_history_present") is not True:
        errors.append("backup did not prove Prisma migration history")
    if tuple(database.get("expected_migration_names") or []) != EXPECTED_MIGRATIONS:
        errors.append("backup manifest does not identify the exact current release migration chain")
    applied = database.get("applied_migrations") or []
    if not isinstance(applied, list):
        errors.append("backup applied_migrations must be a list")
        applied = []
    applied_names = [str(row.get("migration_name") or "") for row in applied if isinstance(row, dict)]
    if len(applied_names) != len(applied) or not migration_names_match_exactly(applied_names):
        errors.append("backup applied migration ledger does not exactly match the current release")
    constraints = database.get("critical_constraints") or []
    if not isinstance(constraints, list) or set(map(str, constraints)) != set(CRITICAL_CONSTRAINTS):
        errors.append("backup critical constraint fingerprint does not match the current release")

    if not offsite_dir.is_dir():
        errors.append(f"off-site directory missing: {offsite_dir}")
    else:
        remote_backup = offsite_dir / backup_file.name
        remote_manifest = offsite_dir / manifest_file.name
        if not remote_backup.is_file():
            errors.append(f"off-site backup missing: {remote_backup}")
        elif actual_sha and sha256_file(remote_backup) != actual_sha:
            errors.append("off-site backup sha256 differs from local backup")
        if not remote_manifest.is_file():
            errors.append(f"off-site manifest missing: {remote_manifest}")
        elif sha256_file(remote_manifest) != sha256_file(manifest_file):
            errors.append("off-site manifest differs from local manifest")

    try:
        restore = load_json(restore_evidence_file, "restore evidence")
    except Exception as exc:
        errors.append(str(exc))
        restore = {}
    if restore:
        if restore.get("schema_version") != 1:
            errors.append("restore evidence schema_version must be 1")
        if restore.get("status") != "VERIFIED":
            errors.append("restore evidence status must be VERIFIED")
        if restore.get("property_code") != PROPERTY_CODE:
            errors.append(f"restore evidence property_code must be {PROPERTY_CODE}")
        if restore.get("backup_sha256") != str(manifest.get("sha256") or ""):
            errors.append("restore evidence backup_sha256 does not match backup manifest")
        if restore.get("backup_created_at") != manifest.get("created_at"):
            errors.append("restore evidence backup_created_at does not match backup manifest")
        if restore.get("migration_count") != len(EXPECTED_MIGRATIONS):
            errors.append("restore evidence migration_count does not match current release")
        if restore.get("critical_constraint_count") != len(CRITICAL_CONSTRAINTS):
            errors.append("restore evidence critical_constraint_count does not match current release")
        if restore.get("restored_counts") != counts:
            errors.append("restore evidence counts differ from backup manifest")
        try:
            verified_at = parse_time(str(restore.get("verified_at") or ""))
            if verified_at > now_utc:
                errors.append("restore verified_at cannot be in the future")
            if created_at is not None and verified_at < created_at:
                errors.append("restore verification predates the backup")
        except Exception:
            errors.append("restore evidence verified_at must be valid ISO-8601")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed gate for fresh Three Crowns pre-cutover PostgreSQL backup evidence")
    parser.add_argument("--backup-file", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--offsite-dir", required=True)
    parser.add_argument("--restore-evidence", required=True)
    parser.add_argument("--restore-owner", required=True)
    parser.add_argument("--max-age-hours", type=float, default=6.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    backup_file = Path(args.backup_file).expanduser().resolve()
    manifest_file = Path(args.manifest).expanduser().resolve()
    offsite_dir = Path(args.offsite_dir).expanduser().resolve()
    restore_evidence_file = Path(args.restore_evidence).expanduser().resolve()
    errors = validate_pre_cutover_backup(
        backup_file=backup_file,
        manifest_file=manifest_file,
        offsite_dir=offsite_dir,
        restore_evidence_file=restore_evidence_file,
        restore_owner=args.restore_owner,
        max_age_hours=args.max_age_hours,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print("RESULT: PRE_CUTOVER_BACKUP_GATE_RED", file=sys.stderr)
        return 1

    manifest = load_json(manifest_file, "backup manifest")
    evidence = {
        "schema_version": 1,
        "status": "VERIFIED",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "restore_owner": args.restore_owner.strip(),
        "backup_file": backup_file.name,
        "backup_manifest": manifest_file.name,
        "backup_created_at": manifest.get("created_at"),
        "backup_sha256": manifest.get("sha256"),
        "offsite_dir": str(offsite_dir),
        "restore_evidence": str(restore_evidence_file),
        "migration_count": len(EXPECTED_MIGRATIONS),
        "critical_constraint_count": len(CRITICAL_CONSTRAINTS),
        "safety": {"changes_dns": False, "mutates_database": False, "contains_credentials": False},
    }
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"PRE_CUTOVER_BACKUP_EVIDENCE={output}")

    print(f"BACKUP_SHA256={manifest.get('sha256')}")
    print(f"BACKUP_CREATED_AT={manifest.get('created_at')}")
    print(f"RESTORE_OWNER={args.restore_owner.strip()}")
    print("RESULT: PRE_CUTOVER_BACKUP_GATE_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
