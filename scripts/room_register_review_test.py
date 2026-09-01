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
    enrichment = [item for item in issues if item['severity'] == 'ENRICHMENT']
    assert blockers, 'current canonical intake must stay fail-closed while explicit CONFIRM/inferred values remain'
    assert reviews, 'current canonical intake is expected to contain owner-facing bed-layout review items'
    assert enrichment, 'current canonical intake is expected to contain optional enrichment gaps'
    assert any(item['code'] == 'CONFIRM_NOTE' for item in blockers)
    assert any(item['code'] == 'INFERRED_VALUE' for item in blockers)
    assert any(item['code'] == 'EMPTY_BED_CONFIGURATION' for item in reviews)
    assert any(item['code'] == 'BED_LEGEND_REQUIRED' for item in reviews)
    assert all(item['code'] == 'UNKNOWN_ENRICHMENT' for item in enrichment)
    assert all(item['field'] != 'operational_status' for item in enrichment), (
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
    }
    approval_errors = validate_owner_approval(not_approved, rooms, errors, issues)
    assert any('status must be OWNER_APPROVED' in item for item in approval_errors)

    # Positive path unit-test only: simulate that BLOCKER corrections have already
    # been made in canonical CSV and that the owner explicitly acknowledged every
    # remaining REVIEW issue. ENRICHMENT is intentionally non-blocking.
    synthetic_review_and_enrichment = [item for item in issues if item['severity'] != 'BLOCKER']
    synthetic_approval = {
        'status': 'OWNER_APPROVED',
        'rooms_sha256': checksum(),
        'room_count': len(rooms),
        'approved_by': 'SYNTHETIC_TEST_ONLY',
        'approved_at': datetime.now(timezone.utc).isoformat(),
        'evidence_ref': 'synthetic://unit-test-only',
        'reviewed_issue_ids': sorted(item['id'] for item in reviews),
    }
    assert validate_owner_approval(synthetic_approval, rooms, errors, synthetic_review_and_enrichment) == []

    wrong_checksum = dict(synthetic_approval)
    wrong_checksum['rooms_sha256'] = '0' * 64
    assert any('does not match current' in item for item in validate_owner_approval(wrong_checksum, rooms, errors, synthetic_review_and_enrichment))

    missing_review = dict(synthetic_approval)
    missing_review['reviewed_issue_ids'] = synthetic_approval['reviewed_issue_ids'][:-1]
    assert any('must exactly acknowledge every current REVIEW issue' in item for item in validate_owner_approval(missing_review, rooms, errors, synthetic_review_and_enrichment))

    print(
        f'ROOM_REGISTER_REVIEW_TEST_OK blockers={len(blockers)} '
        f'reviews={len(reviews)} enrichment={len(enrichment)}'
    )


if __name__ == '__main__':
    main()
