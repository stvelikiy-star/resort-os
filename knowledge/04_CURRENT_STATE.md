# RESORT OS — CURRENT STATE

Version: 2.4
Date: 2026-08-29
Status: INTEGRATION RELEASE CANDIDATE / CI-LOCAL DOCKER STAGING VERIFIED / SINGLE-SERVER PRODUCTION PACKAGE VERIFIED IN CI / EXTERNAL HOST NOT VERIFIED / NOT PRODUCTION READY
Canonical: YES
Document Type: Evidence-Based Current System State
Authority: factual implementation reality only

Critical rule: **TARGET != CURRENT. IMPLEMENTED != VERIFIED. CI-LOCAL STAGING VERIFIED != EXTERNAL STAGING VERIFIED != PRODUCTION VERIFIED.**

This document records factual implementation evidence only. It does not redefine Product Bible, Domain Business Rules, target architecture or AI governance.

---

## 1. Audited integration baseline

Repository: `stvelikiy-star/resort-os`.
Integration branch: `integration/site-pms-cms-20260827`.
Open integration PR: `#37 — Unify site, V9 PMS/CRM, analytics, staff and staging through Resort Core`.

Latest fully audited executable/package head before this documentation synchronization:

`eb30433f0dd3bd44fd80cb44a150e53e0e44a816`.

All **25** pull-request-triggered workflow contours associated with that executable head completed with conclusion `success`:

- n8n Workflow JSON CI — `33243634671`;
- Three Crowns Dependency Security Inspection — `33243634667`;
- NFC Deferred Scope CI — `33243634678`;
- Public Site Truth CI — `33243634710`;
- Data Intake Integrity CI — `33243634724`;
- Three Crowns AI Administrator CI — `33243634684`;
- Production Migration Baseline CI — `33243634644`;
- PostgreSQL Backup Restore CI — `33243634730`;
- Staff Voice CI — `33243634662`;
- Payment Idempotency CI — `33243634700`;
- AI Sales Draft CI — `33243634636`;
- PMS Chessboard Mutation CI — `33243634705`;
- n8n Resort Core Contract CI — `33243634694`;
- Realtime PMS CI — `33243634714`;
- Automation Contract CI — `33243634740`;
- Guest Services PMS CI — `33243634701`;
- Control Center Monorepo Contract CI — `33243634688`;
- Hotel Operations CI — `33243634721`;
- Unified Inbox CI — `33243634654`;
- Telegram Sales CI — `33243634603`;
- Owner Intelligence CI — `33243634715`;
- Owner Control V2 CI — `33243634765`;
- Resort Core CI — `33243634661`;
- Three Crowns Full Staging Gate — `33243634787`;
- Three Crowns Single Server Production Package CI — `33243634632`.

Pull-request workflows prove the repository/CI integration context only. They do not establish external host, provider, real-device or production verification.

Documentation-only commits after this head may move the branch without broadening executable verification. The exact audited executable head above remains the release evidence boundary until a later executable head receives equivalent verification.

---

## 2. Active architecture and authority

Operational source-of-truth boundary:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint: `services/api/app/app_entry.py` -> `app.app_entry:app`.

Google Sheets, n8n, AI and analytics UIs are not parallel reservation/inventory/pricing/payment sources of truth. NFC remains deferred and absent from active application composition.

---

## 3. Database / migrations

STATUS: **VERIFIED IN CLEAN CI, BACKUP/RESTORE CI AND CI-LOCAL DOCKER STAGING.**

Committed migration chain:
1. `0_init` — core baseline and PostgreSQL invariants;
2. `1_site_content` — site content documents;
3. `2_guest_service_tasks` — Reservation-linked Guest Services context;
4. `3_owner_analytics_snapshots` — one property/date derived management snapshot for real pickup history.

Verified facts:
- clean `prisma migrate deploy` succeeds;
- ledger is exactly the four migrations above;
- development seed = 84 room positions / 12 categories;
- critical room/date/payment constraints remain present;
- snapshot horizon is checked to 1..367 days;
- snapshot payload must be a JSON object;
- one snapshot per property/date is protected by a unique index;
- backup -> clean restore preserves the migration ledger and data.

Evidence: Migration Baseline `33243634644`, Backup Restore `33243634730`, Full Staging `33243634787` — all `success`.

`owner_analytics_snapshots` is derived management evidence, not a second booking ledger. Current operational truth remains Resort Core Reservations, InventoryBlocks, Payments, Guests, tasks and communications.

---

## 4. Reservation / PMS / Guest Services

STATUS: **IMPLEMENTED AND CI-VERIFIED FOR CURRENT V1.**

Canonical boundary: `ReservationRequest -> manager/human confirmation -> Reservation`.

No global automatic prepayment percentage is authoritative. Manager chooses payment amount/terms/method. AI/n8n cannot guarantee a Reservation or confirm payment.

PMS V9 remains the canonical operational chessboard with server preview/commit, move/resize/Split Stay, conflict/stale-version protection, TECH_BLOCK protection, CLEAN check-in gate, realtime and audit history.

Guest Services remain Reservation-linked `OperationalTask(type=GUEST_REQUEST)` with controlled codes `TRANSFER`, `MEALS`, `PARKING`, `SAUNA`, `BILLIARDS`, `EXCURSIONS`. Creating a service does not automatically change accommodation total or create Payment.

Evidence: Core `33243634661`, Payment `33243634700`, PMS Mutation `33243634705`, Realtime `33243634714`, Guest Services `33243634701` — all `success`.

---

## 5. Owner Intelligence

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Current capabilities:
- fail-closed repeat-Guest resolver using normalized property-scoped phone/email;
- `GUEST_IDENTITY_CONFLICT` and `GUEST_IDENTITY_AMBIGUOUS` protection;
- no automatic historical merge;
- guest directory and complete reservation/room/payment/service/conversation history;
- 84-room day-by-day management heatmap;
- previous-period comparisons;
- CSV / print-PDF;
- actual XLSX export with `Итоги`, `Занятость по номерам`, `Брони`, `Гости`, `Платежи`.

Dedicated Owner Intelligence CI `33243634715` — `success`.

Management figures are not statutory accounting or tax reporting.

---

## 6. Owner Control V2

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Owner Control V2 adds factual forward on-books management without pretending to be a statistical demand forecast.

Forward view includes:
- 7/30-day on-books occupancy;
- booked/available rooms by day;
- management allocated booked value;
- arrivals/departures;
- repeat-guest factual segments;
- Action Center signals: `ARRIVAL_NOT_READY_TODAY`, `UNASSIGNED_72H`, `DEBT_72H`, `URGENT_TASKS`, `MESSAGES_NEED_REPLY`, `GUEST_DUPLICATES`.

Daily snapshot behavior:
- one Core-derived snapshot row per hotel-local date;
- same-date recapture updates that date rather than creating fake intraday history;
- OWNER/MANAGER manual capture;
- service-auth automation capture;
- AuditLog evidence.

Pickup behavior:
- no prior snapshot -> `INSUFFICIENT_HISTORY`;
- insufficient baseline coverage -> `INSUFFICIENT_COVERAGE`;
- valid history -> `READY` with net room-night, occupancy-point and management booked-value pickup;
- additions and cancellations both affect net pickup;
- no historical values are invented.

n8n template `automation/n8n/owner-analytics-daily-snapshot.json` is configured for `03:10` Asia/Bishkek, 180-day horizon, Core service-auth only and no direct DB write. Repository state is deliberately `active: false`; live deployed n8n activation is NOT VERIFIED.

Dedicated Owner Control V2 CI run `33243634765`, job `99077163420` — `success`.

---

## 7. Dashboard / reports

STATUS: **IMPLEMENTED AND CI-VERIFIED; NOT EXTERNALLY PRODUCTION-VERIFIED.**

Management has three complementary levels:
1. Command Center — current live operational control;
2. Reports / Owner Intelligence — historical/period analysis and exports;
3. Owner Control V2 — forward on-books control and snapshot-based pickup.

No management surface becomes a parallel operational source of truth.

---

## 8. Authentication / operations / channels / AI

STATUS: **REPOSITORY CONTOURS VERIFIED; LIVE EXTERNAL PROVIDERS/DEVICES NOT VERIFIED.**

Current auth/RBAC includes Argon2, hashed sessions, HttpOnly cookies, active-user checks, roles, Property binding and AuditLog.

Operations/Staff PWA are CI-verified; real iPhone/Android/Telegram acceptance remains open.

Approved channel boundary remains Instagram -> ManyChat -> n8n; WhatsApp -> API Green -> n8n; website -> Resort Core; Sheets mirror/control only.

AI Sales remains manager-review draft assistance. Public AI uses Core facts/availability and cannot confirm payment/Reservation.

Relevant green contours include Hotel Operations `33243634721`, Staff Voice `33243634662`, Inbox `33243634654`, Telegram Sales `33243634603`, AI Sales `33243634636`, AI Administrator `33243634684`, n8n Core Contract `33243634694`, n8n JSON `33243634671`.

Live OpenAI/API Green/provider delivery remains NOT VERIFIED / NOT LIVE.

---

## 9. Public site truth

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

The site keeps approved guest facts, request-not-confirmation booking semantics and current payment truth. Rejected gym/sports-ground claims and stale fixed-prepayment/acquiring claims remain excluded.

Public Site Truth `33243634710` and Full Staging `33243634787` — `success`.

The currently live legacy `3korony.com` is not the verified new Resort OS deployment.

---

## 10. Known architecture/product gaps

- distinct persisted canonical `Stay` is not implemented;
- generic multi-property tenancy is not implemented;
- complete Folio/Charge/Adjustment/Void/Refund accounting is not implemented;
- statistical demand/revenue forecast is intentionally not claimed before sufficient clean historical data and measurable accuracy exist;
- NFC remains DEFERRED.

These are gaps, not permission for unreviewed rewrites.

---

## 11. Physical room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

CI/development contains 84 room positions / 12 categories. Production physical room truth remains fail-closed until owner-confirmed.

---

## 12. Deployment state

- CI-local staging: **VERIFIED**, run `33243634787`.
- Single-server production package: **VERIFIED IN CI**, run `33243634632`.
- Beget direction: **APPROVED / ACTUAL HOST CAPABILITY NOT VERIFIED**.
- Daily Owner Control n8n workflow: **CONFIGURED + CI-VERIFIED / LIVE ACTIVATION NOT VERIFIED**.
- Legacy rollback backup: **BLOCKED / NOT VERIFIED**.
- External HTTPS/WSS staging: **BLOCKED / NOT VERIFIED**.
- Live AI/messaging providers: **BLOCKED / NOT VERIFIED**.
- Production cutover: **NOT PRODUCTION READY / NOT EXECUTED**.

No CI result alone authorizes DNS cutover.

---

## 13. P0 blockers

1. Actual Beget account/server access + non-destructive host preflight.
2. Verified full rollback backup of the current legacy site.
3. Isolated external HTTPS/WSS staging.
4. External rendered public-truth probe.
5. Owner-confirmed physical 84-room register.
6. Real iPhone/Android/Telegram acceptance.
7. Real website AI browser/mobile acceptance.
8. Launch-enabled provider acceptance.
9. Fresh backup/restore/preflight/secrets/DNS/rollback evidence before cutover.

---

## 14. P1 next work

Non-infrastructure work that can continue without violating P0 boundaries:
- controlled post-stay feedback/NPS/review workflow;
- controlled repeat-guest/follow-up/reactivation queue;
- safe historical Guest duplicate-resolution workflow if needed;
- monitoring/watchdog and restore cadence templates;
- marketing attribution/control;
- statistical forecast only after sufficient snapshot history exists.

---

## 15. Foundations to extend rather than rewrite

Preserve: Resort Core truth boundary; PostgreSQL inventory constraints; ReservationRequest -> human confirmation; fail-closed Guest identity; PMS V9 server preview/commit; Owner Intelligence; Owner Control derived snapshots/pickup; Reservation-linked Guest Services; payment idempotency; AuditLog; property-scoped RBAC; OperationalTask; n8n without DB authority; public Core booking flow; public AI without Reservation/payment authority; dormant NFC isolation.

---

## 16. Next release task

NEXT TASK: **External infrastructure remains the P0 release task: Beget preflight -> verified rollback backup -> isolated HTTPS/WSS staging -> activate/observe daily Owner Control snapshots -> public-truth + browser/device/provider acceptance. In parallel, non-blocked product work may continue through controlled post-stay feedback and repeat-guest follow-up without automatic outbound authority.**

LAST AUDITED EXECUTABLE HEAD: `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`
LAST AUDITED: 2026-08-29
