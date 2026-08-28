# Three Crowns PMS V10 unified integration evidence

Date: 2026-08-28
Status: EXECUTABLE INTEGRATION VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION CUTOVER

## Scope

This evidence records the integration of the owner-reviewed V10 PMS concept into the existing server-authoritative PMS V9 / Resort Core architecture. It does not create a parallel booking engine, database or offline source of truth.

Canonical runtime invariant remains:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

## Implemented integration

Executable verified head:

`98468ff982fb4a80d7d1dcec7a46f8a09a851d4b`

Changes on the integration branch:

- `PMSGridV9` now mounts `PMSIntegrationRailV10` above the existing V9 operational surfaces.
- V10 unified control reads only existing Resort Core APIs:
  - `/core/api/v1/admin/dashboard`;
  - `/core/api/v1/admin/guest-services?status=ACTIVE&limit=300`;
  - `/core/api/v1/admin/reception/reservations?limit=500`.
- The unified control exposes a single operator chain: `website request -> manager confirmation -> Reservation -> stay/reception -> guest services -> finance -> chessboard`.
- Navigation jumps to the existing live V9 reception cockpit, Guest Services, bulk operational guard and Universal Tape Chart rather than duplicating their logic.
- Counts based on potentially truncated guest-service/reservation lists fail closed: if the 300/500 read limit is reached or a dependent read is incomplete, the corresponding KPI is hidden instead of presenting a false complete count.
- Existing authoritative rules remain unchanged: `ReservationRequest != Reservation`, human confirmation, no automatic fixed prepayment percentage, payment facts remain manager-controlled, Guest Services do not automatically mutate lodging finance, check-in requires a ready room, PMS schedule mutation remains preview -> explicit commit, Split Stay remains server-authoritative, and NFC remains deferred.

## Existing connected contour retained

The live PMS composition is now:

1. `PMSIntegrationRailV10`
2. `PMSOperationsCockpitV9`
3. `PMSGuestServicesV9`
4. `PMSBulkGuardV9`
5. `PMSUniversalBoard`

All components use Resort Core/PostgreSQL state. The owner-review standalone HTML remains a review artifact only and is not introduced as a second operational database or booking truth.

## Verification

All 23 pull-request workflow contours associated with executable head `98468ff982fb4a80d7d1dcec7a46f8a09a851d4b` completed with conclusion `success`:

- Resort Core CI — `33185800028`
- Three Crowns Full Staging Gate — `33185799944`
- Three Crowns Single Server Production Package CI — `33185799912`
- Three Crowns Dependency Security Inspection — `33185799995`
- Production Migration Baseline CI — `33185799929`
- PostgreSQL Backup Restore CI — `33185799957`
- Control Center Monorepo Contract CI — `33185799945`
- PMS Chessboard Mutation CI — `33185800013`
- Realtime PMS CI — `33185799938`
- Guest Services PMS CI — `33185799897`
- Hotel Operations CI — `33185799988`
- Public Site Truth CI — `33185799961`
- Three Crowns AI Administrator CI — `33185799953`
- AI Sales Draft CI — `33185799910`
- Unified Inbox CI — `33185799888`
- Telegram Sales CI — `33185799941`
- Staff Voice CI — `33185800004`
- Payment Idempotency CI — `33185799935`
- Automation Contract CI — `33185799887`
- n8n Resort Core Contract CI — `33185800060`
- n8n Workflow JSON CI — `33185799926`
- Data Intake Integrity CI — `33185800099`
- NFC Deferred Scope CI — `33185799875`

Guest Services PMS CI additionally proved on this head:

- Prisma schema / migration chain validation;
- PMS V9 TypeScript typecheck;
- Core compile;
- real Reservation creation through the current manager flow;
- structured transfer request creation with no automatic finance mutation;
- duplicate active service rejection and invalid-time rejection;
- property isolation;
- queue/status transition and AuditLog evidence.

## Production boundary

This verification is repository/CI-local staging evidence. It does not prove the purchased `3korony.com` host, external HTTPS/WSS, real mobile devices, real provider credentials or production DNS/cutover.

Production blockers remain the host preflight, verified backup/rollback of the legacy site, external staging acceptance, owner-confirmed physical room register, real-device acceptance and real provider E2E where applicable.
