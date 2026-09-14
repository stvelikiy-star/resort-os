#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dns_rollback_capture import CANONICAL_HOSTS, DOMAIN, sha256
from dns_rollback_gate import validate_capture, validate_snapshot

NS = ["ns1.example.net", "ns2.example.net"]


def query(status: str, records: list[str]) -> dict:
    return {
        "status": status,
        "records": records,
        "authoritative": {name: {"status": status, "records": records} for name in NS},
    }


def host_snapshot(state: str, *, a: list[str] | None = None, cname: list[str] | None = None, nxdomain: bool = False) -> dict:
    if nxdomain:
        queries = {record_type: query("NXDOMAIN", []) for record_type in ("A", "AAAA", "CNAME")}
        records: list[str] = []
    else:
        a_records = a or []
        cname_records = cname or []
        queries = {
            "A": query("NOERROR", a_records),
            "AAAA": query("NOERROR", []),
            "CNAME": query("NOERROR", cname_records),
        }
        records = sorted(set(a_records + cname_records))
    return {"state": state, "queries": queries, "rollback_records": records}


def build_snapshot(captured_at: str) -> dict:
    apex = host_snapshot("PRESENT", a=["3korony.com. 300 IN A 203.0.113.10"])
    apex["queries"].update(
        {
            "NS": query("NOERROR", [
                "3korony.com. 3600 IN NS ns1.example.net.",
                "3korony.com. 3600 IN NS ns2.example.net.",
            ]),
            "SOA": query("NOERROR", [
                "3korony.com. 3600 IN SOA ns1.example.net. hostmaster.3korony.com. 1 3600 600 1209600 300"
            ]),
            "MX": query("NOERROR", ["3korony.com. 3600 IN MX 10 mail.example.net."]),
            "TXT": query("NOERROR", ["3korony.com. 3600 IN TXT \"v=spf1 -all\""]),
            "CAA": query("NOERROR", []),
        }
    )
    return {
        "schema_version": 1,
        "kind": "THREE_CROWNS_DNS_ROLLBACK_SNAPSHOT",
        "domain": DOMAIN,
        "captured_at": captured_at,
        "expected_hosts": list(CANONICAL_HOSTS),
        "authoritative_nameservers": NS,
        "hosts": {
            "3korony.com": apex,
            "api.3korony.com": host_snapshot("PRESENT", a=["api.3korony.com. 300 IN A 203.0.113.20"]),
            "admin.3korony.com": host_snapshot("NO_WEB_RECORDS"),
            "staff.3korony.com": host_snapshot("NXDOMAIN", nxdomain=True),
            "automation.3korony.com": host_snapshot("PRESENT", cname=["automation.3korony.com. 300 IN CNAME legacy.example.net."]),
        },
        "safety": {"changes_dns": False, "mutates_services": False, "contains_credentials": False},
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc)
    captured_at = (now - timedelta(minutes=10)).isoformat()
    snapshot = build_snapshot(captured_at)
    assert validate_snapshot(snapshot) == []

    bad_hosts = json.loads(json.dumps(snapshot))
    del bad_hosts["hosts"]["staff.3korony.com"]
    assert any("every canonical production hostname" in error for error in validate_snapshot(bad_hosts))

    disagreement = json.loads(json.dumps(snapshot))
    disagreement["hosts"]["api.3korony.com"]["queries"]["A"]["authoritative"][NS[1]]["records"] = []
    assert any("record disagreement" in error for error in validate_snapshot(disagreement))

    with tempfile.TemporaryDirectory(prefix="three-crowns-dns-rollback-") as temp:
        root = Path(temp) / "local"
        offsite_parent = Path(temp) / "offsite"
        offsite = offsite_parent / root.name
        root.mkdir(parents=True)
        offsite.mkdir(parents=True)
        snapshot_path = root / "dns-rollback-snapshot.json"
        write_json(snapshot_path, snapshot)
        manifest = {
            "schema_version": 1,
            "kind": "THREE_CROWNS_DNS_ROLLBACK_CAPTURE",
            "status": "CAPTURED",
            "captured_at": captured_at,
            "domain": DOMAIN,
            "expected_hosts": list(CANONICAL_HOSTS),
            "rollback_owner": "OWNER",
            "snapshot": {
                "path": snapshot_path.name,
                "size_bytes": snapshot_path.stat().st_size,
                "sha256": sha256(snapshot_path),
            },
            "offsite_copy": {"status": "COPIED", "path": str(offsite)},
            "safety": {"changes_dns": False, "mutates_services": False, "contains_credentials": False},
        }
        manifest_path = root / "manifest.json"
        write_json(manifest_path, manifest)
        (offsite / snapshot_path.name).write_bytes(snapshot_path.read_bytes())
        (offsite / manifest_path.name).write_bytes(manifest_path.read_bytes())

        errors, _, _ = validate_capture(root, 24.0, now=now)
        assert errors == [], errors

        original = (offsite / snapshot_path.name).read_bytes()
        (offsite / snapshot_path.name).write_bytes(original + b"tamper")
        errors, _, _ = validate_capture(root, 24.0, now=now)
        assert any("off-site DNS rollback evidence mismatch" in error for error in errors)
        (offsite / snapshot_path.name).write_bytes(original)

        stale_snapshot = build_snapshot((now - timedelta(hours=25)).isoformat())
        write_json(snapshot_path, stale_snapshot)
        manifest["captured_at"] = stale_snapshot["captured_at"]
        manifest["snapshot"]["size_bytes"] = snapshot_path.stat().st_size
        manifest["snapshot"]["sha256"] = sha256(snapshot_path)
        write_json(manifest_path, manifest)
        (offsite / snapshot_path.name).write_bytes(snapshot_path.read_bytes())
        (offsite / manifest_path.name).write_bytes(manifest_path.read_bytes())
        errors, _, _ = validate_capture(root, 24.0, now=now)
        assert any("not fresh enough" in error for error in errors)

    print("PASS: DNS rollback contract covers all production hosts, absence states, authoritative consensus, freshness and off-site integrity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
