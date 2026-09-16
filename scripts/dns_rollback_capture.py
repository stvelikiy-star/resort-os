#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOMAIN = "3korony.com"
CANONICAL_HOSTS = (
    "3korony.com",
    "api.3korony.com",
    "admin.3korony.com",
    "staff.3korony.com",
    "automation.3korony.com",
)
WEB_TYPES = ("A", "AAAA", "CNAME")
APEX_EXTRA_TYPES = ("NS", "SOA", "MX", "TXT", "CAA")
STATUS_RE = re.compile(r"status:\s*([A-Z]+),")
ALLOWED_STATUS = {"NOERROR", "NXDOMAIN"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_dns_name(value: str) -> str:
    return value.strip().rstrip(".").lower()


def parse_answer_line(line: str) -> tuple[str, int, str, str, str]:
    parts = line.split(None, 4)
    if len(parts) != 5:
        raise ValueError(f"malformed DNS answer line: {line}")
    owner = normalize_dns_name(parts[0])
    if not parts[1].isdigit() or int(parts[1]) < 0:
        raise ValueError(f"invalid DNS TTL: {line}")
    if parts[2].upper() != "IN":
        raise ValueError(f"DNS class must be IN: {line}")
    return owner, int(parts[1]), "IN", parts[3].upper(), parts[4].strip()


def canonical_answer(line: str) -> str:
    owner, ttl, dns_class, record_type, rdata = parse_answer_line(line)
    return f"{owner}. {ttl} {dns_class} {record_type} {rdata}"


def run_dig(args: list[str]) -> str:
    proc = subprocess.run(["dig", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"dig failed: {' '.join(args)}: {(proc.stderr or '').strip()[:300]}")
    return proc.stdout


def authoritative_nameservers(domain: str) -> list[str]:
    raw = run_dig(["+short", "NS", domain])
    nameservers = sorted({normalize_dns_name(line) for line in raw.splitlines() if line.strip()})
    if not nameservers:
        raise RuntimeError(f"no authoritative nameservers discovered for {domain}")
    return nameservers


def query_authoritative(nameserver: str, hostname: str, record_type: str) -> dict[str, Any]:
    raw = run_dig([f"@{nameserver}", "+noall", "+answer", "+comments", hostname, record_type])
    match = STATUS_RE.search(raw)
    if not match:
        raise RuntimeError(f"cannot determine authoritative DNS status for {hostname} {record_type} via {nameserver}")
    status = match.group(1)
    if status not in ALLOWED_STATUS:
        raise RuntimeError(f"authoritative DNS returned {status} for {hostname} {record_type} via {nameserver}")
    direct: list[str] = []
    owner = normalize_dns_name(hostname)
    for raw_line in raw.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";;"):
            continue
        parsed_owner, *_ = parse_answer_line(line)
        if parsed_owner == owner:
            direct.append(canonical_answer(line))
    return {"status": status, "records": sorted(set(direct))}


def consensus_query(hostname: str, record_type: str, nameservers: list[str]) -> dict[str, Any]:
    responses = {ns: query_authoritative(ns, hostname, record_type) for ns in nameservers}
    statuses = {str(item["status"]) for item in responses.values()}
    records = {tuple(item["records"]) for item in responses.values()}
    if len(statuses) != 1 or len(records) != 1:
        raise RuntimeError(f"authoritative DNS disagreement for {hostname} {record_type}")
    return {
        "status": next(iter(statuses)),
        "records": list(next(iter(records))),
        "authoritative": responses,
    }


def capture_snapshot(domain: str = DOMAIN, hosts: tuple[str, ...] = CANONICAL_HOSTS) -> dict[str, Any]:
    domain = normalize_dns_name(domain)
    normalized_hosts = tuple(normalize_dns_name(item) for item in hosts)
    if normalized_hosts != CANONICAL_HOSTS:
        raise ValueError("DNS rollback capture host set must exactly match the current production topology")
    nameservers = authoritative_nameservers(domain)
    host_data: dict[str, Any] = {}
    for hostname in normalized_hosts:
        queries: dict[str, Any] = {}
        for record_type in WEB_TYPES:
            queries[record_type] = consensus_query(hostname, record_type, nameservers)
        if hostname == domain:
            for record_type in APEX_EXTRA_TYPES:
                queries[record_type] = consensus_query(hostname, record_type, nameservers)
        web_statuses = {queries[item]["status"] for item in WEB_TYPES}
        if "NXDOMAIN" in web_statuses and web_statuses != {"NXDOMAIN"}:
            raise RuntimeError(f"inconsistent NXDOMAIN state across web record types for {hostname}")
        direct_web = sorted({line for item in WEB_TYPES for line in queries[item]["records"]})
        if web_statuses == {"NXDOMAIN"}:
            state = "NXDOMAIN"
        elif direct_web:
            state = "PRESENT"
        else:
            state = "NO_WEB_RECORDS"
        host_data[hostname] = {"state": state, "queries": queries, "rollback_records": direct_web}

    apex = host_data[domain]["queries"]
    if not apex["NS"]["records"] or not apex["SOA"]["records"]:
        raise RuntimeError("apex authoritative snapshot must include NS and SOA")

    return {
        "schema_version": 1,
        "kind": "THREE_CROWNS_DNS_ROLLBACK_SNAPSHOT",
        "domain": domain,
        "captured_at": utc_now(),
        "expected_hosts": list(normalized_hosts),
        "authoritative_nameservers": nameservers,
        "hosts": host_data,
        "safety": {"changes_dns": False, "mutates_services": False, "contains_credentials": False},
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture authoritative rollback DNS state for every Three Crowns production hostname without changing DNS")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--offsite-dir", required=True, help="Mounted/restricted off-site destination")
    parser.add_argument("--rollback-owner", required=True)
    args = parser.parse_args()

    try:
        if shutil.which("dig") is None:
            raise RuntimeError("dig is required; resolver fallback is not acceptable rollback evidence")
        owner = args.rollback_owner.strip()
        if not owner:
            raise ValueError("rollback owner is required")
        output = Path(args.output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        if any(output.iterdir()):
            raise ValueError(f"output directory must be empty: {output}")
        offsite_root = Path(args.offsite_dir).expanduser().resolve()
        offsite_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = offsite_root / output.name
        if destination.exists():
            raise ValueError(f"refusing to overwrite off-site DNS rollback evidence: {destination}")

        snapshot = capture_snapshot()
        snapshot_path = output / "dns-rollback-snapshot.json"
        write_json(snapshot_path, snapshot)
        manifest = {
            "schema_version": 1,
            "kind": "THREE_CROWNS_DNS_ROLLBACK_CAPTURE",
            "status": "CAPTURED",
            "captured_at": snapshot["captured_at"],
            "domain": DOMAIN,
            "expected_hosts": list(CANONICAL_HOSTS),
            "rollback_owner": owner,
            "snapshot": {
                "path": snapshot_path.name,
                "size_bytes": snapshot_path.stat().st_size,
                "sha256": sha256(snapshot_path),
            },
            "offsite_copy": {"status": "COPIED", "path": str(destination)},
            "safety": {"changes_dns": False, "mutates_services": False, "contains_credentials": False},
        }
        manifest_path = output / "manifest.json"
        write_json(manifest_path, manifest)
        shutil.copytree(output, destination)
        for filename in ("manifest.json", "dns-rollback-snapshot.json"):
            if sha256(output / filename) != sha256(destination / filename):
                raise RuntimeError(f"off-site DNS rollback evidence differs: {filename}")

        print(f"DNS_ROLLBACK_CAPTURE={output}")
        print(f"DNS_ROLLBACK_OFFSITE={destination}")
        print(f"DNS_ROLLBACK_HOSTS={','.join(CANONICAL_HOSTS)}")
        print("RESULT: DNS_ROLLBACK_CAPTURED_NO_DNS_CHANGES")
        return 0
    except Exception as exc:
        print(f"DNS_ROLLBACK_CAPTURE_BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
