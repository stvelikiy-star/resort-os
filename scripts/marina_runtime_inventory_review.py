#!/usr/bin/env python3
"""Interpret read-only MARINA host inventory without declaring production ready.

This script consumes metadata ONLY. It does not connect to Docker or any network.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

SCHEMA = "marina-runtime-inventory-v1"

def review(data: dict) -> dict:
    findings = []
    if data.get("schema") != SCHEMA or data.get("read_only") is not True:
        findings.append("Unrecognized or non-read-only inventory")
    repo = data.get("repo") or {}
    docker = data.get("docker") or {}
    backups = data.get("backups") or {}
    if not repo.get("head"):
        findings.append("Git HEAD unavailable")
    if repo.get("dirty_tracked") is None:
        findings.append("Git tracked-file state unknown")
    elif repo.get("dirty_tracked"):
        findings.append("Tracked files modified; worktree differs from HEAD")
    if docker.get("available") is not True:
        findings.append("Docker inventory unavailable")
    containers = docker.get("containers")
    if not isinstance(containers, list) or not containers:
        findings.append("No MARINA containers identified")
        containers = []
    for item in containers:
        name = item.get("name", "<unnamed>") if isinstance(item, dict) else "<invalid>"
        if not isinstance(item, dict) or item.get("state") != "running":
            findings.append(f"Container not reported running: {name}")
        elif not item.get("image_id"):
            findings.append(f"Immutable image ID unavailable: {name}")
    if backups.get("directory_present") is not True:
        findings.append("Backup directory not present")
    files = backups.get("files") or []
    if not files:
        findings.append("No matching backup files listed")
    elif not any(
        isinstance(item, dict) and item.get("custom_archive_listing_ok") is True
        for item in files
    ):
        findings.append("No PostgreSQL custom backup with a verified readable archive TOC")
    # TOC readability is not successful database restoration.
    # Metadata presence is not evidence of validity. Never emit READY or PASS.
    return {
        "schema": "marina-inventory-review-v1",
        "status": "INCOMPLETE" if findings else "INVENTORY_METADATA_COLLECTED",
        "release_approved": False,
        "pms_accepted": False,
        "backup_restored": False,
        "findings": findings,
        "next_required": [
            "Verify running image provenance against recorded Git SHA and build artifacts",
            "Verify separate Docker volumes, networks, secret boundaries and live health",
            "Validate backup and restore into a disposable database",
            "Execute role/permission, PMS and provider E2E on the identified environment"
        ]
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        parser.error("Expected a JSON object")
    print(json.dumps(review(data), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
