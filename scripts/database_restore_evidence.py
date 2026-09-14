#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS


def main() -> int:
    parser = argparse.ArgumentParser(description="Run database_restore_verify.py and emit machine evidence only after a successful clean restore")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    backup_path = os.environ.get("BACKUP_FILE", "").strip()
    manifest_path = os.environ.get("BACKUP_MANIFEST", "").strip()
    restore_url = os.environ.get("RESTORE_DATABASE_URL", "").strip()
    if not backup_path or not restore_url:
        print("BACKUP_FILE and RESTORE_DATABASE_URL are required", file=sys.stderr)
        return 2
    backup = Path(backup_path).expanduser().resolve()
    manifest_file = Path(manifest_path).expanduser().resolve() if manifest_path else backup.with_suffix(".manifest.json")
    if not manifest_file.is_file():
        print(f"Backup manifest not found: {manifest_file}", file=sys.stderr)
        return 2

    verifier = Path(__file__).with_name("database_restore_verify.py")
    completed = subprocess.run(
        [sys.executable, str(verifier)],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0 or "RESTORE_VERIFICATION=SUCCESS" not in completed.stdout:
        print("RESULT: RESTORE_EVIDENCE_NOT_EMITTED", file=sys.stderr)
        return completed.returncode or 1

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    facts = manifest.get("facts") or {}
    counts = facts.get("counts") or {}
    evidence = {
        "schema_version": 1,
        "status": "VERIFIED",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "backup_sha256": manifest.get("sha256"),
        "backup_created_at": manifest.get("created_at"),
        "property_code": manifest.get("property_code"),
        "migration_count": len(EXPECTED_MIGRATIONS),
        "critical_constraint_count": len(CRITICAL_CONSTRAINTS),
        "restored_counts": counts,
        "verifier": "scripts/database_restore_verify.py",
        "safety": {
            "restores_into_explicit_restore_database": True,
            "changes_dns": False,
            "contains_database_credentials": False,
        },
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RESTORE_EVIDENCE_FILE={output}")
    print("RESULT: RESTORE_EVIDENCE_VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
