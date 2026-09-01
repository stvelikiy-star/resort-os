# THREE CROWNS — OWNER ROOM REGISTER REVIEW

Date: 2026-09-01
Status: DEVELOPMENT REGISTER PRESENT / OWNER APPROVAL NOT YET EVIDENCED
Canonical data source: `data-intake/rooms.csv`

This review layer does **not** create a second room inventory and does not rewrite owner data by inference.

## Current truth boundary

`data-intake/rooms.csv` currently contains exactly 84 unique room codes across 12 canonical room types and passes Data Intake Integrity CI.

That proves development-data integrity. It does **not** prove that the physical production register has been finally approved by the owner.

The current CSV intentionally preserves unresolved source markers such as `UNKNOWN`, `CONFIRM`, inferred category notes and bed abbreviations whose semantic legend has not been confirmed. Those markers must not be silently replaced by assumptions.

## Deterministic review

Run:

```bash
python scripts/room_register_review.py --format summary
python scripts/room_register_review.py --format json > /tmp/room-register-review.json
```

The tool reads only the canonical CSV and reports:

- exact CSV SHA-256;
- room count / unique codes / room-type count;
- structural errors;
- `BLOCKER` owner issues;
- `REVIEW` owner-label issues;
- optional `ENRICHMENT` gaps.

### BLOCKER

A BLOCKER means the source itself explicitly says confirmation/inference is involved. Current examples include notes containing `CONFIRM` or `inferred`.

A register cannot be marked OWNER_APPROVED while any BLOCKER remains. The correct resolution is to obtain owner evidence and update the canonical CSV, not to acknowledge the inference as true.

### REVIEW

A REVIEW item is limited to the physical room-label information the owner actually works with in the chessboard:

- empty `bed_configuration`;
- preserved bed abbreviations whose semantic legend is explicitly marked as requiring confirmation.

A REVIEW item may remain only if the owner explicitly reviewed the exact register revision and acknowledged it as acceptable. The approval manifest must list every current REVIEW issue ID exactly.

### ENRICHMENT

`building_or_zone`, `floor` and `capacity_children` UNKNOWN values are reported separately as useful metadata enrichment. They do **not** by themselves block approval of the screenshot-style physical room register.

`operational_status` is deliberately excluded from permanent owner-register approval because room operational state is runtime PMS truth (`CLEAN`, `DIRTY`, `IN_INSPECTION`, `TECH_BLOCK`), not a static physical-room attribute.

This separation prevents a 300+ item pseudo-review from obscuring the smaller set of facts the owner actually needs to confirm.

## Owner approval evidence

Template:

`data-intake/room-register-owner-approval.example.json`

Final evidence must contain:

- `status=OWNER_APPROVED`;
- SHA-256 of the exact current `rooms.csv`;
- exact room count 84;
- approver identity/name suitable for project evidence;
- approval timestamp;
- non-secret `evidence_ref` to the owner approval record;
- exact list of every remaining REVIEW issue ID.

Validation:

```bash
python scripts/room_register_review.py \
  --require-owner-approved \
  --approval /secure/path/room-register-owner-approval.json
```

The committed example is intentionally `NOT_APPROVED` and must fail this command.

Do not commit private credentials or secrets in approval evidence.

## What must not happen

- Do not infer the meaning of `1сп`, `2сп`, `д`, `кр`, `крк`, `к` without owner evidence.
- Do not infer what red/black text meant in the screenshots.
- Do not silently correct odd source text such as the current room 223 bed label.
- Do not turn the development count of 84 into an owner-approval claim.
- Do not treat runtime `operational_status` as a permanent room-register fact.
- Do not create a second spreadsheet/JSON inventory that can drift from `rooms.csv`.

## Launch relationship

The Block 12 launch gate keeps `owner_room_register` as `NOT_VERIFIED` until this exact-register approval evidence exists.

Only after the canonical CSV has no BLOCKER issues and the owner approval verifier passes may the launch evidence gate reference that approval as the physical room-register evidence.
