#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pre_cutover_backup_gate import validate_pre_cutover_backup
from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix="three-crowns-precutover-") as tmp:
        root = Path(tmp)
        local = root / "local"
        offsite = root / "offsite"
        local.mkdir()
        offsite.mkdir()

        backup = local / "three-crowns-test.dump"
        backup.write_bytes(b"three-crowns-backup-contract\n")
        created_at = (now - timedelta(minutes=10)).isoformat()
        counts = {
            "rooms": 84,
            "room_types": 12,
            "rate_periods": 48,
            "guests": 5,
            "reservation_requests": 2,
            "reservations": 1,
            "payments": 1,
            "conversations": 0,
            "staff_users": 3,
            "operational_tasks": 0,
            "owner_analytics_snapshots": 0,
            "guest_engagements": 0,
            "audit_logs": 1,
        }
        manifest = {
            "format": "three-crowns-postgres-backup-v3",
            "created_at": created_at,
            "property_code": "THREE_CROWNS",
            "backup_file": backup.name,
            "size_bytes": backup.stat().st_size,
            "sha256": sha256(backup),
            "facts": {
                "counts": counts,
                "database": {
                    "migration_history_present": True,
                    "expected_migration_names": list(EXPECTED_MIGRATIONS),
                    "applied_migrations": [
                        {"migration_name": name, "checksum": f"checksum-{index}"}
                        for index, name in enumerate(EXPECTED_MIGRATIONS)
                    ],
                    "critical_constraints": sorted(CRITICAL_CONSTRAINTS),
                },
            },
        }
        manifest_file = local / "three-crowns-test.manifest.json"
        write_json(manifest_file, manifest)
        (offsite / backup.name).write_bytes(backup.read_bytes())
        (offsite / manifest_file.name).write_bytes(manifest_file.read_bytes())

        restore = {
            "schema_version": 1,
            "status": "VERIFIED",
            "verified_at": (now - timedelta(minutes=5)).isoformat(),
            "backup_sha256": manifest["sha256"],
            "backup_created_at": created_at,
            "property_code": "THREE_CROWNS",
            "migration_count": len(EXPECTED_MIGRATIONS),
            "critical_constraint_count": len(CRITICAL_CONSTRAINTS),
            "restored_counts": counts,
        }
        restore_file = local / "restore-evidence.json"
        write_json(restore_file, restore)

        kwargs = dict(
            backup_file=backup,
            manifest_file=manifest_file,
            offsite_dir=offsite,
            restore_evidence_file=restore_file,
            restore_owner="OWNER",
            max_age_hours=6.0,
            now=now,
        )
        assert validate_pre_cutover_backup(**kwargs) == []

        remote_backup = offsite / backup.name
        original = remote_backup.read_bytes()
        remote_backup.write_bytes(original + b"tamper")
        assert any("off-site backup sha256" in item for item in validate_pre_cutover_backup(**kwargs))
        remote_backup.write_bytes(original)

        stale = dict(manifest)
        stale["created_at"] = (now - timedelta(hours=7)).isoformat()
        write_json(manifest_file, stale)
        (offsite / manifest_file.name).write_bytes(manifest_file.read_bytes())
        assert any("backup is stale" in item for item in validate_pre_cutover_backup(**kwargs))

        write_json(manifest_file, manifest)
        (offsite / manifest_file.name).write_bytes(manifest_file.read_bytes())
        bad_restore = dict(restore)
        bad_restore["backup_sha256"] = "0" * 64
        write_json(restore_file, bad_restore)
        assert any("restore evidence backup_sha256" in item for item in validate_pre_cutover_backup(**kwargs))

        write_json(restore_file, restore)
        no_owner = dict(kwargs)
        no_owner["restore_owner"] = ""
        assert any("restore owner is required" in item for item in validate_pre_cutover_backup(**no_owner))

    print("PASS: pre-cutover backup gate accepts complete evidence and rejects stale/tampered/mismatched evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
