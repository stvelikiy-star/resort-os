# THREE CROWNS — OWNER ROOM REGISTER REVIEW

Date: 2026-09-01
Status: OWNER APPROVAL EVIDENCE COMMITTED / CI VERIFICATION REQUIRED BEFORE MERGE
Canonical room data: `data-intake/rooms.csv`
Approval evidence: `data-intake/room-register-owner-approval.json`
Historical owner-question snapshot: `data-intake/owner-room-checklist.json`

## Current truth boundary

`data-intake/rooms.csv` contains exactly 84 unique room codes across 12 canonical room types. The owner has explicitly accepted the existing 84-room register and the exact PMS room labels as sufficient for V1.

This approval does **not** authorize invention of optional metadata. Unknown `building_or_zone`, `floor`, and `capacity_children` values remain `UNKNOWN` where no factual value is recorded. Raw bed shorthand is preserved verbatim and is not semantically expanded by the system. Runtime `operational_status` remains PMS truth and is not part of the permanent physical register.

The stale `CONFIRM` / `inferred` provenance text on rooms 501/502 has been removed without changing their room codes, category, capacity, floor marker, raw bed label, or area. The approval evidence binds to the exact SHA-256 of the canonical CSV.

## Deterministic approval gate

The block is approved only when this command succeeds on the exact PR head:

```bash
python scripts/room_register_review.py \
  --require-owner-approved \
  --approval data-intake/room-register-owner-approval.json
```

CI additionally proves:

- exactly 84 rows and 84 unique room codes;
- exactly 12 canonical room types;
- zero structural errors;
- zero `BLOCKER` issues (`CONFIRM_NOTE` / `INFERRED_VALUE`);
- exact CSV SHA-256 binding;
- exact acknowledgement of every current `REVIEW` / `POLICY_REVIEW` group;
- exact coverage of all 13 historical OWNER_CHECKLIST question IDs;
- bad checksum fails closed;
- missing review acknowledgement fails closed;
- missing checklist resolution fails closed;
- downgraded `NOT_APPROVED` status fails closed;
- the example approval template remains unable to authorize production.

## Accepted review semantics

Remaining review groups are acknowledged decisions, not missing launch facts:

- unknown building/floor metadata stays unknown rather than being guessed;
- child/additional-place numeric limits are not publicly promised unless later configured;
- empty raw bed labels remain empty where the source did not provide a label;
- bed abbreviations stay verbatim (`1сп`, `2сп`, `д`, `кр`, `крк`, variants) without an invented legend.

## What must not happen

- Do not infer building, floor, child capacity, or bed semantics.
- Do not infer meaning from legacy chessboard colors.
- Do not silently normalize odd source labels such as room 223.
- Do not create a second inventory that can drift from `rooms.csv`.
- Do not treat runtime `CLEAN / DIRTY / TECH_BLOCK` as permanent room metadata.

## PMS relationship

PMS Owner Grid CI is required to seed the canonical 84-room intake because `data-intake/**` is in its PR trigger. PMS Chessboard Mutation CI is also expected on this PR because the verifier test under `scripts/**` changes. The room-register block is not reported as complete until the exact PR head is green and merged into `integration/site-pms-cms-20260827`.
