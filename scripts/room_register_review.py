#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOMS_PATH = Path("data-intake/rooms.csv")
EXPECTED_ROOM_COUNT = 84
EXPECTED_ROOM_TYPE_COUNT = 12
UNKNOWN = "UNKNOWN"
BLOCKER_CODES = {"CONFIRM_NOTE", "INFERRED_VALUE"}
REVIEW_FIELDS = ("building_or_zone", "floor", "capacity_children", "operational_status")


def read_bytes(path: Path = ROOMS_PATH) -> bytes:
    return path.read_bytes()


def checksum(path: Path = ROOMS_PATH) -> str:
    return hashlib.sha256(read_bytes(path)).hexdigest()


def load_rooms(path: Path = ROOMS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def issue_id(room_code: str, code: str, field: str) -> str:
    safe_room = room_code.strip() or "<EMPTY>"
    return f"{safe_room}:{code}:{field}"


def audit_rooms(rooms: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    structural_errors: list[str] = []
    issues: list[dict[str, str]] = []

    if len(rooms) != EXPECTED_ROOM_COUNT:
        structural_errors.append(f"room count mismatch: expected {EXPECTED_ROOM_COUNT}, found {len(rooms)}")

    codes = [row.get("room_code", "").strip() for row in rooms]
    if any(not code for code in codes):
        structural_errors.append("empty room_code exists")
    duplicates = sorted(code for code, count in Counter(codes).items() if code and count > 1)
    if duplicates:
        structural_errors.append("duplicate room_code: " + ", ".join(duplicates))

    room_types = {row.get("room_type", "").strip() for row in rooms if row.get("room_type", "").strip()}
    if len(room_types) != EXPECTED_ROOM_TYPE_COUNT:
        structural_errors.append(
            f"room type count mismatch: expected {EXPECTED_ROOM_TYPE_COUNT}, found {len(room_types)}"
        )

    for row in rooms:
        room_code = row.get("room_code", "").strip()
        room_type = row.get("room_type", "").strip()
        if not room_type:
            structural_errors.append(f"room {room_code or '<EMPTY>'}: room_type is empty")

        notes = row.get("notes", "").strip()
        notes_lower = notes.lower()
        if "confirm" in notes_lower:
            issues.append({
                "id": issue_id(room_code, "CONFIRM_NOTE", "notes"),
                "room_code": room_code,
                "severity": "BLOCKER",
                "code": "CONFIRM_NOTE",
                "field": "notes",
                "value": notes,
                "reason": "Source intake explicitly marks this value for confirmation.",
            })
        if "inferred" in notes_lower:
            issues.append({
                "id": issue_id(room_code, "INFERRED_VALUE", "notes"),
                "room_code": room_code,
                "severity": "BLOCKER",
                "code": "INFERRED_VALUE",
                "field": "notes",
                "value": notes,
                "reason": "At least one value was inferred rather than directly owner-confirmed.",
            })
        if "decode key required" in notes_lower:
            issues.append({
                "id": issue_id(room_code, "BED_LEGEND_REQUIRED", "bed_configuration"),
                "room_code": room_code,
                "severity": "REVIEW",
                "code": "BED_LEGEND_REQUIRED",
                "field": "bed_configuration",
                "value": row.get("bed_configuration", "").strip(),
                "reason": "Bed abbreviations are preserved but their semantic legend is not owner-confirmed.",
            })

        bed = row.get("bed_configuration", "").strip()
        if not bed:
            issues.append({
                "id": issue_id(room_code, "EMPTY_BED_CONFIGURATION", "bed_configuration"),
                "room_code": room_code,
                "severity": "REVIEW",
                "code": "EMPTY_BED_CONFIGURATION",
                "field": "bed_configuration",
                "value": "",
                "reason": "Owner-facing room label has no bed configuration in canonical intake.",
            })

        for field in REVIEW_FIELDS:
            value = row.get(field, "").strip()
            if not value or value.upper() == UNKNOWN:
                issues.append({
                    "id": issue_id(room_code, "UNKNOWN_FIELD", field),
                    "room_code": room_code,
                    "severity": "REVIEW",
                    "code": "UNKNOWN_FIELD",
                    "field": field,
                    "value": value or "<EMPTY>",
                    "reason": "Canonical intake does not contain an owner-confirmed operational value.",
                })

    seen_ids: set[str] = set()
    for item in issues:
        if item["id"] in seen_ids:
            structural_errors.append(f"duplicate review issue id: {item['id']}")
        seen_ids.add(item["id"])

    return structural_errors, issues


def report(rooms: list[dict[str, str]], errors: list[str], issues: list[dict[str, str]]) -> dict[str, Any]:
    severity = Counter(item["severity"] for item in issues)
    issue_codes = Counter(item["code"] for item in issues)
    return {
        "register": {
            "path": str(ROOMS_PATH),
            "sha256": checksum(),
            "room_count": len(rooms),
            "unique_room_codes": len({row.get("room_code", "").strip() for row in rooms}),
            "room_type_count": len({row.get("room_type", "").strip() for row in rooms}),
        },
        "structural_errors": errors,
        "owner_review": {
            "approved": False,
            "blocker_count": severity.get("BLOCKER", 0),
            "review_count": severity.get("REVIEW", 0),
            "issue_count": len(issues),
            "issue_codes": dict(sorted(issue_codes.items())),
            "issues": issues,
        },
        "truth_boundary": "84 unique development rows != owner-approved physical production register",
    }


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_owner_approval(
    approval: dict[str, Any],
    rooms: list[dict[str, str]],
    errors: list[str],
    issues: list[dict[str, str]],
) -> list[str]:
    result = list(errors)
    if approval.get("status") != "OWNER_APPROVED":
        result.append("approval.status must be OWNER_APPROVED")
        return result

    expected_sha = checksum()
    if approval.get("rooms_sha256") != expected_sha:
        result.append("approval.rooms_sha256 does not match current data-intake/rooms.csv")
    if approval.get("room_count") != len(rooms) or len(rooms) != EXPECTED_ROOM_COUNT:
        result.append(f"approval.room_count must match exact current count {EXPECTED_ROOM_COUNT}")

    approved_by = str(approval.get("approved_by") or "").strip()
    evidence_ref = str(approval.get("evidence_ref") or "").strip()
    approved_at = str(approval.get("approved_at") or "").strip()
    if not approved_by:
        result.append("approval.approved_by is required")
    if not evidence_ref:
        result.append("approval.evidence_ref is required")
    if not approved_at:
        result.append("approval.approved_at is required")
    else:
        try:
            if parse_time(approved_at) > datetime.now(timezone.utc):
                result.append("approval.approved_at cannot be in the future")
        except (ValueError, TypeError):
            result.append("approval.approved_at must be ISO-8601")

    blockers = sorted(item["id"] for item in issues if item["severity"] == "BLOCKER")
    if blockers:
        result.append(
            "canonical register still has BLOCKER issues that must be corrected in rooms.csv before owner approval: "
            + ", ".join(blockers)
        )

    review_ids = sorted(item["id"] for item in issues if item["severity"] == "REVIEW")
    acknowledged = approval.get("reviewed_issue_ids")
    if not isinstance(acknowledged, list):
        result.append("approval.reviewed_issue_ids must be an array")
    elif sorted(str(item) for item in acknowledged) != review_ids:
        result.append("approval.reviewed_issue_ids must exactly acknowledge every current REVIEW issue")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Three Crowns owner room-register review")
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    parser.add_argument("--approval")
    parser.add_argument("--require-owner-approved", action="store_true")
    args = parser.parse_args()

    rooms = load_rooms()
    structural_errors, issues = audit_rooms(rooms)
    data = report(rooms, structural_errors, issues)

    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"REGISTER: rooms={data['register']['room_count']} unique={data['register']['unique_room_codes']} room_types={data['register']['room_type_count']}")
        print(f"SHA256: {data['register']['sha256']}")
        print(f"STRUCTURAL_ERRORS: {len(structural_errors)}")
        print(f"OWNER_BLOCKERS: {data['owner_review']['blocker_count']}")
        print(f"OWNER_REVIEW_ITEMS: {data['owner_review']['review_count']}")
        for code, count in data["owner_review"]["issue_codes"].items():
            print(f"ISSUE: {code}={count}")
        print("OWNER_APPROVED: false")
        print("TRUTH: 84 unique development rows do not equal owner-approved physical production register")

    if structural_errors:
        for item in structural_errors:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1

    if args.require_owner_approved:
        if not args.approval:
            print("FAIL: --approval is required with --require-owner-approved", file=sys.stderr)
            return 1
        approval = json.loads(Path(args.approval).read_text(encoding="utf-8"))
        approval_errors = validate_owner_approval(approval, rooms, structural_errors, issues)
        if approval_errors:
            for item in approval_errors:
                print(f"FAIL: {item}", file=sys.stderr)
            print("RESULT: OWNER ROOM REGISTER NOT APPROVED", file=sys.stderr)
            return 1
        print("RESULT: OWNER ROOM REGISTER APPROVED")
        return 0

    print("RESULT: OWNER REVIEW REPORT GENERATED; PRODUCTION APPROVAL NOT IMPLIED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
