#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOMS_PATH = Path("data-intake/rooms.csv")
CHECKLIST_PATH = Path("data-intake/owner-room-checklist.json")
EXPECTED_ROOM_COUNT = 84
EXPECTED_ROOM_TYPE_COUNT = 12
EXPECTED_CHECKLIST_QUESTIONS = 13
UNKNOWN = "UNKNOWN"
# Operational state is intentionally absent: it is runtime PMS truth, not a
# permanent physical-room fact. These unknowns are grouped for review/enrichment.
OWNER_LOCATION_FIELDS = ("building_or_zone", "floor")
OWNER_POLICY_FIELDS = ("capacity_children",)


def checksum(path: Path = ROOMS_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rooms(path: Path = ROOMS_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_checklist(path: Path = CHECKLIST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def group_issue_id(code: str, field: str, group: str) -> str:
    return f"GROUP:{code}:{field}:{group}"


def audit_checklist(checklist: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    questions = checklist.get("questions")
    if not isinstance(questions, list):
        return ["owner checklist questions must be an array"]
    if len(questions) != EXPECTED_CHECKLIST_QUESTIONS:
        errors.append(
            f"owner checklist question count mismatch: expected {EXPECTED_CHECKLIST_QUESTIONS}, found {len(questions)}"
        )
    ids = [str(item.get("id") or "").strip() for item in questions if isinstance(item, dict)]
    if any(not item for item in ids):
        errors.append("owner checklist contains empty question id")
    if len(ids) != len(set(ids)):
        errors.append("owner checklist contains duplicate question ids")
    for item in questions:
        if not isinstance(item, dict):
            errors.append("owner checklist question must be an object")
            continue
        if item.get("priority") not in {"P0", "P1"}:
            errors.append(f"owner checklist {item.get('id')}: priority must be P0 or P1")
        if not str(item.get("group") or "").strip() or not str(item.get("question") or "").strip():
            errors.append(f"owner checklist {item.get('id')}: group/question is required")
    source = checklist.get("source")
    if not isinstance(source, dict) or not source.get("spreadsheet_id") or source.get("sheet") != "OWNER_CHECKLIST":
        errors.append("owner checklist must retain Drive spreadsheet provenance")
    return errors


def audit_rooms(rooms: list[dict[str, str]]) -> tuple[list[str], list[dict[str, Any]]]:
    structural_errors: list[str] = []
    issues: list[dict[str, Any]] = []

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

    empty_beds: dict[str, list[str]] = defaultdict(list)
    bed_legend_rooms: list[str] = []
    unknown_groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    for row in rooms:
        room_code = row.get("room_code", "").strip()
        room_type = row.get("room_type", "").strip()
        if not room_type:
            structural_errors.append(f"room {room_code or '<EMPTY>'}: room_type is empty")
            continue

        notes = row.get("notes", "").strip()
        notes_lower = notes.lower()
        if "confirm" in notes_lower:
            issues.append({
                "id": f"{room_code}:CONFIRM_NOTE:notes",
                "room_codes": [room_code],
                "severity": "BLOCKER",
                "code": "CONFIRM_NOTE",
                "field": "notes",
                "group": room_type,
                "value": notes,
                "reason": "Source intake explicitly marks this value for confirmation.",
            })
        if "inferred" in notes_lower:
            issues.append({
                "id": f"{room_code}:INFERRED_VALUE:notes",
                "room_codes": [room_code],
                "severity": "BLOCKER",
                "code": "INFERRED_VALUE",
                "field": "notes",
                "group": room_type,
                "value": notes,
                "reason": "At least one value was inferred rather than directly owner-confirmed.",
            })
        if "decode key required" in notes_lower:
            bed_legend_rooms.append(room_code)

        if not row.get("bed_configuration", "").strip():
            empty_beds[room_type].append(room_code)

        for field in OWNER_LOCATION_FIELDS + OWNER_POLICY_FIELDS:
            value = row.get(field, "").strip()
            if not value or value.upper() == UNKNOWN:
                severity = "REVIEW" if field in OWNER_LOCATION_FIELDS else "POLICY_REVIEW"
                unknown_groups[(severity, field, room_type)].append(room_code)

    if bed_legend_rooms:
        issues.append({
            "id": "GLOBAL:BED_LEGEND_REQUIRED:bed_configuration",
            "room_codes": sorted(bed_legend_rooms),
            "severity": "REVIEW",
            "code": "BED_LEGEND_REQUIRED",
            "field": "bed_configuration",
            "group": "GLOBAL",
            "value": "1сп / 2сп / д / кр / крк / variants",
            "reason": "The source preserves bed abbreviations but the internal legend is not owner-confirmed.",
        })

    for room_type, affected in sorted(empty_beds.items()):
        issues.append({
            "id": group_issue_id("EMPTY_BED_CONFIGURATION", "bed_configuration", room_type),
            "room_codes": sorted(affected),
            "severity": "REVIEW",
            "code": "EMPTY_BED_CONFIGURATION",
            "field": "bed_configuration",
            "group": room_type,
            "value": "",
            "reason": "One or more owner-facing room labels have no bed configuration in canonical intake.",
        })

    for (severity, field, room_type), affected in sorted(unknown_groups.items()):
        issues.append({
            "id": group_issue_id("UNKNOWN_FIELD", field, room_type),
            "room_codes": sorted(affected),
            "severity": severity,
            "code": "UNKNOWN_FIELD",
            "field": field,
            "group": room_type,
            "value": UNKNOWN,
            "reason": (
                "Owner checklist requires location confirmation for this group."
                if severity == "REVIEW"
                else "Owner checklist asks for an explicit child/additional-place policy; UNKNOWN is allowed only after that answer."
            ),
        })

    seen_ids: set[str] = set()
    for item in issues:
        if item["id"] in seen_ids:
            structural_errors.append(f"duplicate review issue id: {item['id']}")
        seen_ids.add(item["id"])

    return structural_errors, issues


def report(
    rooms: list[dict[str, str]],
    errors: list[str],
    issues: list[dict[str, Any]],
    checklist: dict[str, Any],
) -> dict[str, Any]:
    severity = Counter(item["severity"] for item in issues)
    issue_codes = Counter(item["code"] for item in issues)
    questions = checklist["questions"]
    return {
        "register": {
            "path": str(ROOMS_PATH),
            "sha256": checksum(),
            "room_count": len(rooms),
            "unique_room_codes": len({row.get("room_code", "").strip() for row in rooms}),
            "room_type_count": len({row.get("room_type", "").strip() for row in rooms if row.get("room_type", "").strip()}),
        },
        "structural_errors": errors,
        "owner_checklist": {
            "source_spreadsheet_id": checklist["source"]["spreadsheet_id"],
            "source_sheet": checklist["source"]["sheet"],
            "question_count": len(questions),
            "question_ids": [item["id"] for item in questions],
            "captured_status": (
                "HISTORICAL DRIVE SNAPSHOT: ROOMS_IMPORT owner_confirmed=NO and OWNER_CHECKLIST answers blank at capture time; "
                "production authority is the later checksum-bound approval when its verifier passes"
            ),
        },
        "owner_review": {
            "approved": None,
            "blocker_count": severity.get("BLOCKER", 0),
            "review_group_count": severity.get("REVIEW", 0),
            "policy_review_group_count": severity.get("POLICY_REVIEW", 0),
            "issue_count": len(issues),
            "issue_codes": dict(sorted(issue_codes.items())),
            "issues": issues,
        },
        "truth_boundary": (
            "Canonical 84-room data requires checksum-bound owner-approval verification before production reconciliation; "
            "acknowledged optional UNKNOWN values are not inferred."
        ),
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
    issues: list[dict[str, Any]],
    checklist: dict[str, Any],
) -> list[str]:
    result = list(errors)
    if approval.get("status") != "OWNER_APPROVED":
        result.append("approval.status must be OWNER_APPROVED")
        return result

    if approval.get("rooms_sha256") != checksum():
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

    review_ids = sorted(item["id"] for item in issues if item["severity"] in {"REVIEW", "POLICY_REVIEW"})
    acknowledged = approval.get("reviewed_issue_ids")
    if not isinstance(acknowledged, list):
        result.append("approval.reviewed_issue_ids must be an array")
    elif sorted(str(item) for item in acknowledged) != review_ids:
        result.append("approval.reviewed_issue_ids must exactly acknowledge every current REVIEW/POLICY_REVIEW group")

    checklist_ids = sorted(str(item["id"]) for item in checklist["questions"])
    resolved_questions = approval.get("resolved_question_ids")
    if not isinstance(resolved_questions, list):
        result.append("approval.resolved_question_ids must be an array")
    elif sorted(str(item) for item in resolved_questions) != checklist_ids:
        result.append("approval.resolved_question_ids must exactly cover all current Drive OWNER_CHECKLIST P0/P1 questions")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Three Crowns owner room-register review")
    parser.add_argument("--format", choices=("summary", "json"), default="summary")
    parser.add_argument("--approval")
    parser.add_argument("--require-owner-approved", action="store_true")
    args = parser.parse_args()

    rooms = load_rooms()
    checklist = load_checklist()
    structural_errors, issues = audit_rooms(rooms)
    structural_errors.extend(audit_checklist(checklist))
    data = report(rooms, structural_errors, issues, checklist)

    approval: dict[str, Any] | None = None
    approval_errors: list[str] = []
    approval_verified = False
    if args.require_owner_approved:
        if not args.approval:
            approval_errors = ["--approval is required with --require-owner-approved"]
        else:
            try:
                approval = json.loads(Path(args.approval).read_text(encoding="utf-8"))
                approval_errors = validate_owner_approval(approval, rooms, structural_errors, issues, checklist)
                approval_verified = not approval_errors
            except (OSError, json.JSONDecodeError) as exc:
                approval_errors = [f"approval evidence could not be loaded: {exc}"]

    data["owner_review"]["approved"] = approval_verified if args.require_owner_approved else None
    if approval is not None:
        data["owner_review"]["approval_evidence"] = {
            "status": approval.get("status"),
            "rooms_sha256": approval.get("rooms_sha256"),
            "room_count": approval.get("room_count"),
            "approved_by": approval.get("approved_by"),
            "approved_at": approval.get("approved_at"),
            "evidence_ref": approval.get("evidence_ref"),
        }

    if args.format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"REGISTER: rooms={data['register']['room_count']} unique={data['register']['unique_room_codes']} room_types={data['register']['room_type_count']}")
        print(f"SHA256: {data['register']['sha256']}")
        print(f"STRUCTURAL_ERRORS: {len(structural_errors)}")
        print(f"DRIVE_OWNER_QUESTIONS: {data['owner_checklist']['question_count']}")
        print(f"OWNER_BLOCKERS: {data['owner_review']['blocker_count']}")
        print(f"OWNER_REVIEW_GROUPS: {data['owner_review']['review_group_count']}")
        print(f"OWNER_POLICY_REVIEW_GROUPS: {data['owner_review']['policy_review_group_count']}")
        for code, count in data["owner_review"]["issue_codes"].items():
            print(f"ISSUE: {code}={count}")
        if args.require_owner_approved:
            print(f"OWNER_APPROVED: {'true' if approval_verified else 'false'}")
            print("DRIVE_CAPTURE: historical provenance retained; checksum-bound approval is current V1 authority")
            print(
                "TRUTH: canonical 84-room register is owner-approved for V1; acknowledged optional UNKNOWN values remain unfilled"
                if approval_verified
                else "TRUTH: canonical production authority has not passed checksum-bound approval verification"
            )
        else:
            print("OWNER_APPROVED: unverified (no approval evidence was required for this report)")
            print("DRIVE_CAPTURE: historical provenance retained; this report alone does not authorize production")
            print("TRUTH: checksum-bound approval must be verified before production reconciliation")

    if structural_errors:
        for item in structural_errors:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1

    if args.require_owner_approved:
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
