# THREE CROWNS RESORT OS — RELEASE COMPLETION PLAN

Status: ACTIVE EXECUTION PLAN
Date: 2026-08-31

Goal: finish the entire Three Crowns Resort OS as one operational product, not as isolated guest, PMS, website, staff, analytics, or automation modules.

## Block 1 — Core architecture and data integrity

- Preserve `PUBLIC SITE / PMS / STAFF / n8n / GUEST OS -> FASTAPI CORE -> POSTGRESQL`.
- Add Stay, RoomAssignment, RoomQr, GuestSession, GuestHistoryEvent, GuestPreference.
- Link OperationalTask to exact Stay.
- Add operational staff roles required by Reception/Store/Dining.
- Preserve reservation/payment authority and AuditLog.
- Keep NFC/payment-partner scope deferred unless separately approved.
- Add migrations and regression tests.

Exit gate: clean migration, Prisma validation, existing booking/PMS tests green, explicit stay/room/guest lifecycle tests green.

## Block 2 — Public site completion

- Verify all room cards/pages and owner-approved facts.
- Verify prices/rate rendering from canonical source.
- Preserve Transfer before Tours in service presentation.
- Verify RU/KG/EN completeness.
- Verify booking flow into ReservationRequest/Core.
- Verify mobile layout, forms, contact CTAs, rules and Guest Services content.
- Remove stale claims including gym/sports grounds/fixed prepayment.

Exit gate: public truth tests + mobile/browser acceptance.

## Block 3 — PMS / Reception / chessboard completion

- Preserve current V9/V10 visual and interaction design unless a defect requires change.
- Complete check-in/check-out lifecycle using Stay.
- Integrate RoomAssignment with move/resize/Split Stay.
- Keep room operational readiness separate from occupancy.
- Complete fast filters, conflict/stale protection, TECH_BLOCK and CLEAN check-in gate.
- Complete Reception board, reservations, payments, debt visibility and audit trail.

Exit gate: full reservation -> check-in -> move -> checkout scenario passes.

## Block 4 — Guest CRM and history

- Reliable Guest identity matching, fail closed on ambiguity.
- Unified stay/reservation/service/feedback history.
- Repeat guest, nights, rooms, service usage, notes and approved preferences.
- Avoid duplicate Guest creation where identity is safely matched.
- Preserve marketing/communication consent boundaries.

Exit gate: repeat-guest test across multiple reservations/stays passes without history loss.

## Block 5 — Guest OS / room QR

- Permanent QR per physical room.
- Secure active-stay resolution.
- First-device verification and GuestSession.
- Personalized mobile Guest OS.
- Housekeeping, towels, linen, maintenance, reception, meals, transfer, excursions, sauna, billiards.
- My Requests with statuses.
- Session revocation at checkout.

Exit gate: complete QR guest acceptance scenario passes.

## Block 6 — Staff operations

- MAID queue/checklists/photos/readiness transitions.
- TECHNICIAN voice/text ticket workflow and TECH_BLOCK integration.
- RECEPTION guest-service routing.
- STORE_STAFF and DINING_STAFF operational queues where their modules are enabled.
- Assignment, priority, SLA timestamps and AuditLog.
- Telegram WebApp/PWA real-device verification.

Exit gate: task creation -> assignment -> completion -> PMS/guest status propagation works.

## Block 7 — Guest Services Center

- One PMS queue for all guest requests.
- Filters by room, guest, stay, service, assignee, priority, date, status.
- New / assigned / in progress / done / cancelled views.
- Duplicate request protection where appropriate.
- No automatic payment/accommodation-total mutation from service request creation.

Exit gate: Reception can operate all active service requests from one surface.

## Block 8 — Finance and operational control

- Reservation payment ledger and manager-controlled payment terms.
- Outstanding balances/debtors.
- Payment idempotency and audit.
- No AI/n8n direct PostgreSQL writes or payment confirmation authority.
- Reconcile finance views with reservation truth.

Exit gate: payment and debtor scenarios reconcile against Core without duplicate mutation.

## Block 9 — Owner dashboard / analytics

- Occupancy, ADR, RevPAR, recorded payments, CRM conversion.
- 7/30-day on-books and next-30 arrivals/departures/value.
- Repeat guest metrics.
- Guest-service SLA and volume.
- Housekeeping/maintenance performance.
- Problem rooms and recurring faults.
- NPS/recovery/return-guest queues.
- CSV/XLSX/print/PDF where already supported.
- No fabricated forecast where evidence is absent.

Exit gate: dashboard numbers reconcile with seeded/known Core records.

## Block 10 — AI, n8n and unified communications

- Website, Telegram, WhatsApp, Instagram into controlled inbox/automation contracts.
- AI can qualify, draft and create ReservationRequest.
- Human OWNER/MANAGER confirmation remains required for Reservation where canonical policy requires it.
- AI cannot invent availability, price, payment terms, QR payment links or payment confirmation.
- Voice workflows route through approved Core APIs.

Exit gate: automation contract tests + manual channel acceptance.

## Block 11 — Service Point QR and property operations

- Pool, beach, toilets, corridors, dining, sauna and other selected locations.
- Location QR creates structured issue/request without exposing guest/private data.
- Route to responsible team and management visibility.

Exit gate: anonymous/location request lifecycle works end-to-end.

## Block 12 — Launch acceptance and production

- Owner-confirmed physical 84-room register.
- Beget host/account preflight.
- Verified rollback backup of current live site.
- Isolated HTTPS/WSS staging.
- Real iPhone/Android/browser/Telegram acceptance.
- Provider E2E where launch-enabled.
- Monitoring, backup/restore and secrets checks.
- Explicit owner approval before DNS cutover.

Exit gate: only after evidence exists may the release be called LIVE/VERIFIED IN PRODUCTION.

## Execution rule

Work block by block. Each block must finish with code, migration/config where relevant, tests/acceptance evidence, and a short status update before advancing. Do not redesign working surfaces unnecessarily and do not create parallel sources of truth.