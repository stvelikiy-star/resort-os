# Three Crowns Reception UX gap — 2026-09-05

## Reproduced behavior

Check-in is correctly fail-closed unless the assigned room is `CLEAN`. The Reception UI currently surfaces the rejection but does not make the recovery path obvious enough to the operator.

## Preserve

- Core check-in gate `room_state == CLEAN`;
- housekeeping lifecycle `DIRTY -> IN_PROGRESS -> IN_INSPECTION -> CLEAN`;
- maintenance `TECH_BLOCK` isolation;
- RECEPTION must not gain unrestricted housekeeping/maintenance mutation authority by a frontend shortcut.

## UX change required

For every GUARANTEED arrival:
- show room readiness as a first-class badge next to the check-in action;
- if not CLEAN, replace/disable the primary check-in CTA with an explicit readiness action/help text;
- distinguish `DIRTY`, `IN_INSPECTION`, `TECH_BLOCK`, `UNKNOWN`, and no assigned room;
- provide a safe handoff to the responsible manager/housekeeping workflow rather than a dead-end error;
- after successful check-in, surface the one-time Guest OS PIN and guest-access next step clearly.

## Backend decision before implementation

Current Operations authorization does not grant RECEPTION generic task mutation permissions. A direct Reception "send to housekeeping" action therefore needs either:
1. manager-only navigation/handoff; or
2. a narrow audited Core endpoint that allows RECEPTION to request housekeeping without changing arbitrary task/room state.

Do not solve this by exposing the full Operations API to RECEPTION.
