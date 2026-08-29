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

All 25 pull-request-triggered workflow contours associated with that executable head completed with conclusion `success`:

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

These are repository/CI facts. Pull-request workflows test the PR integration context associated with the head; this evidence does not establish external-host, provider, real-device or production verification.

Documentation-only commits after this head may move the branch without broadening executable verification. The exact audited executable head above remains the release evidence boundary until a later executable head receives equivalent verification.

---

## 2. Current active architecture

Current operational source-of-truth boundary:

`PUBLIC SITE / PMS ADMIN / STAFF PWA / n8n -> FASTAPI RESORT CORE -> POSTGRESQL`

Canonical runtime entrypoint:
`services/api/app/app_entry.py` -> `app.app_entry:app`.

Current repository surfaces:
- `apps/web` — public Next.js application;
- `apps/admin` — PMS/admin Next.js application;
- `apps/staff` — staff Next.js/PWA;
- `services/api` — FastAPI Resort Core;
- `packages/database` — Prisma/PostgreSQL schema and committed migrations;
- `automation/n8n` — controlled orchestration workflows/runbooks;
- `deploy` — one-server Caddy/Docker package;
- `scripts` — integrity, migration, backup/restore, staging, host, public-truth, owner-intelligence and owner-control gates;
- `knowledge` / `docs` — canonical rules and implementation evidence.

Google Sheets, n8n, AI and analytics UIs are not parallel reservation/inventory/pricing/payment sources of truth.

NFC remains deferred and absent from active application composition.

---

## 3. CI-local Docker staging

STATUS: **VERIFIED on audited executable head `eb30433f0dd3bd44fd80cb44a150e53e0e44a816` / associated PR integration context.**

Workflow: `Three Crowns Full Staging Gate`.
Run: `33243634787`.
Conclusion: `success`.

The gate covers isolated PostgreSQL, the committed four-migration chain, deterministic seed, database invariants, release/public-truth guards, real web/admin/staff/Core container build/start, staging acceptance, active-route scope and teardown.

The staging migration check explicitly proves `owner_analytics_snapshots` exists with the expected snapshot constraints.

This is **CI-local container staging evidence only**. It is not external HTTPS/WSS staging and not production verification.

---

## 4. Single-server production package

STATUS: **VERIFIED IN CI / NOT EXTERNALLY DEPLOYED.**

Workflow: `Three Crowns Single Server Production Package CI`.
Run: `33243634632`.
Conclusion: `success`.

Current one-server runtime package remains:
- Caddy on public 80/443 edge;
- public Next.js web;
- PMS/Admin Next.js;
- Staff PWA;
- FastAPI Resort Core;
- PostgreSQL for the current package;
- pinned n8n `2.36.2`;
- persistent media/PostgreSQL/n8n state;
- backup tooling and off-site-copy expectation.

Owner-approved production direction may use Beget VPS plus managed PostgreSQL DBaaS and S3 for stronger operational autonomy. That direction is **approved architecture/planning, not externally implemented or verified current production state**.

---

## 5. Dependency / build security

STATUS: **VERIFIED FOR THE AUDITED LOCKED FRONTEND TREE IN CI.**

Declared frontend runtime:
- Next.js `15.5.24`;
- React `19.2.8`;
- React DOM `19.2.8`;
- patched PostCSS override `8.5.23`.

Owner Intelligence additionally uses server-side `openpyxl 3.1.5` for controlled XLSX management exports.

Workflow: `Three Crowns Dependency Security Inspection`.
Run: `33243634667`.
Conclusion: `success`.

Committed lockfiles remain in web/admin/staff and production Dockerfiles use deterministic installs.

---

## 6. Migration / database truth

STATUS: **VERIFIED IN CLEAN CI, BACKUP/RESTORE CI AND CI-LOCAL DOCKER STAGING.**

Committed migration chain:
- `0_init` — canonical core baseline and PostgreSQL invariants;
- `1_site_content` — `site_content_documents`;
- `2_guest_service_tasks` — structured reservation-linked guest-service context on `operational_tasks`;
- `3_owner_analytics_snapshots` — one property/date management snapshot used for real booking-pickup history.

`owner_analytics_snapshots` stores a dated derived management payload, not a second booking ledger. Operational current truth remains Reservations, InventoryBlocks, Payments, Guests, tasks and communications in Resort Core/PostgreSQL.

Verified current facts:
- clean `prisma migrate deploy` succeeds;
- migration ledger is exactly `0_init,1_site_content,2_guest_service_tasks,3_owner_analytics_snapshots`;
- development seed contains 84 room positions / 12 room categories;
- critical production-preflight PostgreSQL constraints remain present;
- active room/date overlap remains protected by PostgreSQL exclusion constraint;
- payment/date/amount integrity remains database protected;
- snapshot horizon is DB-checked to 1..367 days;
- snapshot JSON must be a JSON object;
- one snapshot row per property/date is protected by a unique index;
- backup -> clean restore preserves the new migration ledger and database state.

Evidence:
- Production Migration Baseline CI `33243634644` — `success`;
- PostgreSQL Backup Restore CI `33243634730` — `success`;
- Full Staging Gate `33243634787` — `success`.

The production database itself has not yet been migrated or proven by this evidence.

---

## 7. Reservation / availability / PMS authority

STATUS: **VERIFIED FOR CURRENT THREE CROWNS V1 FLOW IN CI.**

Canonical active boundary:

`ReservationRequest -> manager/human confirmation -> Reservation`.

Verified rules:
- `ReservationRequest != Reservation`;
- request creation does not itself guarantee a room;
- no authoritative global automatic prepayment percentage exists for current V1;
- manager chooses payment amount/terms/method and records accepted payment fact;
- AI/n8n cannot guarantee a Reservation or confirm payment;
- availability and pricing are server-authoritative Core facts;
- payment status and reservation status are separate concepts.

Evidence on audited head:
- Resort Core CI `33243634661` — `success`;
- Payment Idempotency CI `33243634700` — `success`;
- PMS Chessboard Mutation CI `33243634705` — `success`;
- Realtime PMS CI `33243634714` — `success`.

The verified PMS mutation contour includes schedule read, move preview/commit, stale-version rejection, resize, Split Stay, CLEAN check-in protection, relocation/history preservation, conflict rollback, checkout/housekeeping and AuditLog evidence.

---

## 8. PMS V9 / universal chessboard current UI

STATUS: **IMPLEMENTED AND CI-VERIFIED THROUGH PMS/CORE/STAGING CONTOURS.**

Primary daily composition:
- `PMSOperationsCockpitV9`;
- `PMSGuestServicesV9`;
- `PMSBulkGuardV9`;
- `PMSUniversalBoard`;
- shared `PMSControlSnapshotProviderV9`.

Current implemented chessboard capabilities include search, room/category/building/floor/state filters, finance/debt filters, arrivals/departures/in-house/free/debt/attention quick views, grouping, density, 7/14/21/31-day windows, HTTP polling + WebSocket, whole/segment move, Split Stay, server preview/commit, TECH_BLOCK protection, checked-in history protection and unassigned guaranteed placement.

This is the canonical operational chessboard. Review/demo packaging must not become a second scheduling source of truth.

---

## 9. Structured Guest Services

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Current flow:

`Reservation -> OperationalTask(type=GUEST_REQUEST) -> service context -> operational status`.

Controlled hotel service codes: `TRANSFER`, `MEALS`, `PARKING`, `SAUNA`, `BILLIARDS`, `EXCURSIONS`.

The admin API is OWNER/MANAGER scoped, property isolated, reservation linked and rejects duplicate active same reservation/service/date/time.

Creating a guest service does **not** automatically modify `Reservation.totalKgs` or create a `Payment`.

Dedicated evidence: Guest Services PMS CI `33243634701` — `success`.

---

## 10. Owner Intelligence / guest database / history / management analytics

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

Current owner-management contour extends canonical Guest/Reservation data rather than creating a second CRM database.

Manager confirmation resolves repeat Guests by normalized property-scoped phone/email and fails closed on identity conflict/ambiguity. Historical duplicate candidates are surfaced; automatic merge is disabled.

OWNER/MANAGER surfaces provide guest directory/search, reservation/completed-stay counts, accumulated nights, booked value/RECEIVED payment totals, last/next stay, source, complete reservation history, Split Stay room segments, payments, Guest Services, linked conversation/channel history and property isolation.

`/api/v1/admin/intelligence/occupancy-matrix` provides a room-by-day management heatmap for up to 93 days.

`/api/v1/admin/intelligence/export.xlsx` creates a real XLSX with `Итоги`, `Занятость по номерам`, `Брони`, `Гости`, `Платежи`.

Reports also retains CSV, browser print/PDF and previous-period comparisons.

Dedicated workflow: Owner Intelligence CI `33243634715` — `success`.

These are management/operational analytics, not statutory accounting.

---

## 11. Owner Control V2 / forward view / real booking pickup

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

Owner Control V2 extends Command Center with a factual forward-management layer. It does not claim to be a statistical demand forecast.

### Forward on-books view

`/api/v1/admin/intelligence/owner-brief` and the Dashboard UI provide 7/30-day forward on-books occupancy, daily booked/available rooms, management allocated booked value, arrivals/departures, an action/risk center and factual repeat-guest segments.

Current Action Center signals: `ARRIVAL_NOT_READY_TODAY`, `UNASSIGNED_72H`, `DEBT_72H`, `URGENT_TASKS`, `MESSAGES_NEED_REPLY`, `GUEST_DUPLICATES`.

### Daily snapshots

`owner_analytics_snapshots` stores one Core-derived management snapshot row per hotel-local date. Re-capturing on the same date updates that date's snapshot rather than fabricating additional intraday history.

Admin capture is OWNER/MANAGER-only. Automation capture is protected by `X-Resort-Service-Key`. Snapshot capture writes AuditLog evidence.

### Booking pickup

`GET /api/v1/admin/intelligence/pickup` compares current on-books state to a stored prior hotel-local-date snapshot.

Verified behavior:
- no prior snapshot -> `INSUFFICIENT_HISTORY`;
- inadequate baseline coverage -> `INSUFFICIENT_COVERAGE`;
- valid history -> `READY` with room-night, occupancy-point and management booked-value pickup;
- pickup is net on-books change, so additions and cancellations are both represented;
- no past values are invented;
- no demand forecast or statutory revenue claim is made.

### Daily n8n capture template

`automation/n8n/owner-analytics-daily-snapshot.json` is configured for cron `10 3 * * *`, timezone `Asia/Bishkek`, 180-day horizon and Core service-auth only, with no direct PostgreSQL write.

The repository workflow remains intentionally `active: false`. JSON/contract configuration is CI-verified; **live deployed n8n activation/execution is not verified**.

Dedicated evidence:
- Owner Control V2 CI run `33243634765`, job `99077163420` — `success`.

The E2E proves the clean four-migration chain, 84-room development seed, admin production build, Core compile/start, no fabricated pickup before history, baseline capture, real manager-confirmed Reservation after baseline, positive pickup, correct checkout movement, debt-72h, service-auth rejection/acceptance, one same-day property/date snapshot, AuditLog evidence and n8n no-direct-DB contract.

---

## 12. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts include `Guest`, `ReservationRequest`, `Reservation` and segmented `InventoryBlock` assignments.

A distinct persisted canonical `Stay` entity is still not implemented. Therefore `Guest != Reservation != Stay` separation is not yet fully implemented.

---

## 13. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Pricing is server-side by room type/date using integer KGS and sale-state controls. Payment CI covers manager-entered facts, positive amounts, context and idempotency/conflict protection.

Owner analytics figures remain management metrics, not statutory accounting. Complete Folio/Charge/Adjustment/Void/Refund accounting is not implemented. Automated acquiring is not an active V1 launch requirement.

---

## 14. Authentication / RBAC / property boundary

STATUS: **VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.**

Current evidence includes Argon2 passwords, hashed session tokens, HttpOnly cookies, expiry/revocation, active-user checks, server-side roles, Property binding and AuditLog.

Owner Intelligence/Control admin routes are OWNER/MANAGER scoped. Daily automation snapshot capture uses service auth and does not expose DB authority to n8n.

External HTTPS cookie/CORS behavior remains an external staging gate.

---

## 15. Operations / Staff PWA

STATUS: **VERIFIED IN CI; REAL-DEVICE ACCEPTANCE OPEN.**

Hotel Operations CI `33243634721` and Staff Voice CI `33243634662` completed `success`.

Real iPhone/Android/Telegram Mini App acceptance remains open.

---

## 16. CRM / omnichannel / AI

STATUS: **PARTIAL; REPOSITORY CONTOURS VERIFIED / LIVE PROVIDERS NOT VERIFIED.**

Approved channel boundary:
- Instagram -> ManyChat -> n8n;
- WhatsApp -> API Green -> n8n;
- website -> Resort Core directly;
- Google Sheets -> mirror/control surface only.

Internal AI Sales remains manager-review draft assistance only. AI does not auto-send, confirm payment or create guaranteed Reservations.

Evidence on audited head:
- Three Crowns AI Administrator CI `33243634684` — `success`;
- AI Sales Draft CI `33243634636` — `success`;
- n8n Resort Core Contract CI `33243634694` — `success`;
- n8n Workflow JSON CI `33243634671` — `success`;
- Telegram Sales CI `33243634603` — `success`;
- Unified Inbox CI `33243634654` — `success`.

Real OpenAI/API Green/provider execution remains **NOT VERIFIED / NOT LIVE**.

---

## 17. Public site / owner-approved guest truth

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

The site keeps owner-approved guest facts, request-not-confirmation boundary and current payment truth. It does not publish rejected gym/sports-ground claims or stale fixed-prepayment/acquiring claims.

Evidence:
- Public Site Truth CI `33243634710` — `success`;
- Full Staging Gate `33243634787` — `success`.

The live legacy `3korony.com` is not the verified new Resort OS deployment.

---

## 18. Dashboard / analytics / control

STATUS: **IMPLEMENTED AND CI-VERIFIED; NOT EXTERNALLY PRODUCTION-VERIFIED.**

Management now has three complementary levels:
1. **Command Center** — live current-state control;
2. **Reports / Owner Intelligence** — historical/period analysis, guest history, heatmap, comparisons and exports;
3. **Owner Control V2** — factual forward on-books control and snapshot-based pickup.

No layer becomes a parallel operational source of truth.

---

## 19. NFC

STATUS: **DEFERRED / DORMANT.**

Active application composition excludes NFC routers. NFC Deferred Scope CI `33243634678` and Full Staging `33243634787` completed `success`.

---

## 20. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks. Owner Intelligence/Control E2E use this development baseline.

Production physical room truth remains fail-closed until owner-confirmed.

---

## 21. Deployment state

### CI-local staging
STATUS: **VERIFIED** on executable head `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`. Run `33243634787` — `success`.

### Single-server deployment package
STATUS: **VERIFIED IN CI.** Run `33243634632` — `success`.

### Purchased hosting / Beget production direction
STATUS: **HOST PLATFORM DIRECTION APPROVED / ACTUAL ACCOUNT AND HOST CAPABILITY NOT VERIFIED.**

`scripts/host_preflight.sh` remains the required non-destructive first infrastructure test.

### Daily Owner Control automation
STATUS: **REPOSITORY WORKFLOW CONFIGURED AND CI-VERIFIED / LIVE n8n ACTIVATION NOT VERIFIED.**

### Legacy rollback backup
STATUS: **BLOCKED / NOT VERIFIED.**

### External HTTPS/WSS staging
STATUS: **BLOCKED / NOT VERIFIED.**

### Live AI / messaging providers
STATUS: **BLOCKED / NOT VERIFIED.**

### Production
STATUS: **NOT PRODUCTION READY / NOT PRODUCTION EXECUTED.**

No CI result alone authorizes DNS cutover.

---

## 22. High-priority gaps / blockers

### P0 production blockers
1. actual Beget access + host preflight;
2. verified full rollback backup of current legacy site;
3. isolated external HTTPS/WSS staging;
4. external rendered public-truth probe;
5. owner-confirmed physical 84-room register;
6. real iPhone/Android/Telegram acceptance;
7. real website AI browser/mobile acceptance;
8. launch-enabled provider acceptance;
9. fresh backup/restore/preflight/secrets/DNS/rollback evidence before cutover.

### P1 product/operations gaps
- live activation/observation of daily Owner Control snapshot workflow on staging;
- safe historical Guest duplicate resolution if required;
- production monitoring/watchdog + restore cadence;
- post-stay feedback/NPS/review flow;
- controlled lead follow-up/reactivation;
- marketing attribution;
- statistical forecast only after sufficient clean history and measurable forecast accuracy.

### P2 architecture gaps
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- complete Folio/Charge financial domain;
- universal internal AI Operations Administrator controlled-tool/risk model.

### DEFER
- NFC / beach wallet for current V1.

---

## 23. Foundations to extend rather than rewrite

Preserve unless concrete evidence proves a defect:
- FastAPI Resort Core truth boundary;
- PostgreSQL inventory/exclusion constraint;
- ReservationRequest -> human manager confirmation;
- fail-closed repeat-Guest identity resolver;
- server-authoritative PMS preview/commit;
- V9 universal chessboard;
- Owner Intelligence over canonical Core data;
- Owner Control derived snapshot/pickup history;
- reservation-linked Guest Services;
- payment idempotency;
- AuditLog;
- property-scoped RBAC;
- OperationalTask;
- n8n without DB authority;
- public Core availability/pricing/request flow;
- public AI without Reservation/payment authority;
- dormant NFC isolation.

---

## 24. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the actual Beget account, obtain a verified rollback backup, and—if suitable—deploy isolated external HTTPS/WSS staging. On staging, activate/observe the daily Owner Control snapshot workflow, then run external public-truth and browser/device acceptance.**

Why this remains next:
- all 25 PR-triggered workflow contours on the latest audited executable head are successful;
- Owner Intelligence and Owner Control V2 are CI-verified;
- the four-migration chain is clean-deploy verified;
- backup -> clean restore is verified;
- CI-local full staging is verified;
- the production package is verified in CI;
- the largest remaining uncertainty is the actual external infrastructure/device/provider environment.

OWNER involvement should be limited to genuine human-only blockers: infrastructure access, physical room confirmation, launch secrets/provider approval, real-device acceptance and irreversible production cutover approval.

LAST AUDITED EXECUTABLE HEAD: `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`
LAST AUDITED: 2026-08-29
