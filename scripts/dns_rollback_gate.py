#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dns_rollback_capture import (
    APEX_EXTRA_TYPES,
    CANONICAL_HOSTS,
    DOMAIN,
    WEB_TYPES,
    canonical_answer,
    normalize_dns_name,
    parse_answer_line,
    sha256,
)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_query(hostname: str, record_type: str, query: Any, nameservers: list[str], errors: list[str]) -> None:
    label = f"{hostname} {record_type}"
    if not isinstance(query, dict):
        errors.append(f"{label}: query missing")
        return
    status = query.get("status")
    if status not in {"NOERROR", "NXDOMAIN"}:
        errors.append(f"{label}: invalid authoritative status {status!r}")
    records = query.get("records")
    if not isinstance(records, list):
        errors.append(f"{label}: records must be a list")
        records = []
    canonical_records: list[str] = []
    for line in records:
        try:
            owner, _, _, _, _ = parse_answer_line(str(line))
            if owner != normalize_dns_name(hostname):
                errors.append(f"{label}: rollback record owner mismatch: {line}")
            canonical_records.append(canonical_answer(str(line)))
        except ValueError as exc:
            errors.append(f"{label}: {exc}")
    if sorted(set(canonical_records)) != sorted(records):
        errors.append(f"{label}: records are not canonical/deduplicated")

    authoritative = query.get("authoritative")
    if not isinstance(authoritative, dict) or set(authoritative) != set(nameservers):
        errors.append(f"{label}: authoritative nameserver response set mismatch")
        return
    for nameserver in nameservers:
        response = authoritative.get(nameserver)
        if not isinstance(response, dict):
            errors.append(f"{label}: response missing for {nameserver}")
            continue
        if response.get("status") != status:
            errors.append(f"{label}: status disagreement at {nameserver}")
        if response.get("records") != records:
            errors.append(f"{label}: record disagreement at {nameserver}")


def validate_snapshot(snapshot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if snapshot.get("schema_version") != 1 or snapshot.get("kind") != "THREE_CROWNS_DNS_ROLLBACK_SNAPSHOT":
        errors.append("unsupported DNS rollback snapshot schema/kind")
    if normalize_dns_name(str(snapshot.get("domain") or "")) != DOMAIN:
        errors.append(f"DNS rollback domain must be {DOMAIN}")
    if tuple(snapshot.get("expected_hosts") or []) != CANONICAL_HOSTS:
        errors.append("DNS rollback host set does not exactly match production topology")
    nameservers = snapshot.get("authoritative_nameservers")
    if not isinstance(nameservers, list) or not nameservers:
        errors.append("authoritative nameserver list is required")
        nameservers = []
    else:
        normalized_ns = [normalize_dns_name(str(item)) for item in nameservers]
        if len(set(normalized_ns)) != len(normalized_ns) or normalized_ns != nameservers:
            errors.append("authoritative nameserver list must be normalized and unique")

    safety = snapshot.get("safety") or {}
    for key in ("changes_dns", "mutates_services", "contains_credentials"):
        if safety.get(key) is not False:
            errors.append(f"unsafe DNS rollback snapshot flag: {key}")

    hosts = snapshot.get("hosts")
    if not isinstance(hosts, dict) or set(hosts) != set(CANONICAL_HOSTS):
        errors.append("DNS rollback snapshot must contain every canonical production hostname exactly once")
        hosts = hosts if isinstance(hosts, dict) else {}

    for hostname in CANONICAL_HOSTS:
        host = hosts.get(hostname)
        if not isinstance(host, dict):
            errors.append(f"{hostname}: host snapshot missing")
            continue
        queries = host.get("queries")
        if not isinstance(queries, dict):
            errors.append(f"{hostname}: query set missing")
            continue
        expected_types = set(WEB_TYPES) | (set(APEX_EXTRA_TYPES) if hostname == DOMAIN else set())
        if set(queries) != expected_types:
            errors.append(f"{hostname}: query types do not match expected topology")
        for record_type in expected_types:
            validate_query(hostname, record_type, queries.get(record_type), nameservers, errors)

        web_queries = [queries.get(item) for item in WEB_TYPES if isinstance(queries.get(item), dict)]
        statuses = {item.get("status") for item in web_queries}
        rollback_records = sorted({line for item in web_queries for line in item.get("records", [])})
        state = host.get("state")
        expected_state = "NXDOMAIN" if statuses == {"NXDOMAIN"} else ("PRESENT" if rollback_records else "NO_WEB_RECORDS")
        if state != expected_state:
            errors.append(f"{hostname}: state mismatch {state!r} != {expected_state!r}")
        if host.get("rollback_records") != rollback_records:
            errors.append(f"{hostname}: rollback_records do not match authoritative query union")

    apex = hosts.get(DOMAIN) if isinstance(hosts, dict) else None
    if isinstance(apex, dict) and isinstance(apex.get("queries"), dict):
        if not apex["queries"].get("NS", {}).get("records"):
            errors.append("apex NS rollback evidence is missing")
        if not apex["queries"].get("SOA", {}).get("records"):
            errors.append("apex SOA rollback evidence is missing")

    return errors


def validate_capture(root: Path, max_age_hours: float, now: datetime | None = None) -> tuple[list[str], dict[str, Any] | None, dict[str, Any] | None]:
    errors: list[str] = []
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        return [f"manifest missing: {manifest_path}"], None, None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"cannot read DNS rollback manifest: {exc}"], None, None
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "THREE_CROWNS_DNS_ROLLBACK_CAPTURE":
        errors.append("unsupported DNS rollback capture schema/kind")
    if manifest.get("status") != "CAPTURED":
        errors.append("DNS rollback capture status must be CAPTURED")
    if manifest.get("domain") != DOMAIN or tuple(manifest.get("expected_hosts") or []) != CANONICAL_HOSTS:
        errors.append("DNS rollback capture domain/host topology mismatch")
    if not str(manifest.get("rollback_owner") or "").strip():
        errors.append("DNS rollback owner is required")
    safety = manifest.get("safety") or {}
    for key in ("changes_dns", "mutates_services", "contains_credentials"):
        if safety.get(key) is not False:
            errors.append(f"unsafe DNS rollback capture flag: {key}")
    if max_age_hours <= 0:
        errors.append("max_age_hours must be positive")
    try:
        captured_at = parse_time(str(manifest.get("captured_at") or ""))
        age_hours = (now_utc - captured_at).total_seconds() / 3600
        if age_hours < -0.25 or age_hours > max_age_hours:
            errors.append(f"DNS rollback capture is not fresh enough: age_hours={age_hours:.2f}")
    except Exception:
        errors.append("DNS rollback captured_at must be valid ISO-8601")

    spec = manifest.get("snapshot") or {}
    snapshot_path = root / str(spec.get("path") or "")
    snapshot: dict[str, Any] | None = None
    if not snapshot_path.is_file():
        errors.append(f"DNS rollback snapshot missing: {snapshot_path}")
    else:
        if snapshot_path.stat().st_size != int(spec.get("size_bytes") or -1):
            errors.append("DNS rollback snapshot size mismatch")
        if sha256(snapshot_path) != str(spec.get("sha256") or ""):
            errors.append("DNS rollback snapshot sha256 mismatch")
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            errors.extend(validate_snapshot(snapshot))
            if snapshot.get("captured_at") != manifest.get("captured_at"):
                errors.append("DNS rollback snapshot captured_at differs from manifest")
        except Exception as exc:
            errors.append(f"cannot read DNS rollback snapshot: {exc}")

    offsite = manifest.get("offsite_copy") or {}
    if offsite.get("status") != "COPIED":
        errors.append("off-site DNS rollback copy is mandatory")
    else:
        offsite_root = Path(str(offsite.get("path") or "")).expanduser().resolve()
        for filename in ("manifest.json", str(spec.get("path") or "")):
            local = root / filename
            remote = offsite_root / filename
            if not local.is_file() or not remote.is_file() or sha256(local) != sha256(remote):
                errors.append(f"off-site DNS rollback evidence mismatch: {filename}")

    return errors, manifest, snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed gate for complete Three Crowns DNS rollback evidence")
    parser.add_argument("evidence_dir")
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.evidence_dir).expanduser().resolve()
    errors, manifest, snapshot = validate_capture(root, args.max_age_hours)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("RESULT: DNS_ROLLBACK_GATE_RED")
        return 1

    assert manifest is not None and snapshot is not None
    evidence = {
        "schema_version": 1,
        "kind": "THREE_CROWNS_DNS_ROLLBACK_EVIDENCE",
        "status": "VERIFIED",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "domain": DOMAIN,
        "expected_hosts": list(CANONICAL_HOSTS),
        "rollback_owner": manifest["rollback_owner"],
        "capture_manifest_sha256": sha256(root / "manifest.json"),
        "snapshot_sha256": manifest["snapshot"]["sha256"],
        "captured_at": manifest["captured_at"],
        "authoritative_nameservers": snapshot["authoritative_nameservers"],
        "rollback_states": {
            hostname: {
                "state": snapshot["hosts"][hostname]["state"],
                "records": snapshot["hosts"][hostname]["rollback_records"],
            }
            for hostname in CANONICAL_HOSTS
        },
        "safety": {"changes_dns": False, "mutates_services": False, "contains_credentials": False},
    }
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"DNS_ROLLBACK_EVIDENCE={output}")
    print(f"DNS_ROLLBACK_OWNER={manifest['rollback_owner']}")
    print(f"DNS_ROLLBACK_HOSTS={','.join(CANONICAL_HOSTS)}")
    print("RESULT: DNS_ROLLBACK_GATE_GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
