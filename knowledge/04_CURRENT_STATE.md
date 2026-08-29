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

Current implemented chessboard capabilities include:
- search by guest/phone/booking/room/category/building context;
- room type/building/floor/room-state/reservation-state filters;
- finance/debt, occupancy and block-type filters;
- quick views: arrivals, departures, in-house, free, debt, attention;
- grouping by building/floor/category;
- compact/comfortable density;
- 7/14/21/31-day windows;
- HTTP polling + PMS WebSocket realtime;
- allowed whole-booking drag/move;
- segment move;
- Split Stay / scissors interaction;
- server preview before commit;
- TECH_BLOCK destination protection;
- checked-in history protection;
- unassigned guaranteed-reservation placement;
- fail-closed finance filters when the finance read model is unavailable/incomplete.

This is the canonical operational chessboard. Review/demo packaging must not become a second scheduling source of truth.

---

## 9. Structured Guest Services

STATUS: **IMPLEMENTED AND CI-VERIFIED.**

Current flow:

`Reservation -> OperationalTask(type=GUEST_REQUEST) -> service context -> operational status`.

Controlled hotel service codes:
- `TRANSFER`;
- `MEALS`;
- `PARKING`;
- `SAUNA`;
- `BILLIARDS`;
- `EXCURSIONS`.

The admin API `/api/v1/admin/guest-services` is OWNER/MANAGER scoped, property isolated, reservation linked, validates active `GUARANTEED`/`CHECKED_IN` reservations and rejects duplicate active same reservation/service/date/time.

Creating a guest service does **not** automatically modify `Reservation.totalKgs` or create a `Payment`.

Dedicated evidence:
- Guest Services PMS CI `33243634701` — `success`.

---

## 10. Owner Intelligence / guest database / history / management analytics

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

Current owner-management contour extends the existing Reports/Analytics and canonical Guest/Reservation data rather than creating a second CRM database.

### Guest identity

Manager confirmation resolves an existing Guest by normalized property-scoped phone/email before creating a new profile.

Verified fail-closed behavior:
- the same repeat guest with equivalent differently formatted phone/email reuses one Guest profile;
- if phone and email identify different existing profiles, confirmation returns `GUEST_IDENTITY_CONFLICT` and Reservation/Payment are not created;
- if multiple existing profiles already share the same phone or email, confirmation returns `GUEST_IDENTITY_AMBIGUOUS` instead of choosing a profile silently;
- duplicate candidates are surfaced for manual review; automatic historical merge is disabled.

Phone/email are identity evidence, not permission for uncontrolled probabilistic merging.

### Owner guest database and history

OWNER/MANAGER API under `/api/v1/admin/intelligence` provides:
- guest directory/search;
- reservation count and completed-stay count;
- accumulated room nights;
- stored booked value and RECEIVED payment totals;
- last and next stay dates;
- latest recorded source;
- complete reservation history;
- segmented room history / Split Stay schedule;
- stored payments;
- structured Guest Services;
- linked conversation/channel history;
- property isolation.

Admin UI includes `Гости / История` with lifetime management metrics, room segments, payments, services, conversations and duplicate-candidate warnings.

### Occupancy matrix

`/api/v1/admin/intelligence/occupancy-matrix` provides a room-by-day management heatmap for periods up to 93 days, including all room rows, Reservation segments, maintenance/manual blocks and guest/booking context.

### Management exports

`/api/v1/admin/intelligence/export.xlsx` creates an actual XLSX workbook for selected periods up to 367 days.

Verified sheets:
- `Итоги`;
- `Занятость по номерам`;
- `Брони`;
- `Гости`;
- `Платежи`.

Reports also retains CSV exports, browser print/PDF and previous equal-period comparisons for occupancy, ADR, RevPAR, received payments, booked room nights and CRM conversion.

Dedicated workflow: `Owner Intelligence CI`.
Run: `33243634715`.
Conclusion: `success`.

These are management/operational analytics. They are **not statutory accounting or tax reporting**.

---

## 11. Owner Control V2 / forward view / real booking pickup

STATUS: **IMPLEMENTED AND CI-VERIFIED ON AUDITED EXECUTABLE HEAD.**

Owner Control V2 extends Command Center with a factual forward-management layer. It does not claim to be a statistical demand forecast.

### Forward on-books view

`/api/v1/admin/intelligence/owner-brief` and the Dashboard UI provide:
- 7-day forward on-books occupancy;
- 30-day forward on-books occupancy;
- daily booked/available rooms;
- management allocated booked value;
- daily arrivals and departures;
- action/risk center;
- repeat-guest factual segments.

Current Action Center signals:
- `ARRIVAL_NOT_READY_TODAY`;
- `UNASSIGNED_72H`;
- `DEBT_72H`;
- `URGENT_TASKS`;
- `MESSAGES_NEED_REPLY`;
- `GUEST_DUPLICATES`.

The 72-hour lists expose the supporting Reservations rather than only a synthetic risk score.

### Daily snapshots

`owner_analytics_snapshots` stores one Core-derived management snapshot row per hotel-local date. Re-capturing on the same date updates that date's snapshot rather than fabricating additional intraday history.

Admin route:
- `POST /api/v1/admin/intelligence/snapshots/capture` — OWNER/MANAGER only.

Automation route:
- `POST /api/v1/automation/intelligence/snapshots/capture` — protected by `X-Resort-Service-Key`.

Snapshot capture writes AuditLog evidence.

### Booking pickup

`GET /api/v1/admin/intelligence/pickup` compares the current on-books state to a stored prior hotel-local-date snapshot.

Verified behavior:
- before a prior snapshot exists: `INSUFFICIENT_HISTORY`;
- if a selected baseline does not cover the requested future dates: `INSUFFICIENT_COVERAGE`;
- when history exists: `READY` with room-night pickup, occupancy-point pickup and management booked-value pickup;
- pickup is net on-books change and naturally includes additions/cancellations;
- no past values are invented;
- no demand forecast or statutory revenue-recognition claim is made.

### Daily n8n capture template

Repository workflow: `automation/n8n/owner-analytics-daily-snapshot.json`.

Configured schedule:
- cron `10 3 * * *`;
- timezone `Asia/Bishkek`;
- 180-day horizon;
- Core service-auth API only;
- no direct PostgreSQL write.

The repository workflow is intentionally `active: false`. JSON/contract configuration is CI-verified; **live deployed n8n activation/execution is not verified**.

### Dedicated evidence

Owner Control V2 CI:
- run `33243634765`;
- job `99077163420`;
- conclusion `success`.

Dedicated E2E proves:
- clean four-migration database chain;
- 84-room development seed;
- admin TypeScript typecheck and production build;
- Core compile/start;
- no fabricated pickup before historical snapshot exists;
- baseline snapshot capture;
- real Reservation creation through current manager-confirmation flow;
- positive room-night and booked-value pickup after the baseline;
- correct checkout-day departure movement;
- debt-within-72-hours control;
- unauthenticated/wrong service keys rejected;
- correct service key accepted;
- same-day snapshot remains one property/date record;
- snapshot AuditLog evidence;
- n8n workflow timezone/schedule/service-auth/no-direct-DB contract.

---

## 12. Guest / Reservation / Stay gap

STATUS: **PARTIAL.**

Persisted concepts include `Guest`, `ReservationRequest`, `Reservation` and segmented `InventoryBlock` room/date assignments.

Guest identity/repeat-reservation history is materially stronger through Owner Intelligence.

A distinct persisted canonical `Stay` entity is still not implemented. Operational stay state is represented primarily through Reservation lifecycle and segmented inventory assignments.

Therefore canonical `Guest != Reservation != Stay` separation is not yet fully implemented. This is a known target/current GAP, not permission for an unreviewed data-model rewrite.

---

## 13. Pricing / finance

STATUS: **PARTIAL; CURRENT V1 DETERMINISTIC PRICING AND MANAGER-MANUAL PAYMENT CONTROL VERIFIED.**

Current pricing is server-side by room type/date using integer KGS values and sale-state controls.

Current Payment domain/CI covers manager-entered payment facts, positive amounts, request/reservation context and idempotency/conflict protection.

Owner Intelligence and Owner Control booked-value / received-payment / ADR / RevPAR / pickup figures are management metrics from stored Resort Core facts. They do not transform current finance into statutory accounting.

A complete Folio/Charge/Adjustment/Void/Refund accounting domain is not implemented.

Automated acquiring/payment-provider integration is not an active Three Crowns V1 launch requirement.

---

## 14. Authentication / RBAC / property boundary

STATUS: **VERIFIED FOR CURRENT SINGLE-PROPERTY ROLE CONTOUR; GENERIC MULTI-TENANCY NOT IMPLEMENTED.**

Current evidence includes Argon2 passwords, hashed session tokens, HttpOnly cookies, expiry/revocation, active-user checks, server-side roles, Property binding and AuditLog authentication evidence.

Owner Intelligence/Owner Control admin routes are OWNER/MANAGER scoped. Daily automation snapshot capture uses the existing service-auth boundary and never exposes a direct database credential to n8n workflow logic.

Current runtime is property-selected by `PROPERTY_CODE`.

Generic organization/tenant hierarchy, cross-property workflows and universal resource-level multi-property permissions are not established.

External HTTPS cookie/CORS behavior remains an external staging gate.

---

## 15. Operations / Staff PWA

STATUS: **VERIFIED IN CI; REAL-DEVICE ACCEPTANCE OPEN.**

`OperationalTask` supports HOUSEKEEPING, MAINTENANCE and GUEST_REQUEST.

Hotel Operations CI `33243634721` completed `success` and covers owner/maid/technician authorization, housekeeping assignment/state transitions/rework/inspection/CLEAN acceptance, TECH_BLOCK protection, assignment history/workload and application build checks.

Staff Voice CI `33243634662` also completed `success`.

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

Public website AI Administrator is implemented and CI-covered. It uses Core facts/availability, is rate limited, fails explicitly when provider configuration is unavailable, and hands sellable booking intent to the existing ReservationRequest flow.

Evidence on audited head:
- Three Crowns AI Administrator CI `33243634684` — `success`;
- AI Sales Draft CI `33243634636` — `success`;
- n8n Resort Core Contract CI `33243634694` — `success`;
- n8n Workflow JSON CI `33243634671` — `success`;
- Telegram Sales CI `33243634603` — `success`;
- Unified Inbox CI `33243634654` — `success`.

Real OpenAI production credentials, API Green credentials, actual hotel-number webhook/E2E and external HTTPS provider execution remain **NOT VERIFIED / NOT LIVE**.

---

## 17. Public site / owner-approved guest truth

STATUS: **IMPLEMENTED AND CI/CI-LOCAL-STAGING VERIFIED; EXTERNAL LIVE ACCEPTANCE OPEN.**

Current public site preserves the approved visual direction and current owner-approved guest facts while keeping booking truth in Resort Core.

Current owner-approved facts represented in the site truth contour include current transfer prices, current approved food baseline, free parking wording, winter-only sauna, billiards, free table tennis, current excursion program, seasonal independent water operators and hotel rules.

Explicit owner rejection/current truth:
- no gym / тренажёрный зал;
- no sports grounds / sports fields / спортивные площадки.

The site keeps the request-not-confirmation boundary and current payment truth. It must not publish stale fixed 30% prepayment, first-night automatic prepayment, two-day unpaid hold, unverified online-card acquiring, unverified Elsom or AI-generated payment instructions.

Evidence:
- Public Site Truth CI `33243634710` — `success`;
- Full Staging Gate `33243634787` — `success`.

The current live legacy `3korony.com` must not be represented as the verified new Resort OS deployment.

---

## 18. Dashboard / analytics / control

STATUS: **IMPLEMENTED AND CI-VERIFIED; NOT EXTERNALLY PRODUCTION-VERIFIED.**

Current management surfaces now cover three complementary levels:

1. **Command Center** — live current-state control: arrivals/departures, occupancy, room attention, tasks, communications, payments and active debt.
2. **Reports / Owner Intelligence** — historical/period management analysis: occupancy, ADR, RevPAR, payments, CRM, guest history, heatmap, comparisons, CSV/XLSX/print.
3. **Owner Control V2** — factual forward on-books control and real snapshot-based pickup.

No layer becomes a parallel operational source of truth.

---

## 19. NFC

STATUS: **DEFERRED / DORMANT.**

Historical NFC/wristband/beach source/schema may remain in the repository, but active application composition excludes NFC routers.

NFC Deferred Scope CI `33243634678` and Full Staging `33243634787` completed `success`.

Reactivation requires explicit owner decision.

---

## 20. Physical Three Crowns room truth

STATUS: **DEVELOPMENT 84/12 BASELINE VERIFIED / PRODUCTION IMPORT BLOCKED ON OWNER FACTS.**

Development intake contains 84 room positions / 12 categories and passes integrity checks.

Owner Intelligence and Owner Control E2E use and verify the 84-room CI/development baseline.

The production register remains fail-closed until exactly 84 physical room rows and unresolved building/floor/mansard/cottage details are owner-confirmed. Development seed data must not be silently promoted into physical production truth.

---

## 21. Deployment state

### CI-local staging
STATUS: **VERIFIED** on executable head `eb30433f0dd3bd44fd80cb44a150e53e0e44a816` / associated PR integration context. Run `33243634787` — `success`.

### Single-server deployment package
STATUS: **VERIFIED IN CI.** Run `33243634632` — `success`.

### Purchased hosting / Beget production direction
STATUS: **HOST PLATFORM DIRECTION APPROVED / ACTUAL ACCOUNT AND HOST CAPABILITY NOT VERIFIED.**

The intended autonomy-oriented production direction is Beget infrastructure with application compute, managed PostgreSQL/S3 where selected, self-healing container runtime, health monitoring and controlled backup/restore. No current repository/CI evidence proves that the actual purchased account, VPS resources, DBaaS/S3 configuration, DNS, network or credentials are already provisioned accordingly.

`scripts/host_preflight.sh` remains the required non-destructive first infrastructure test.

### Daily Owner Control automation
STATUS: **REPOSITORY WORKFLOW CONFIGURED AND CI-VERIFIED / LIVE n8n ACTIVATION NOT VERIFIED.**

The daily 03:10 Asia/Bishkek snapshot workflow is present as an inactive template and calls Resort Core through service auth. Real deployed n8n scheduling has not been executed/observed by repository CI.

### Legacy rollback backup
STATUS: **BLOCKED / NOT VERIFIED.**

No verified full rollback backup of the exact currently live legacy site exists in accessible project evidence. A public crawl or old emergency archive is not sufficient proof of a full rollback point.

### External HTTPS/WSS staging
STATUS: **BLOCKED / NOT VERIFIED.**

Real TLS, secure cookies, CORS, WSS, firewall/network behavior, real browser and real-device behavior remain unproven.

### Live AI / messaging providers
STATUS: **BLOCKED / NOT VERIFIED.**

Repository configuration does not prove live credentials/provider delivery.

### Production
STATUS: **NOT PRODUCTION READY / NOT PRODUCTION EXECUTED.**

No CI result alone authorizes DNS cutover.

---

## 22. High-priority gaps / blockers

### P0 production blockers
1. actual Beget account/server access and non-destructive host capability preflight;
2. verified full rollback backup for the current legacy site;
3. isolated external HTTPS/WSS staging on the real host/network;
4. external rendered public-truth probe against that staging;
5. owner-confirmed physical 84-room register;
6. real iPhone/Android/Telegram acceptance;
7. real website AI browser/mobile acceptance;
8. real provider/WhatsApp/Instagram acceptance for launch-enabled channels;
9. fresh production backup/clean-restore/preflight/secrets/DNS/rollback evidence immediately before cutover.

### P1 product/operations gaps
- live activation and observation of the daily Owner Control snapshot workflow after staging deployment;
- safe manual workflow for resolving historical Guest duplicate candidates if owner requires historical cleanup;
- production monitoring/watchdog and backup restore cadence on the actual Beget environment;
- post-stay feedback/NPS/review flow;
- controlled lead follow-up/reactivation flow;
- production marketing analytics destination/attribution;
- statistical demand/revenue forecasting only after sufficient clean historical snapshot/booking data exists and forecast accuracy can be measured.

### P2 architecture/product gaps — not automatic rewrite mandates
- distinct canonical Stay persistence;
- generic multi-property/tenant architecture;
- complete Folio/Charge financial domain;
- universal internal AI Operations Administrator controlled-tool/risk model.

### DEFER
- NFC / beach wallet for current Three Crowns V1.

---

## 23. Foundations to extend rather than rewrite

Preserve unless later evidence proves a concrete defect:
- FastAPI Resort Core as hotel truth boundary;
- PostgreSQL room/date inventory and exclusion constraint;
- ReservationRequest -> human manager confirmation;
- repeat-Guest fail-closed identity resolver;
- server-authoritative PMS preview/commit;
- V9 universal chessboard composition;
- Owner Intelligence guest/history/reporting surfaces over canonical Core data;
- Owner Control snapshot/pickup history as derived management evidence, not source of truth;
- reservation-linked structured guest-service tasks;
- payment idempotency;
- AuditLog pattern;
- property-scoped staff session/RBAC baseline;
- OperationalTask engine;
- n8n without direct DB authority;
- public site using Core availability/pricing/ReservationRequest;
- public AI using Core facts without Reservation/payment authority;
- public truth fail-closed guards;
- dormant NFC isolation;
- current deployment package until real Beget host evidence proves a required topology change.

---

## 24. Next release task

NEXT TASK: **Run the non-destructive host capability preflight on the actual Beget hosting/VPS account, obtain a verified rollback backup of the current legacy site, and—if the host is suitable—deploy an isolated external HTTPS/WSS staging contour before replacing the apex site. On staging, activate/observe the daily Owner Control snapshot workflow, then run the external rendered public-truth probe and complete browser/device acceptance.**

Why this remains next:
- all 25 PR-triggered workflow contours associated with the latest audited executable head are successful;
- Owner Intelligence covers repeat-guest resolution, guest history, room-by-day heatmap and management exports;
- Owner Control V2 adds factual forward on-books control and real snapshot-based booking pickup without invented forecast history;
- the four-migration chain is clean-deploy verified;
- migration-aware backup -> clean restore is verified;
- CI-local Docker staging is verified;
- the one-server production package is verified in CI;
- PMS move/resize/Split Stay/realtime and structured Guest Services remain green;
- public owner-approved guest facts remain guarded;
- the highest-risk unknown is now the actual external Beget host/network/TLS/cookie/CORS/WSS/browser/device/provider environment.

OWNER involvement should be limited to real human-only blockers: Beget account/infrastructure access when unavailable to engineering, physical room-register confirmations, launch secrets/financial/provider approval where required, real-device acceptance and irreversible production cutover approval.

LAST AUDITED EXECUTABLE HEAD: `eb30433f0dd3bd44fd80cb44a150e53e0e44a816`
LAST AUDITED: 2026-08-29
