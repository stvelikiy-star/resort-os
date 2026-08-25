# Three Crowns PMS Chessboard Mutation Contract

Status: **P0 IMPLEMENTATION CONTRACT**
Date: 2026-08-25

## Purpose

The PMS chessboard is the primary daily operating surface for reception/management. Dragging or resizing a visual block must never directly mutate browser state as booking truth. Resort Core is authoritative.

One reservation may already own multiple `InventoryBlock` rows. This is intentionally used to preserve room-move history: when a guest changes rooms during one stay, the reservation remains one reservation while room assignment is represented as contiguous date segments.

## Canonical schedule model

A reservation schedule is an ordered list of contiguous segments:

```json
[
  {"room_id":"...","start":"2026-08-25","end":"2026-08-28"},
  {"room_id":"...","start":"2026-08-28","end":"2026-08-31"}
]
```

Rules:

- first segment starts at reservation `checkIn`;
- last segment ends at reservation `checkOut`;
- every segment has `start < end`;
- segments are contiguous: previous `end == next start`;
- segments never overlap or leave a gap;
- adjacent segments using the same room are canonicalized into one segment;
- all rooms belong to the same property;
- target rooms may not be `TECH_BLOCK`;
- external active blocks may not overlap any proposed segment.

## Supported user actions

The same schedule engine supports:

1. **Move future booking** — drag the reservation to another room; dates stay unchanged.
2. **Resize/cut future booking** — drag left/right edge to alter check-in or check-out.
3. **Planned split** — move only a later part of a future stay to another room.
4. **In-stay relocation** — a CHECKED_IN guest changes rooms from an effective date; prior room history stays unchanged.
5. **Extend/shorten future portion** — where allowed by current reservation status and conflict checks.

Check-in/check-out remain explicit lifecycle actions; drag/drop does not silently change Reservation status.

## Immutable history rule

For a `CHECKED_IN` reservation, room assignment for hotel nights strictly before the property's local current date is immutable through chessboard schedule mutation.

A relocation effective today may create a new segment beginning today. The old room segment remains stored up to today. No successful operation may rewrite the room assignment of already-lived nights.

`CHECKED_OUT`, `CANCELLED` and `NO_SHOW` reservations are read-only in chessboard mutation V1.

## Transaction algorithm

Every commit executes inside one PostgreSQL transaction:

1. lock Reservation `FOR UPDATE`;
2. verify reservation status is mutable;
3. compare client schedule version/token with the latest server value;
4. lock all currently used and proposed Room rows in deterministic ID order;
5. lock current active Reservation inventory blocks;
6. validate proposed dates/contiguity/property/room state;
7. for CHECKED_IN reservations, compare proposed historical assignment with stored historical assignment;
8. recheck target conflicts against active blocks belonging to other reservations/manual/maintenance blocks;
9. calculate deterministic Core pricing preview where possible;
10. mark the reservation's old active RESERVATION blocks inactive;
11. insert the new canonical active RESERVATION block schedule;
12. update Reservation `checkIn/checkOut` only when dates changed;
13. do **not** silently change `totalKgs` as part of a drag/drop mutation;
14. write AuditLog with before/after schedule and pricing preview/delta;
15. commit.

If any step fails, the transaction rolls back. The prior reservation schedule remains intact.

PostgreSQL constraint `no_overlapping_active_room_blocks` is the final guard against double booking even if an application-level conflict check misses a race.

## Pricing rule

A room/date mutation may change the deterministic tariff context. PMS must show:

- currently stored reservation value;
- suggested current Core tariff total when calculable;
- delta;
- whether room category changed.

V1 chessboard mutation does not silently overwrite the stored reservation value. Automatic compensation/upgrade/downgrade policy is UNKNOWN and must not be invented. A later explicit manager pricing action may update the commercial value if/when that workflow is approved.

## Preview before commit

Drag/drop/resize UX calls a preview endpoint before final commit. Preview returns:

- normalized proposed schedule;
- conflict status and conflict details if any;
- room/category changes;
- deterministic suggested tariff where calculable;
- stored reservation total;
- price delta;
- whether the operation rewrites protected history (must be rejected);
- current server schedule version.

Only a conflict-free preview may be committed.

## Optimistic concurrency

The UI must send the schedule version/token obtained from the current Core snapshot/preview. If another manager changed the reservation first, commit returns `409 STALE_RESERVATION` and no mutation occurs. UI reloads the current reservation and asks the manager to retry.

## Audit requirements

Every successful mutation logs:

- staff actor;
- action type `PMS_SCHEDULE_MUTATION`;
- reservation ID/booking number;
- old schedule;
- new schedule;
- old/new stay dates;
- stored total before/after (normally unchanged);
- suggested tariff and delta when available;
- timestamp/source `PMS_CHESSBOARD`.

## Realtime requirement

After commit, the existing PMS WebSocket must surface the changed schedule to all open manager screens. The public website continues to use the same inventory blocks, so availability changes immediately without any separate sync job.

## UI interaction target

Desktop:

- whole-block drag = move assignment;
- left/right resize handles = date resize;
- split/relocate action = choose effective date and target room;
- click block = reservation side panel;
- click room = room side panel;
- all mutations show preview/confirm before commit.

Touch/mobile/tablet:

- no precision-dependent drag requirement;
- tapping a reservation opens explicit `Перенести / Изменить даты / Переселить` controls using the same preview/commit API.

## Non-goals / unknown rules

Do not invent within this engine:

- cancellation/no-show penalties;
- free/paid upgrade policy;
- automatic price forgiveness or surcharge policy;
- early check-in/late checkout fees;
- group-booking semantics.

These may be layered later without changing the core schedule-safety model.
