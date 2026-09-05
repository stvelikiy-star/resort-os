#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from room_register_review import (
    EXPECTED_CHECKLIST_QUESTIONS,
    EXPECTED_ROOM_COUNT,
    audit_checklist,
    audit_rooms,
    load_checklist,
    load_rooms,
    validate_owner_approval,
)

APPROVAL_PATH = Path("data-intake/room-register-owner-approval.json")


def main() -> None:
    rooms = load_rooms()
    checklist = load_checklist()
    errors, issues = audit_rooms(rooms)
    errors.extend(audit_checklist(checklist))
    assert errors == [], errors
    assert len(rooms) == EXPECTED_ROOM_COUNT
    assert len({row['room_code'].strip() for row in rooms}) == EXPECTED_ROOM_COUNT
    assert len(checklist['questions']) == EXPECTED_CHECKLIST_QUESTIONS

    blockers = [item for item in issues if item['severity'] == 'BLOCKER']
    reviews = [item for item in issues if item['severity'] == 'REVIEW']
    policy_reviews = [item for item in issues if item['severity'] == 'POLICY_REVIEW']
    assert blockers == [], f'owner-approved canonical register must contain zero BLOCKER issues: {blockers}'
    assert reviews, 'optional owner-review groups remain intentionally acknowledged rather than invented'
    assert policy_reviews, 'child/additional-place policy remains intentionally non-numeric unless configured'
    assert not any(item['code'] in {'CONFIRM_NOTE', 'INFERRED_VALUE'} for item in issues)
    assert any(item['code'] == 'EMPTY_BED_CONFIGURATION' for item in reviews)
    assert any(item['code'] == 'BED_LEGEND_REQUIRED' for item in reviews)
    assert all(item['field'] != 'operational_status' for item in issues), (
        'runtime PMS status must not be part of permanent owner room-register approval'
    )

    approval = json.loads(APPROVAL_PATH.read_text(encoding='utf-8'))
    approval_errors = validate_owner_approval(approval, rooms, errors, issues, checklist)
    assert approval_errors == [], approval_errors

    wrong_checksum = dict(approval)
    wrong_checksum['rooms_sha256'] = '0' * 64
    assert any(
        'does not match current' in item
        for item in validate_owner_approval(wrong_checksum, rooms, errors, issues, checklist)
    )

    missing_review = dict(approval)
    missing_review['reviewed_issue_ids'] = approval['reviewed_issue_ids'][:-1]
    assert any(
        'must exactly acknowledge every current REVIEW/POLICY_REVIEW group' in item
        for item in validate_owner_approval(missing_review, rooms, errors, issues, checklist)
    )

    missing_question = dict(approval)
    missing_question['resolved_question_ids'] = approval['resolved_question_ids'][:-1]
    assert any(
        'must exactly cover all current Drive OWNER_CHECKLIST' in item
        for item in validate_owner_approval(missing_question, rooms, errors, issues, checklist)
    )

    downgraded = dict(approval)
    downgraded['status'] = 'NOT_APPROVED'
    assert any(
        'status must be OWNER_APPROVED' in item
        for item in validate_owner_approval(downgraded, rooms, errors, issues, checklist)
    )

    print(
        f'ROOM_REGISTER_REVIEW_TEST_OK blockers={len(blockers)} reviews={len(reviews)} '
        f'policy_reviews={len(policy_reviews)} checklist_questions={len(checklist["questions"])} '
        'owner_approved=true'
    )


if __name__ == '__main__':
    main()
