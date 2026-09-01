#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

from room_register_review import (
    EXPECTED_ROOM_COUNT,
    audit_rooms,
    checksum,
    load_rooms,
    validate_owner_approval,
)


def main() -> None:
    rooms = load_rooms()
    errors, issues = audit_rooms(rooms)
    assert errors == [], errors
    assert len(rooms) == EXPECTED_ROOM_COUNT
    assert len({row['room_code'].strip() for row in rooms}) == EXPECTED_ROOM_COUNT

    blockers = [item for item in issues if item['severity'] == 'BLOCKER']
    reviews = [item for item in issues if item['severity'] == 'REVIEW']
    assert blockers, 'current canonical intake must stay fail-closed while explicit CONFIRM/inferred values remain'
    assert reviews, 'current canonical intake is expected to contain owner-review items'
    assert any(item['code'] == 'CONFIRM_NOTE' for item in blockers)
    assert any(item['code'] == 'INFERRED_VALUE' for item in blockers)
    assert any(item['code'] == 'UNKNOWN_FIELD' for item in reviews)

    not_approved = {
        'status': 'NOT_APPROVED',
        'rooms_sha256': checksum(),
        'room_count': len(rooms),
        'approved_by': None,
        'approved_at': None,
        'evidence_ref': None,
        'reviewed_issue_ids': [],
    }
    approval_errors = validate_owner_approval(not_approved, rooms, errors, issues)
    assert any('status must be OWNER_APPROVED' in item for item in approval_errors)

    # Positive path unit-test only: simulate that BLOCKER corrections have already
    # been made in canonical CSV and that the owner explicitly acknowledged every
    # remaining REVIEW issue on this exact checksum. This does NOT approve the
    # committed register and is not external owner evidence.
    synthetic_review_only = [item for item in issues if item['severity'] == 'REVIEW']
    synthetic_approval = {
        'status': 'OWNER_APPROVED',
        'rooms_sha256': checksum(),
        'room_count': len(rooms),
        'approved_by': 'SYNTHETIC_TEST_ONLY',
        'approved_at': datetime.now(timezone.utc).isoformat(),
        'evidence_ref': 'synthetic://unit-test-only',
        'reviewed_issue_ids': sorted(item['id'] for item in synthetic_review_only),
    }
    assert validate_owner_approval(synthetic_approval, rooms, errors, synthetic_review_only) == []

    wrong_checksum = dict(synthetic_approval)
    wrong_checksum['rooms_sha256'] = '0' * 64
    assert any('does not match current' in item for item in validate_owner_approval(wrong_checksum, rooms, errors, synthetic_review_only))

    missing_review = dict(synthetic_approval)
    missing_review['reviewed_issue_ids'] = synthetic_approval['reviewed_issue_ids'][:-1]
    assert any('must exactly acknowledge every current REVIEW issue' in item for item in validate_owner_approval(missing_review, rooms, errors, synthetic_review_only))

    print(f'ROOM_REGISTER_REVIEW_TEST_OK blockers={len(blockers)} reviews={len(reviews)}')


if __name__ == '__main__':
    main()
