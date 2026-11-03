#!/usr/bin/env python3
"""Read-only MARINA host inventory: image-ID-only Docker inspect; no secrets, restart or DB queries."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

def command(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=8)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def inventory(repo: Path, backups: Path):
    report = {
        "schema": "marina-runtime-inventory-v1",
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "repo": {"head": None, "branch": None, "dirty_tracked": None},
        "docker": {"available": False, "containers": []},
        "backups": {"directory_present": backups.is_dir(), "files": [], "integrity_checked": False},
        "limitations": [
            "No DB queries, volume checks, backup restore, host HTTPS checks or deploy performed; pg_restore --list checks TOC readability only.",
            "Git HEAD does not establish the running image version; immutable image_id is a local Docker image ID, not a repository commit or registry digest."
        ]
    }
    if repo.is_dir():
        head = command(["git", "-C", str(repo), "rev-parse", "HEAD"])
        branch = command(["git", "-C", str(repo), "branch", "--show-current"])
        tracked = command(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"])
        report["repo"] = {
            "head": head if head and re.fullmatch(r"[a-fA-F0-9]{40}", head) else None,
            "branch": branch if branch and re.fullmatch(r"[a-zA-Z0-9/_+.-]{1,150}", branch) else None,
            "dirty_tracked": bool(tracked) if tracked is not None else None,
        }
    lines = command(["docker", "ps", "--all", "--format", "{{json .}}"])
    if lines is not None:
        report["docker"]["available"] = True
        for line in lines.splitlines():
            try:
                item = json.loads(line)
                name = item.get("Names")
                if not isinstance(name, str) or not re.match(r"^marina[-_]", name, re.I):
                    continue
                # Only the immutable container image ID is read. Never run a
                # general docker inspect: its Environment may contain secrets.
                image_id = command(["docker", "inspect", "--type", "container",
                                    "--format", "{{.Image}}", name])
                if image_id and not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
                    image_id = None
                report["docker"]["containers"].append({
                    "name": name, "image": item.get("Image", ""),
                    "image_id": image_id,
                    "state": item.get("State", ""), "status": item.get("Status", "")
                })
            except (ValueError, TypeError):
                continue
        report["docker"]["containers"].sort(key=lambda c: c["name"])
    if backups.is_dir():
        for entry in backups.iterdir():
            try:
                if (entry.is_symlink() or not entry.is_file() or
                    not entry.name.startswith("marina-") or
                    entry.suffix.lower() not in {".dump", ".backup", ".sql", ".gz"}):
                    continue
                stat = entry.stat()
                # pg_restore --list is read-only: it parses an archive's table
                # of contents without contacting PostgreSQL or extracting data.
                # A valid list is NOT evidence of a successful database restore.
                archive_listing = None
                if entry.suffix.lower() in {".dump", ".backup"}:
                    try:
                        with entry.open("rb") as handle:
                            if handle.read(5) == b"PGDMP":
                                archive_listing = command(["pg_restore", "--list", str(entry)]) is not None
                            else:
                                archive_listing = False
                    except OSError:
                        archive_listing = None
                report["backups"]["files"].append({
                    "filename": entry.name, "size_bytes": stat.st_size,
                    "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "custom_archive_listing_ok": archive_listing
                })
            except OSError:
                continue
        report["backups"]["files"].sort(key=lambda f: f["modified_utc"], reverse=True)
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("/home/agent/marina-smart-demo"))
    parser.add_argument("--backup-dir", type=Path, default=Path("/home/agent/marina-backups"))
    args = parser.parse_args()
    print(json.dumps(inventory(args.repo, args.backup_dir), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
