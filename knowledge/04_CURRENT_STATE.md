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

All **25** PR-triggered workflow contours associated with that exact executable head completed `success`:

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

## 2. Active authority

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Sheets, n8n, AI, reports and management snapshots are not parallel operational truth.

`ReservationRequest -> manager/human confirmation -> Reservation` remains mandatory. No automatic global prepayment percentage is authoritative. AI/n8n cannot guarantee Reservation or confirm payment. NFC remains deferred.

## 3. Database

STATUS: **VERIFIED IN CLEAN CI + BACKUP/RESTORE + CI-LOCAL STAGING.**

Committed migrations: `0_init`, `1_site_content`, `2_guest_service_tasks`, `3_owner_analytics_snapshots`.

Clean `prisma migrate deploy` succeeds; ledger is exactly those four migrations; development seed is 84 rooms / 12 categories; critical room/date/payment constraints remain present; backup -> clean restore is verified.

`owner_analytics_snapshots` is derived management evidence only: one property/date row, horizon 1..367, object JSON payload, FK and uniqueness protections.

## 4. PMS / Guest Services

STATUS: **IMPLEMENTED + CI-VERIFIED.**

PMS V9 remains canonical with realtime, server preview->commit, move/resize/Split Stay, conflict/stale protection, TECH_BLOCK protection, CLEAN check-in gate and audit/history.

Guest Services remain Reservation-linked `OperationalTask(type=GUEST_REQUEST)`. Service creation does not automatically change Reservation total or create Payment.

## 5. Owner Intelligence

STATUS: **IMPLEMENTED + CI-VERIFIED.**

Includes fail-closed repeat-Guest identity resolution, Guest directory/history, room/payment/service/conversation drilldown, 84-room heatmap, period comparisons, CSV/print and actual XLSX (`Итоги`, `Занятость по номерам`, `Брони`, `Гости`, `Платежи`). Management metrics are not statutory accounting.

## 6. Owner Control V2

STATUS: **IMPLEMENTED + CI-VERIFIED.**

Forward management includes 7/30-day on-books occupancy, booked/available rooms by day, management allocated value, arrivals/departures, repeat-Guest factual segments and Action Center: `ARRIVAL_NOT_READY_TODAY`, `UNASSIGNED_72H`, `DEBT_72H`, `URGENT_TASKS`, `MESSAGES_NEED_REPLY`, `GUEST_DUPLICATES`.

Daily snapshot: one Core-derived row per hotel-local date; same-date recapture updates the date; manual OWNER/MANAGER and service-auth automation routes; AuditLog evidence.

Pickup states: `INSUFFICIENT_HISTORY`, `INSUFFICIENT_COVERAGE`, `READY`. READY computes net room-night, occupancy-point and management booked-value pickup. No past history is invented and no statistical demand forecast is claimed.

Repository n8n template is configured for `03:10` Asia/Bishkek, 180-day horizon, Core service-auth and no DB write; it remains `active:false`, so live deployed scheduling is NOT VERIFIED.

Dedicated evidence: Owner Control V2 CI `33243634765`, job `99077163420`, success.

## 7. Management surfaces

STATUS: **IMPLEMENTED + CI-VERIFIED / NOT EXTERNALLY PRODUCTION-VERIFIED.**

1. Command Center — current operations.
2. Reports / Owner Intelligence — historical/period analysis.
3. Owner Control V2 — forward on-books + snapshot pickup.

No surface replaces Resort Core truth.

## 8. Auth / staff / channels / AI

Repository RBAC/session/audit, Operations/Staff, Inbox, Telegram, n8n contracts, AI Sales Draft and AI Administrator contours are green. Real provider delivery and real-device acceptance remain NOT VERIFIED.

Approved channel boundary: Instagram -> ManyChat -> n8n; WhatsApp -> API Green -> n8n; website -> Core; Sheets mirror/control only.

## 9. Public site

STATUS: **CI + CI-LOCAL STAGING VERIFIED / EXTERNAL LIVE ACCEPTANCE OPEN.**

Owner-approved facts and request/payment boundaries remain guarded; rejected gym/sports-ground and stale fixed-prepayment/acquiring claims remain excluded. Live legacy `3korony.com` is not the verified new Resort OS deployment.

## 10. Known gaps

- distinct persisted Stay: not implemented;
- generic multi-property tenancy: not implemented;
- complete Folio/Charge accounting: not implemented;
- statistical demand forecasting: intentionally deferred until sufficient clean history and measurable accuracy;
- NFC: deferred.

## 11. Physical inventory

STATUS: **DEVELOPMENT 84/12 VERIFIED / PRODUCTION PHYSICAL REGISTER NOT OWNER-CONFIRMED.**

Development data must not silently become physical production truth.

## 12. Deployment

- CI-local staging: **VERIFIED** — `33243634787`.
- Single-server package: **VERIFIED IN CI** — `33243634632`.
- Beget direction: **APPROVED / ACTUAL HOST CAPABILITY NOT VERIFIED**.
- Daily snapshot n8n template: **CONFIGURED + CI-VERIFIED / LIVE ACTIVATION NOT VERIFIED**.
- Legacy rollback backup: **BLOCKED / NOT VERIFIED**.
- External HTTPS/WSS staging: **BLOCKED / NOT VERIFIED**.
- Live providers/devices: **BLOCKED / NOT VERIFIED**.
- Production cutover: **NOT PRODUCTION READY / NOT EXECUTED**.

## 13. P0 release blockers

1. Beget access + host preflight.
2. Verified rollback backup.
3. Isolated external HTTPS/WSS staging.
4. External public-truth probe.
5. Owner-confirmed physical room register.
6. Real device/browser acceptance.
7. Launch provider acceptance.
8. Fresh backup/restore/preflight/secrets/DNS/rollback evidence before cutover.

## 14. Non-blocked P1

- controlled post-stay feedback/NPS/review flow;
- controlled repeat-Guest follow-up/reactivation queue;
- safe historical Guest duplicate resolution if required;
- monitoring/restore templates;
- marketing attribution/control.

## 15. Extend, do not rewrite

Preserve Resort Core authority, PostgreSQL inventory constraints, human Reservation confirmation, fail-closed Guest identity, PMS V9 preview/commit, Owner Intelligence, Owner Control derived snapshots/pickup, Reservation-linked Guest Services, Payment idempotency, AuditLog, RBAC, OperationalTask, n8n without DB authority, public Core booking flow and dormant NFC isolation.

## 16. Next release task

P0: **Beget preflight -> rollback backup -> isolated external staging -> activate/observe daily snapshots -> external truth/browser/device/provider acceptance.**

In parallel, non-blocked product work may continue with controlled post-stay feedback and repeat-Guest follow-up without automatic outbound authority.
