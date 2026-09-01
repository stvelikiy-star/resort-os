# THREE CROWNS — OWNER ROOM REGISTER REVIEW

Date: 2026-09-01
Status: DEVELOPMENT REGISTER PRESENT / DRIVE OWNER CHECKLIST OPEN / OWNER APPROVAL NOT YET EVIDENCED
Canonical room data: `data-intake/rooms.csv`
Owner-question snapshot: `data-intake/owner-room-checklist.json`

This review layer does **not** create a second room inventory and does not rewrite owner data by inference.

## Current truth boundary

`data-intake/rooms.csv` currently contains exactly 84 unique room codes across 12 canonical room types and passes Data Intake Integrity CI.

The project Google Sheet `НОМЕРНОЙ ФОНД — Три Короны — Production Import 84` was checked on 2026-09-01. Its `OWNER_CHECKLIST` contains 13 P0/P1 questions with blank owner answers. In `ROOMS_IMPORT`, all 84 rows currently have `owner_confirmed=NO`.

Therefore the physical production register is **not owner-approved yet**. The existence of the spreadsheet or the 84-row count is not approval evidence.

The exact captured questions and Drive provenance are stored in `owner-room-checklist.json` as review metadata only. Canonical room values remain in `rooms.csv`.

## Deterministic review

Run:

```bash
python scripts/room_register_review.py --format summary
python scripts/room_register_review.py --format json > /tmp/room-register-review.json
```

The tool reports:

- exact CSV SHA-256;
- 84/unique/12 structural invariants;
- `BLOCKER` source contradictions/inferences;
- grouped `REVIEW` facts for physical location/bed configuration;
- grouped `POLICY_REVIEW` facts such as child/additional-place policy;
- exact 13-question Drive OWNER_CHECKLIST snapshot.

Repeated UNKNOWN values are grouped by room type/field instead of forcing the owner to confirm hundreds of identical cells one by one.

### BLOCKER

A BLOCKER means canonical intake itself contains `CONFIRM` or `inferred`. These values cannot be approved as-is merely by ticking a box. Owner evidence must first be applied to `rooms.csv`.

Current Drive checklist explicitly identifies rooms 501/502 as critical because their guest-room/category status was reconstructed and still requires confirmation.

### REVIEW

REVIEW groups cover owner-controlled physical facts such as:

- `building_or_zone` / `floor` where the Drive checklist requires P0 location confirmation;
- empty bed configurations grouped by room type;
- one global bed-abbreviation legend review rather than repeated per-room questions.

### POLICY_REVIEW

`capacity_children=UNKNOWN` is grouped by category. The owner may explicitly answer that there is no official public limit and that extra places/children are manager-confirmed; the system must not invent a number.

### SYSTEM / runtime state

`operational_status` is deliberately excluded. The Drive OWNER_CHECKLIST marks start-state as SYSTEM: before cutover reception/manager inspects rooms and sets `CLEAN / DIRTY / TECH_BLOCK`. Runtime state is not a permanent room-register attribute.

## Owner approval evidence

Template:

`data-intake/room-register-owner-approval.example.json`

Final `OWNER_APPROVED` evidence requires:

- SHA-256 of the exact current `rooms.csv`;
- exact 84-room count;
- approver, timestamp and non-secret evidence reference;
- zero current BLOCKER issues;
- exact acknowledgement of every current grouped REVIEW/POLICY_REVIEW issue;
- resolution of all 13 captured Drive OWNER_CHECKLIST P0/P1 question IDs.

Validation:

```bash
python scripts/room_register_review.py \
  --require-owner-approved \
  --approval /secure/path/room-register-owner-approval.json
```

The committed example remains `NOT_APPROVED` and CI must prove it cannot authorize production.

## What must not happen

- Do not infer the meaning of `1сп`, `2сп`, `д`, `кр`, `крк`, `к` without owner evidence.
- Do not infer what red/black text meant in screenshots.
- Do not silently correct room 223 or other odd source labels.
- Do not treat 84 development rows or the Drive Production Import file as approval when `owner_confirmed=NO`.
- Do not treat runtime operational state as a permanent room-register fact.
- Do not create a second inventory that can drift from `rooms.csv`.

## Launch relationship

Block 12 keeps `owner_room_register=NOT_VERIFIED` until this exact-register approval evidence exists.

Only after canonical BLOCKERs are corrected and the owner approval verifier passes may launch evidence reference the physical room register as VERIFIED.
