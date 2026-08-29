# RESORT OS — CURRENT STATE

Version: 2.4
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL DOCKER STAGING VERIFIED / SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: factual implementation reality only

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL STAGING VERIFIED != EXTERNAL STAGING VERIFIED != PRODUCTION VERIFIED.**

## 1. Audited executable baseline

Repository: `stvelikiy-star/resort-os`
Branch: `integration/site-pms-cms-20260827`
PR: `#37`

LAST AUDITED EXECUTABLE HEAD: `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`
LAST AUDITED: 2026-08-29

All **25** pull-request-triggered workflow contours associated with that exact executable head completed `success`:

- n8n Workflow JSON CI — `33243634671`
- Dependency Security Inspection — `33243634667`
- NFC Deferred Scope CI — `33243634678`
- Public Site Truth CI — `33243634710`
- Data Intake Integrity CI — `33243634724`
- AI Administrator CI — `33243634684`
- Production Migration Baseline CI — `33243634644`
- PostgreSQL Backup Restore CI — `33243634730`
- Staff Voice CI — `33243634662`
- Payment Idempotency CI — `33243634700`
- AI Sales Draft CI — `33243634636`
- PMS Chessboard Mutation CI — `33243634705`
- n8n Resort Core Contract CI — `33243634694`
- Realtime PMS CI — `33243634714`
- Automation Contract CI — `33243634740`
- Guest Services PMS CI — `33243634701`
- Control Center Monorepo Contract CI — `33243634688`
- Hotel Operations CI — `33243634721`
- Unified Inbox CI — `33243634654`
- Telegram Sales CI — `33243634603`
- Owner Intelligence CI — `33243634715`
- Owner Control V2 CI — `33243634765`
- Resort Core CI — `33243634661`
- Three Crowns Full Staging Gate — `33243634787`
- Single Server Production Package CI — `33243634632`

Documentation-only commits after this executable head do not broaden verification.

## 2. Active source-of-truth boundary

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Sheets, n8n, AI, reporting and management snapshots are not parallel reservation/inventory/pricing/payment truth.

`ReservationRequest -> manager/human confirmation -> Reservation` remains mandatory. No automatic global prepayment percentage is authoritative. AI/n8n cannot guarantee Reservation or confirm payment.

NFC remains deferred and is absent from active application composition.

## 3. Database truth

STATUS: **VERIFIED IN CLEAN CI + BACKUP/RESTORE + CI-LOCAL STAGING.**

Committed migrations:
1. `0_init`
2. `1_site_content`
3. `2_guest_service_tasks`
4. `3_owner_analytics_snapshots`

Clean `prisma migrate deploy` succeeds. Ledger is exactly the four migrations above. Development seed remains 84 room positions / 12 categories. Critical room/date/payment constraints remain present. Backup -> clean restore is verified.

`owner_analytics_snapshots` is derived management evidence only. It has one property/date row, horizon check 1..367, object JSON payload and property FK/unique protection.

## 4. PMS / Guest Services

STATUS: **IMPLEMENTED + CI-VERIFIED.**

PMS V9 remains canonical with search/filters/grouping/density, 7/14/21/31 days, realtime, server preview->commit, move/resize/Split Stay, conflict/stale-version protection, TECH_BLOCK protection, CLEAN check-in gate and history/audit behavior.

Guest Services remain Reservation-linked `OperationalTask(type=GUEST_REQUEST)` with controlled service codes. Creating a Guest Service does not automatically change Reservation total or create Payment.

## 5. Owner Intelligence

STATUS: **IMPLEMENTED + CI-VERIFIED.**

Capabilities:
- normalized property-scoped repeat-Guest resolution;
- fail-closed identity conflict/ambiguity;
- no automatic historical merge;
- Guest directory and full reservation/room/payment/service/conversation history;
- 84-room day heatmap;
- historical period comparisons;
- CSV / browser print-PDF;
- XLSX sheets `Итоги`, `Занятость по номерам`, `Брони`, `Гости`, `Платежи`.

These are management metrics, not statutory accounting.

## 6. Owner Control V2

STATUS: **IMPLEMENTED + CI-VERIFIED.**

Forward view includes 7/30-day on-books occupancy, daily booked/available rooms, management allocated booked value, arrivals/departures, repeat-Guest factual segments and Action Center signals:
- `ARRIVAL_NOT_READY_TODAY`
- `UNASSIGNED_72H`
- `DEBT_72H`
- `URGENT_TASKS`
- `MESSAGES_NEED_REPLY`
- `GUEST_DUPLICATES`

Daily snapshots:
- one Core-derived management row per hotel-local date;
- same-date recapture updates that date rather than fabricating intraday history;
- OWNER/MANAGER manual capture;
- service-auth automation capture;
- AuditLog evidence.

Pickup:
- no prior snapshot -> `INSUFFICIENT_HISTORY`;
- insufficient baseline coverage -> `INSUFFICIENT_COVERAGE`;
- valid history -> `READY` with net room-night, occupancy-point and management booked-value pickup;
- additions/cancellations both affect net pickup;
- no historical values are invented;
- no statistical demand forecast is claimed.

n8n snapshot workflow template is configured for `03:10` Asia/Bishkek, 180-day horizon, Core service-auth only and no direct DB write. Repository workflow is `active:false`; live deployed n8n scheduling is NOT VERIFIED.

Dedicated Owner Control V2 evidence: run `33243634765`, job `99077163420`, `success`.

## 7. Dashboard / analytics

STATUS: **IMPLEMENTED + CI-VERIFIED / NOT EXTERNALLY PRODUCTION-VERIFIED.**

Three management levels now coexist without replacing Core truth:
1. Command Center — current operations;
2. Reports / Owner Intelligence — historical/period analysis;
3. Owner Control V2 — forward on-books and snapshot-based pickup.

## 8. Auth / staff / channels / AI

Current repository RBAC/session/audit, Operations/Staff, Inbox, Telegram, n8n contracts, AI Sales Draft and AI Administrator contours are CI-green.

Real external provider credentials/delivery and real iPhone/Android/Telegram acceptance remain NOT VERIFIED.

Approved channel boundary remains Instagram -> ManyChat -> n8n; WhatsApp -> API Green -> n8n; website -> Resort Core; Sheets mirror/control only.

## 9. Public site truth

STATUS: **CI + CI-LOCAL STAGING VERIFIED / EXTERNAL LIVE ACCEPTANCE OPEN.**

Owner-approved guest facts and booking/payment boundaries remain guarded. Rejected gym/sports-ground and stale fixed-prepayment/acquiring claims remain excluded.

The live legacy `3korony.com` is not the verified new Resort OS deployment.

## 10. Known current gaps

- distinct persisted canonical `Stay` not implemented;
- generic multi-property tenancy not implemented;
- complete Folio/Charge financial domain not implemented;
- statistical forecasting intentionally deferred until sufficient clean historical data and measurable accuracy exist;
- NFC deferred.

## 11. Physical inventory truth

STATUS: **DEVELOPMENT 84/12 VERIFIED / PRODUCTION PHYSICAL REGISTER NOT OWNER-CONFIRMED.**

Development data must not silently become production physical truth.

## 12. Deployment state

- CI-local full staging: **VERIFIED**, run `33243634787`.
- Single-server package: **VERIFIED IN CI**, run `33243634632`.
- Beget platform direction: **APPROVED / ACTUAL HOST CAPABILITY NOT VERIFIED**.
- Daily Owner Control n8n workflow: **CONFIGURED + CI-VERIFIED / LIVE ACTIVATION NOT VERIFIED**.
- Legacy rollback backup: **BLOCKED / NOT VERIFIED**.
- External HTTPS/WSS staging: **BLOCKED / NOT VERIFIED**.
- Live messaging/AI providers: **BLOCKED / NOT VERIFIED**.
- Production cutover: **NOT PRODUCTION READY / NOT EXECUTED**.

## 13. P0 release blockers

1. Actual Beget access + non-destructive host preflight.
2. Verified full rollback backup of current legacy site.
3. Isolated external HTTPS/WSS staging.
4. External rendered public-truth probe.
5. Owner-confirmed physical 84-room register.
6. Real device/browser acceptance.
7. Launch-enabled provider acceptance.
8. Fresh backup/restore/preflight/secrets/DNS/rollback evidence before cutover.

## 14. Non-blocked P1 work

Can continue without violating release blockers:
- controlled post-stay feedback/NPS/review flow;
- controlled repeat-Guest follow-up/reactivation queue;
- safe historical Guest duplicate resolution if required;
- production monitoring/restore templates;
- marketing attribution/control.

## 15. Extension rule

Preserve and extend rather than rewrite: Resort Core truth boundary, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9 server preview/commit, Owner Intelligence, Owner Control derived snapshots/pickup, Reservation-linked Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask, n8n without DB authority, public Core booking flow and dormant NFC isolation.

## 16. Next release task

P0 remains: **Beget preflight -> rollback backup -> isolated external staging -> activate/observe daily snapshots -> external truth/browser/device/provider acceptance.**

In parallel, non-blocked product work may continue with controlled post-stay feedback and repeat-Guest follow-up, without automatic outbound authority.
