#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from room_register_review import (
    EXPECTED_CHECKLIST_QUESTIONS,
    EXPECTED_ROOM_COUNT,
    audit_checklist,
    audit_rooms,
    checksum,
    load_checklist,
    load_rooms,
    validate_owner_approval,
)


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
    assert blockers, 'current canonical intake must stay fail-closed while explicit CONFIRM/inferred values remain'
    assert reviews, 'current canonical intake is expected to contain owner-review groups'
    assert policy_reviews, 'current checklist requires an explicit child/additional-place policy answer'
    assert any(item['code'] == 'CONFIRM_NOTE' for item in blockers)
    assert any(item['code'] == 'INFERRED_VALUE' for item in blockers)
    assert any(item['code'] == 'EMPTY_BED_CONFIGURATION' for item in reviews)
    assert any(item['code'] == 'BED_LEGEND_REQUIRED' for item in reviews)
    assert all(item['field'] != 'operational_status' for item in issues), (
        'runtime PMS status must not be part of permanent owner room-register approval'
    )

    not_approved = {
        'status': 'NOT_APPROVED',
        'rooms_sha256': checksum(),
        'room_count': len(rooms),
        'approved_by': None,
        'approved_at': None,
        'evidence_ref': None,
        'reviewed_issue_ids': [],
        'resolved_question_ids': [],
    }
    approval_errors = validate_owner_approval(not_approved, rooms, errors, issues, checklist)
    assert any('status must be OWNER_APPROVED' in item for item in approval_errors)

    # Positive path unit-test only: simulate corrected BLOCKER rows and explicit
    # owner resolution of every current grouped review + every captured Drive
    # OWNER_CHECKLIST P0/P1 question. This is not external owner evidence.
    synthetic_non_blockers = [item for item in issues if item['severity'] != 'BLOCKER']
    required_review_ids = sorted(
        item['id'] for item in synthetic_non_blockers if item['severity'] in {'REVIEW', 'POLICY_REVIEW'}
    )
    checklist_ids = sorted(item['id'] for item in checklist['questions'])
    synthetic_approval = {
        'status': 'OWNER_APPROVED',
        'rooms_sha256': checksum(),
        'room_count': len(rooms),
        'approved_by': 'SYNTHETIC_TEST_ONLY',
        'approved_at': datetime.now(timezone.utc).isoformat(),
        'evidence_ref': 'synthetic://unit-test-only',
        'reviewed_issue_ids': required_review_ids,
        'resolved_question_ids': checklist_ids,
    }
    assert validate_owner_approval(synthetic_approval, rooms, errors, synthetic_non_blockers, checklist) == []

    wrong_checksum = dict(synthetic_approval)
    wrong_checksum['rooms_sha256'] = '0' * 64
    assert any(
        'does not match current' in item
        for item in validate_owner_approval(wrong_checksum, rooms, errors, synthetic_non_blockers, checklist)
    )

    missing_review = dict(synthetic_approval)
    missing_review['reviewed_issue_ids'] = required_review_ids[:-1]
    assert any(
        'must exactly acknowledge every current REVIEW/POLICY_REVIEW group' in item
        for item in validate_owner_approval(missing_review, rooms, errors, synthetic_non_blockers, checklist)
    )

    missing_question = dict(synthetic_approval)
    missing_question['resolved_question_ids'] = checklist_ids[:-1]
    assert any(
        'must exactly cover all current Drive OWNER_CHECKLIST' in item
        for item in validate_owner_approval(missing_question, rooms, errors, synthetic_non_blockers, checklist)
    )

    print(
        f'ROOM_REGISTER_REVIEW_TEST_OK blockers={len(blockers)} reviews={len(reviews)} '
        f'policy_reviews={len(policy_reviews)} checklist_questions={len(checklist_ids)}'
    )


if __name__ == '__main__':
    main()
